"""
detection.py
------------
Lógica de detección de canales CMYK mediante análisis HSV/LAB/BGR
y template matching sobre imágenes de canal aislado.
"""

import cv2
import numpy as np

from app.core.config import CLUSTERING_SIGMA, CMY_CROP_RANGES
from app.core.image_utils import multi_scale_template_match


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_representative_color(
    mask: np.ndarray, bgr_img: np.ndarray
) -> tuple[tuple | None, tuple | None, int]:
    """
    Dado una máscara binaria y la imagen original BGR, calcula el color
    representativo (mediana) de los píxeles detectados.

    Retorna (rgb_tuple, hsv_tuple, pixel_count).
    """
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None, None, 0
    pixels_bgr = bgr_img[ys, xs]
    med_b = int(np.median(pixels_bgr[:, 0]))
    med_g = int(np.median(pixels_bgr[:, 1]))
    med_r = int(np.median(pixels_bgr[:, 2]))
    rgb = (med_r, med_g, med_b)
    pixel_bgr_sample = np.array([[[med_b, med_g, med_r]]], dtype=np.uint8)
    pixel_hsv = cv2.cvtColor(pixel_bgr_sample, cv2.COLOR_BGR2HSV)
    hsv = (int(pixel_hsv[0, 0, 0]), int(pixel_hsv[0, 0, 1]), int(pixel_hsv[0, 0, 2]))
    return rgb, hsv, len(xs)


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    """Mediana ponderada: el valor cuya suma acumulada de pesos alcanza el 50%."""
    if len(values) == 0:
        return 0
    sorted_indices = np.argsort(values)
    sorted_values = values[sorted_indices]
    sorted_weights = weights[sorted_indices]
    cumsum_weights = np.cumsum(sorted_weights)
    total_weight = cumsum_weights[-1]
    median_idx = np.searchsorted(cumsum_weights, total_weight / 2.0)
    median_idx = np.clip(median_idx, 0, len(sorted_values) - 1)
    return sorted_values[median_idx]


# ---------------------------------------------------------------------------
# Canal de color aislado
# ---------------------------------------------------------------------------

