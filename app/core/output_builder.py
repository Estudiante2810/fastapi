"""
output_builder.py
-----------------
Generación de imágenes de salida: máscaras, resultado anotado y panel de cálculos mm.
"""

import os
import cv2
import numpy as np
from app.core.config import calculate_mm_per_pixel
from app.core.config import (
    CMY_CROP_RANGES, COLORS_LABEL, offsets_label,
    distancia_camara_plano_mm, focal_mm, sensor_width_mm,
    MARK_DIAMETER_PX, FACTOR_CORRECION_MM
)


def build_masks_panel(
    img_bgr: np.ndarray,
    cmyk_marks: dict,
    diag_por_canal: dict,
    k_marks: list,
    roi_margin: int = 230,
) -> np.ndarray:
    """
    Genera el panel de máscaras:
    3 filas (C/M/Y) × 2 columnas (imagen aislada + máscara cerca K).
    """
    ch_list  = ['C', 'M', 'Y']
    cell_h, cell_w = 230, 230
    n_marks  = len(k_marks)
    panel = np.zeros((3 * cell_h, n_marks * 2 * cell_w + n_marks * 6, 3), dtype=np.uint8)

    for row, ch_name in enumerate(ch_list):
        draw_color_bgr = CMY_CROP_RANGES[ch_name].get('color_display', (200, 200, 0))
        diag_data_list = diag_por_canal.get(ch_name, [])
        if not diag_data_list:
            continue

        for mi in range(n_marks):
            if mi >= len(diag_data_list):
                continue
            d      = diag_data_list[mi]
            iso    = d['img_isolated']
            m_near = d['mask_near']
            klx    = d['k_local_cx']
            kly    = d['k_local_cy']
            kscale = k_marks[mi][3]

            iso_draw = iso.copy()
            if cmyk_marks.get(ch_name) and len(cmyk_marks[ch_name]) > mi:
                cx_det = cmyk_marks[ch_name][mi][0]
                cy_det = cmyk_marks[ch_name][mi][1]
                lx_det = int(cx_det) - (int(k_marks[mi][0]) - klx)
                ly_det = int(cy_det) - (int(k_marks[mi][1]) - kly)
                cv2.circle(iso_draw, (lx_det, ly_det), int(40 * kscale), draw_color_bgr, 2)
                cv2.circle(iso_draw, (lx_det, ly_det), 4, draw_color_bgr, -1)
            cv2.drawMarker(iso_draw, (klx, kly), (180, 180, 180), cv2.MARKER_CROSS, 14, 1)

            near_colored = np.zeros_like(iso)
            near_colored[m_near > 0] = draw_color_bgr
            cv2.circle(near_colored, (klx, kly), 80, (80, 80, 80), 1)
            if cmyk_marks.get(ch_name) and len(cmyk_marks[ch_name]) > mi:
                cv2.circle(near_colored, (lx_det, ly_det), int(40 * kscale), draw_color_bgr, 2)

            for col_panel, src in enumerate([iso_draw, near_colored]):
                resized = cv2.resize(src, (cell_w, cell_h))
                col_off = (mi * 2 + col_panel) * cell_w + mi * 6
                row_off = row * cell_h
                panel[row_off:row_off + cell_h, col_off:col_off + cell_w] = resized

            cv2.putText(
                panel,
                f"{ch_name} ({CMY_CROP_RANGES[ch_name]['nombre']})",
                (4, row * cell_h + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                draw_color_bgr, 1, cv2.LINE_AA,
            )

    for mi in range(n_marks):
        for ci, lbl in enumerate(['Imagen aislada', 'Mascara cerca K']):
            col_off = (mi * 2 + ci) * cell_w + mi * 6
            cv2.putText(panel, f'K-{mi} {lbl}', (col_off + 4, 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1, cv2.LINE_AA)

    return panel


def build_result_image(
    img_bgr: np.ndarray,
    cmyk_marks: dict,
    k_marks: list,
    filename: str = '',
    roi_margin: int = 230,
) -> np.ndarray:
    """
    Genera la imagen de resultado: ROI original | ROI anotado con posiciones CMYK.
    """
    mcx, mcy, _, mscale = k_marks[0]
    rx1 = max(int(mcx) - roi_margin, 0)
    ry1 = max(int(mcy) - roi_margin, 0)
    rx2 = min(int(mcx) + roi_margin, img_bgr.shape[1])
    ry2 = min(int(mcy) + roi_margin, img_bgr.shape[0])

    roi_orig = img_bgr[ry1:ry2, rx1:rx2].copy()
    cv2.putText(roi_orig, filename or 'Original', (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

    roi_ann = img_bgr[ry1:ry2, rx1:rx2].copy()
    for ch_name in ['C', 'M', 'Y', 'K']:
        color_bgr  = COLORS_LABEL[ch_name]
        for cx, cy, score, scale in (cmyk_marks.get(ch_name) or [])[:1]:
            if rx1 <= cx <= rx2 and ry1 <= cy <= ry2:
                lx, ly = int(cx) - rx1, int(cy) - ry1
                cv2.circle(roi_ann, (lx, ly), int(40 * scale), color_bgr, 2)
                cv2.circle(roi_ann, (lx, ly), 5, color_bgr, -1)
                cv2.drawMarker(roi_ann, (lx, ly), color_bgr, cv2.MARKER_CROSS, 18, 2)
                if ch_name != 'K' and k_marks:
                    cv2.line(roi_ann, (lx, ly),
                             (int(k_marks[0][0]) - rx1, int(k_marks[0][1]) - ry1),
                             color_bgr, 1, cv2.LINE_AA)
                ox, oy = offsets_label.get(ch_name, (10, -10))
                llx, lly = lx + ox, ly + oy
                lbl = f'{ch_name}  s={score:.2f}'
                (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(roi_ann, (llx - 2, lly - th - 4), (llx + tw + 2, lly + 4), (0, 0, 0), -1)
                cv2.putText(roi_ann, lbl, (llx, lly),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 2, cv2.LINE_AA)

    n_det = sum(1 for v in cmyk_marks.values() if v)
    cv2.putText(roi_ann, f'Resultado — {n_det}/4 canales detectados',
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)

    sep = np.full((roi_orig.shape[0], 4, 3), 200, dtype=np.uint8)
    return np.hstack([roi_orig, sep, roi_ann])


def build_calc_panel(
    img_bgr: np.ndarray,
    cmyk_marks: dict,
    k_marks: list,
    filename: str = '',
    calibration_method: str = 'camera_distance',
    mark_size_mm: float = None,
    camera_distance_mm: float = None,
    mm_per_px: float = None,
) -> np.ndarray:
    """
    Genera el panel de cálculos: desalineamientos respecto a K y distancias en mm.
    """
    image_width_px = img_bgr.shape[1]
    
    # Si no se pasó mm_per_px, calcular con el método por defecto
    if mm_per_px is None:
        if calibration_method == 'mark_size' and mark_size_mm and k_marks:
            mark_size_px = k_marks[0][3] * MARK_DIAMETER_PX   # antes: TEMPLATE_SIZE
            mm_por_px = calculate_mm_per_pixel(
                method='mark_size',
                image_width_px=image_width_px,
                mark_size_mm=mark_size_mm,
                mark_size_px=mark_size_px,
            )
        else:
            mm_por_px = calculate_mm_per_pixel(
                method='camera_distance',
                image_width_px=image_width_px,
                camera_distance_mm=camera_distance_mm,
            )
    else:
        mm_por_px = mm_per_px

    positions = {
        ch: (cmyk_marks[ch][0][0], cmyk_marks[ch][0][1])
        for ch in ['C', 'M', 'Y', 'K']
        if cmyk_marks.get(ch)
    }

    # Usar camera_distance_mm si se proporciona, sino usar el default
    if calibration_method == 'mark_size' and mark_size_mm:
        calibration_text = f'Calibrado con marca de {mark_size_mm} mm'
    else:
        dist = camera_distance_mm if camera_distance_mm is not None else distancia_camara_plano_mm
        calibration_text = (
            f'Dist. camara-plano: {dist} mm  |  Focal: {focal_mm} mm'
        )

    lines = [
        f'Archivo: {filename}',
        f'Factor optico: 1 px = {mm_por_px:.4f} mm  |  {calibration_text}',
        '',
        '--- Desalineamiento respecto a K ---',
    ]

    if k_marks:
        kx, ky = k_marks[0][0], k_marks[0][1]
        for ch in ['C', 'M', 'Y']:
            if positions.get(ch):
                dx_px = positions[ch][0] - kx
                dy_px = positions[ch][1] - ky
                dp    = np.hypot(dx_px, dy_px)
                dx_mm = dx_px * mm_por_px
                dy_mm = dy_px * mm_por_px
                dm    = dp * mm_por_px
                lines.append(
                    f'  {ch}-K:  Dx={dx_mm:+.3f} mm   Dy={dy_mm:+.3f} mm   dist={dm:.3f} mm  ({dp:.1f} px)'
                )
            else:
                lines.append(f'  {ch}: no detectado')

    lines += ['', '--- Distancias entre todos los pares ---']
    pnames = list(positions.keys())
    for i in range(len(pnames)):
        for j in range(i + 1, len(pnames)):
            n1, n2 = pnames[i], pnames[j]
            dx = positions[n1][0] - positions[n2][0]
            dy = positions[n1][1] - positions[n2][1]
            dp = np.hypot(dx, dy)
            dm = dp * mm_por_px
            lines.append(f'  {n1}-{n2}:  {dm:.3f} mm  ({dp:.1f} px)')

    font = cv2.FONT_HERSHEY_SIMPLEX
    lh, pad = 28, 14
    pw = 780
    ph = pad * 2 + lh * (len(lines) + 1)
    panel = np.full((ph, pw, 3), 20, dtype=np.uint8)
    cv2.rectangle(panel, (0, 0), (pw - 1, ph - 1), (60, 60, 60), 2)

    for idx, line in enumerate(lines):
        y = pad + (idx + 1) * lh
        color = (200, 200, 200)
        for ch, bgr in [('C', (255, 255, 0)), ('M', (255, 0, 255)),
                         ('Y', (0, 255, 255)), ('K', (180, 180, 180))]:
            if line.strip().startswith(ch + '-') or line.strip().startswith(ch + ':'):
                color = bgr
                break
        cv2.putText(panel, line, (pad, y), font, 0.52, color, 1, cv2.LINE_AA)

    return panel


def save_all_outputs(
    img_bgr: np.ndarray,
    cmyk_marks: dict,
    diag_por_canal: dict,
    k_marks: list,
    output_dir: str,
    name_no_ext: str,
    filename: str = '',
    roi_margin: int = 230,
    mm_per_px: float = None,
    calibration_method: str = 'camera_distance',
    mark_size_mm: float = None,
    camera_distance_mm: float = None,
) -> dict[str, str]:
    """
    Guarda los 3 archivos JPG de salida y retorna un dict con las rutas.
    """
    os.makedirs(output_dir, exist_ok=True)

    masks_img  = build_masks_panel(img_bgr, cmyk_marks, diag_por_canal, k_marks, roi_margin)
    result_img = build_result_image(img_bgr, cmyk_marks, k_marks, filename, roi_margin)
    calc_img   = build_calc_panel(
        img_bgr, cmyk_marks, k_marks, filename,
        calibration_method=calibration_method,
        mark_size_mm=mark_size_mm,
        camera_distance_mm=camera_distance_mm,
        mm_per_px=mm_per_px,
    )

    paths = {
        'mascaras':    os.path.join(output_dir, f'{name_no_ext}_mascaras.jpg'),
        'resultado':   os.path.join(output_dir, f'{name_no_ext}_resultado.jpg'),
        'calculos_mm': os.path.join(output_dir, f'{name_no_ext}_calculos_mm.jpg'),
    }

    cv2.imwrite(paths['mascaras'],    masks_img)
    cv2.imwrite(paths['resultado'],   result_img)
    cv2.imwrite(paths['calculos_mm'], calc_img)

    return paths
