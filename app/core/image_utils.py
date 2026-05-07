"""
image_utils.py
--------------
Utilidades de procesamiento de imagen: sharpening, preprocesado,
generación de plantilla y template matching multi-escala.
"""

import cv2
import numpy as np


def sharpen_image(bgr_img: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """
    Aplica unsharp masking para mejorar la nitidez de la imagen.

    Parámetros
    ----------
    bgr_img  : imagen BGR (uint8)
    strength : intensidad del sharpening
               0.0 → sin cambio | 0.5 → suave | 1.0 → normal | 2.0 → fuerte
    """
    if strength == 0:
        return bgr_img.copy()
    blur = cv2.GaussianBlur(bgr_img, (0, 0), sigmaX=3)
    sharpened = cv2.addWeighted(bgr_img, 1.0 + strength, blur, -strength, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def preprocess_image(bgr_img: np.ndarray) -> np.ndarray:
    """LAB → CLAHE sobre canal L → devuelve imagen LAB mejorada."""
    lab = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2LAB)
    L, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    L = clahe.apply(L)
    return cv2.merge((L, a, b))


def create_crosshair_template(
    size: int = 101,
    ring_radius: int = 40,
    ring_thickness: int = 8,
    cross_thickness: int = 10,
    cross_length: int = 90,
) -> np.ndarray:
    """Genera plantilla sintética de marca de registro (círculo + cruz). Binaria blanco/negro."""
    template = np.zeros((size, size), dtype=np.uint8)
    center = size // 2
    half_cross = cross_length // 2
    cv2.line(template, (center, center - half_cross), (center, center + half_cross), 255, cross_thickness)
    cv2.line(template, (center - half_cross, center), (center + half_cross, center), 255, cross_thickness)
    cv2.circle(template, (center, center), ring_radius, 255, ring_thickness)
    return template


def multi_scale_template_match(
    gray: np.ndarray,
    template: np.ndarray,
    scales: np.ndarray | None = None,
    threshold: float = 0.5,
) -> list[tuple]:
    """
    Template matching a múltiples escalas.

    Retorna lista de (x, y, score, scale).
    """
    if scales is None:
        scales = np.arange(0.3, 2.5, 0.1)
    detections = []
    th, tw = template.shape[:2]
    for s in scales:
        new_w = int(tw * s)
        new_h = int(th * s)
        if new_w < 20 or new_h < 20:
            continue
        if new_w > gray.shape[1] or new_h > gray.shape[0]:
            continue
        resized_template = cv2.resize(template, (new_w, new_h))
        gray_inv = cv2.bitwise_not(gray)
        result = cv2.matchTemplate(gray_inv, resized_template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        for pt_y, pt_x in zip(*locations):
            cx = pt_x + new_w // 2
            cy = pt_y + new_h // 2
            score = result[pt_y, pt_x]
            detections.append((cx, cy, float(score), s))
    return detections


def non_max_suppression(detections: list[tuple], radius: float) -> list[tuple]:
    """
    Elimina duplicados: si dos detecciones están a menos de `radius` px,
    queda la de mayor score. Devuelve solo la mejor detección.
    """
    if not detections:
        return []
    detections = sorted(detections, key=lambda d: d[2], reverse=True)
    kept = []
    for det in detections:
        cx, cy, score, scale = det
        is_duplicate = any(np.hypot(cx - k[0], cy - k[1]) < radius for k in kept)
        if not is_duplicate:
            kept.append(det)
    return kept[:1]