def crear_imagen_canal_color(
    crop_bgr: np.ndarray,
    ch_name: str,
    ch_info: dict,
    k_local_cx: int,
    k_local_cy: int,
    search_radius: int = 110,
) -> tuple:
    """
    Genera una imagen derivada exclusiva para aislar el canal ch_name (C, M o Y).

    Sistema híbrido (v3.2):
      · C → LAB/BGR + HSV
      · M → HSV + LAB/BGR opcional
      · Y → HSV + LAB

    Retorna
    -------
    img_color_isolated : BGR imagen con solo el color detectado
    mask_full          : máscara binaria completa del color
    mask_near_k        : máscara restringida a zona cercana a K
    crop_enhanced_bgr  : imagen preprocesada (LAB+CLAHE)
    diag_masks         : dict {'hsv_sin_boost', 'lab_bgr'}
    """
    crop_h, crop_w = crop_bgr.shape[:2]
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    # Preprocesamiento LAB + CLAHE
    crop_lab_color = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2LAB)
    L_ch, a_ch, b_ch = cv2.split(crop_lab_color)
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
    L_eq = clahe.apply(L_ch)
    crop_enhanced_bgr = cv2.cvtColor(cv2.merge((L_eq, a_ch, b_ch)), cv2.COLOR_LAB2BGR)

    crop_hsv = cv2.cvtColor(crop_enhanced_bgr, cv2.COLOR_BGR2HSV)
    B_i = crop_bgr[:, :, 0].astype(np.int16)
    G_i = crop_bgr[:, :, 1].astype(np.int16)
    R_i = crop_bgr[:, :, 2].astype(np.int16)

    mask_hsv_sin_boost = np.zeros((crop_h, crop_w), dtype=np.uint8)
    mask_lab_bgr       = np.zeros((crop_h, crop_w), dtype=np.uint8)
    color_mask         = np.zeros((crop_h, crop_w), dtype=np.uint8)

    if ch_name == 'C':
        bgr_mask = ((B_i > R_i + 3) & (B_i > G_i + 2) & (B_i > 25)).astype(np.uint8) * 255
        lab_mask = cv2.bitwise_and(
            cv2.inRange(b_ch, np.array([0]),  np.array([124])),
            cv2.inRange(L_ch, np.array([15]), np.array([170])),
        )
        mask_lab_bgr = cv2.bitwise_or(bgr_mask, lab_mask)
        for lower, upper in ch_info['hsv_ranges']:
            mask_hsv_sin_boost = cv2.bitwise_or(
                mask_hsv_sin_boost, cv2.inRange(crop_hsv, lower, upper)
            )
        color_mask = cv2.bitwise_and(mask_hsv_sin_boost, mask_lab_bgr)

    elif ch_name == 'M':
        for lower, upper in ch_info['hsv_ranges']:
            mask_hsv_sin_boost = cv2.bitwise_or(
                mask_hsv_sin_boost, cv2.inRange(crop_hsv, lower, upper)
            )
        color_mask = mask_hsv_sin_boost.copy()
        if ch_info.get('usar_lab_bgr', False):
            lab_m_mask = cv2.bitwise_and(
                cv2.inRange(a_ch, np.array([138]), np.array([255])),
                cv2.inRange(L_ch, np.array([15]),  np.array([200])),
            )
            bgr_m_mask = (
                (R_i > B_i + 5) & (R_i > G_i + 5) & (R_i > 30) & (np.abs(R_i - B_i) > 10)
            ).astype(np.uint8) * 255
            mask_lab_bgr = cv2.bitwise_or(lab_m_mask, bgr_m_mask)
            color_mask = mask_lab_bgr.copy()

    elif ch_name == 'Y':
        for lower, upper in ch_info['hsv_ranges']:
            mask_hsv_sin_boost = cv2.bitwise_or(
                mask_hsv_sin_boost, cv2.inRange(crop_hsv, lower, upper)
            )
        lab_mask = cv2.bitwise_and(
            cv2.inRange(b_ch, np.array([132]), np.array([255])),
            cv2.inRange(a_ch, np.array([110]), np.array([145])),
        )
        color_mask = lab_mask.copy()

    # Limpieza morfológica
    color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN,  kernel, iterations=1)

    # Restricción a zona cercana a K
    search_mask = np.zeros((crop_h, crop_w), dtype=np.uint8)
    cv2.circle(search_mask, (k_local_cx, k_local_cy), search_radius, 255, -1)
    mask_near_k = cv2.bitwise_and(color_mask, search_mask)

    # Imagen aislada
    background = (crop_bgr.astype(np.float32) * 0.15).astype(np.uint8)
    img_color_isolated = background.copy()
    img_color_isolated[color_mask > 0] = crop_bgr[color_mask > 0]

    diag_masks = {
        'hsv_sin_boost': mask_hsv_sin_boost,
        'lab_bgr':       mask_lab_bgr,
    }
    return img_color_isolated, color_mask, mask_near_k, crop_enhanced_bgr, diag_masks


# ---------------------------------------------------------------------------
# Pipeline de detección por canal
# ---------------------------------------------------------------------------

def detectar_canal(
    img_bgr: np.ndarray,
    ch_name: str,
    ch_info: dict,
    k_marks: list[tuple],
    template: np.ndarray,
    roi_margin: int = 230,
    search_radius: int = 110,
    threshold: float = 0.2,
) -> tuple[list[tuple], list[dict]]:
    """
    Para cada marca K detectada, crea una imagen de canal aislado y detecta
    la posición CMY mediante template matching + mediana ponderada.

    Retorna: (marks_canal, diag_data_list)
    """
    marks_canal    = []
    diag_data_list = []
    img_h, img_w   = img_bgr.shape[:2]

    for mark_idx, (kcx, kcy, kscore, kscale) in enumerate(k_marks[:1]):
        rx1 = max(int(kcx) - roi_margin, 0)
        ry1 = max(int(kcy) - roi_margin, 0)
        rx2 = min(int(kcx) + roi_margin, img_w)
        ry2 = min(int(kcy) + roi_margin, img_h)

        crop_bgr   = img_bgr[ry1:ry2, rx1:rx2].copy()
        k_local_cx = int(kcx) - rx1
        k_local_cy = int(kcy) - ry1

        img_isolated, mask_full, mask_near, crop_enhanced, diag_masks = crear_imagen_canal_color(
            crop_bgr, ch_name, ch_info, k_local_cx, k_local_cy, search_radius
        )

        _, _, px_count = get_representative_color(mask_near, crop_bgr)

        # Detección de posición
        best_cx, best_cy, best_score, best_scale = kcx, kcy, 0.05, kscale
        method_used = 'prediccion'

        if px_count > 30:
            isolated_gray = cv2.cvtColor(img_isolated, cv2.COLOR_BGR2GRAY)
            clahe2 = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(4, 4))
            isolated_enhanced = clahe2.apply(isolated_gray)
            test_scales = np.arange(max(0.2, kscale - 0.2), kscale + 0.3, 0.05)
            local_detections = multi_scale_template_match(
                isolated_enhanced, template, scales=test_scales, threshold=threshold
            )
            if local_detections:
                local_detections.sort(key=lambda x: x[2], reverse=True)
                dcx, dcy, dscore, dscale = local_detections[0]
                best_cx, best_cy = dcx + rx1, dcy + ry1
                best_score, best_scale = dscore, dscale
                method_used = 'template_img_separada'

        # Fallback: centroide ponderado
        ys, xs = np.where(mask_near > 0)
        if method_used == 'prediccion' and len(xs) > 0:
            dists   = np.hypot(xs - k_local_cx, ys - k_local_cy)
            weights = np.exp(-dists / 20.0)
            best_cx = int(np.average(xs, weights=weights)) + rx1
            best_cy = int(np.average(ys, weights=weights)) + ry1
            best_score = round(min(px_count / 300.0, 1.0), 3)
            best_scale = kscale
            method_used = 'centroide_ponderado'

        # v3.2: refinamiento por mediana ponderada
        if len(xs) > 0:
            dists_fin   = np.hypot(xs - k_local_cx, ys - k_local_cy)
            weights_fin = np.exp(-dists_fin / CLUSTERING_SIGMA)
            best_cx     = int(weighted_median(xs, weights_fin)) + rx1
            best_cy     = int(weighted_median(ys, weights_fin)) + ry1
            method_used += '+mediana_ponderada'

        marks_canal.append((best_cx, best_cy, best_score, best_scale))

        diag_data_list.append({
            'crop_bgr':      crop_bgr,
            'crop_enhanced': crop_enhanced,
            'img_isolated':  img_isolated,
            'diag_masks':    diag_masks,
            'mask_full':     mask_full,
            'mask_near':     mask_near,
            'px_count':      px_count,
            'k_local_cx':    k_local_cx,
            'k_local_cy':    k_local_cy,
            'method_used':   method_used,
        })

    return marks_canal, diag_data_list


# ---------------------------------------------------------------------------
# Pipeline completo
# ---------------------------------------------------------------------------

def procesar_imagen_completa(
    img_bgr: np.ndarray,
    template: np.ndarray,
    roi_margin: int = 230,
    search_radius: int = 110,
    min_pixels: int = 1000,
    channels: list = None,  # Agregar este parámetro
) -> tuple[dict | None, dict | None, list]:
    """
    Procesa una imagen completa: detecta K, luego C/M/Y.
    
    Args:
        channels: Lista de canales a analizar (ej: ['C', 'M', 'Y']).
                 Si None, analiza todos.
    """
    from app.core.image_utils import (
        preprocess_image,
        multi_scale_template_match,
        non_max_suppression,
    )

    if channels is None:
        channels = ['C', 'M', 'Y']

    # PASO 1: Detectar K
    lab_prep = preprocess_image(img_bgr)
    L_full, _, _ = cv2.split(lab_prep)
    k_detections = multi_scale_template_match(
        L_full, template,
        scales=np.arange(0.15, 3.2, 0.1),
        threshold=0.35,
    )
    k_marks = non_max_suppression(k_detections, radius=110)

    if not k_marks:
        return None, None, []

    # PASO 2: Detectar solo los canales seleccionados
    cmyk_marks     = {'K': k_marks}
    diag_por_canal = {}

    for ch_name, ch_info in CMY_CROP_RANGES.items():
        if ch_name not in channels:  # Solo si está en la lista
            cmyk_marks[ch_name] = []
            continue
            
        marks_canal, diag_data = detectar_canal(
            img_bgr, ch_name, ch_info, k_marks,
            template, roi_margin=roi_margin,
            search_radius=search_radius, threshold=0.2,
        )
        px = diag_data[0].get('px_count', 0) if diag_data else 0
        if px >= min_pixels:
            cmyk_marks[ch_name]     = marks_canal
            diag_por_canal[ch_name] = diag_data
        else:
            cmyk_marks[ch_name] = []

    return cmyk_marks, diag_por_canal, k_marks
