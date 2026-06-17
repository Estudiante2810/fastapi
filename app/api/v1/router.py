"""
router.py
---------
Endpoints de FastAPI para detección de marcas CMYK.
"""

import os
import io
import cv2
import numpy as np

from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.config import APPLY_SHARPENING, SHARPENING_STRENGTH, calculate_mm_per_pixel
from app.core.image_utils import (
    create_crosshair_template,
    sharpen_image,
)
from app.core.detection import procesar_imagen_completa
from app.core.output_builder import save_all_outputs
from app.schemas.detection import DetectionResult, ChannelResult, MarkPosition
from app.schemas.calibration import CalibrationMethod, CMYKChannel

from print_registry.storage.base import ColorResult, AnalysisRecord, StorageBackend
from print_registry.AnalysisRecord.local_storage import LocalStorage

router = APIRouter(prefix="/detection", tags=["detection"])

# Plantilla global (se crea una vez al cargar el módulo)
_TEMPLATE = create_crosshair_template(
    size=101, ring_radius=40, ring_thickness=8,
    cross_thickness=10, cross_length=90,
)

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "resultados")

storage = LocalStorage(base_dir="print_registry_data")

def _decode_image(file_bytes: bytes) -> np.ndarray:
    """Decodifica bytes de imagen a array BGR de OpenCV."""
    arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="No se pudo decodificar la imagen.")
    return img


def _build_channel_result(ch: str, cmyk_marks: dict, diag_por_canal: dict) -> ChannelResult:
    marks = cmyk_marks.get(ch, [])
    px_count = 0
    if diag_por_canal and ch in diag_por_canal and diag_por_canal[ch]:
        px_count = diag_por_canal[ch][0].get('px_count', 0)
    if marks:
        cx, cy, score, scale = marks[0]
        return ChannelResult(
            detected=True,
            mark=MarkPosition(x=int(cx), y=int(cy), score=round(score, 4), scale=round(scale, 3)),
            pixel_count=px_count,
        )
    return ChannelResult(detected=False, pixel_count=px_count)


@router.post(
    "/analyze",
    response_model=DetectionResult,
    summary="Analiza una imagen y detecta marcas CMYK de registro",
)
async def analyze_image(
    file: UploadFile = File(..., description="Imagen JPG/PNG a analizar"),
    save_outputs: bool = Query(True, description="Si True, guarda los 3 JPG de salida"),
    roi_margin: int = Query(230, description="Margen ROI alrededor de la marca K (px)"),
    min_pixels: int = Query(1000, description="Mínimo de píxeles para considerar canal detectado"),
    calibration_method: CalibrationMethod = Query(
        CalibrationMethod.CAMERA_DISTANCE,
        description="Método para calcular mm/pixel"
    ),
    mark_size_mm: float = Query(None, description="Tamaño conocido del registro en mm (si usa MARK_SIZE)"),
    camera_distance_mm: float = Query(None, description="Distancia cámara-plano en mm (si usa CAMERA_DISTANCE)"), 
    channels: list[CMYKChannel] = Query(
        [CMYKChannel.C, CMYKChannel.M, CMYKChannel.Y],
        description="Canales C, M, Y a analizar (K siempre se detecta automáticamente)"
    ),
):
    """
    Sube una imagen, ejecuta el pipeline de detección CMYK v3.2 y devuelve
    las posiciones detectadas de cada canal junto con las rutas de los archivos
    generados (máscaras, resultado anotado y cálculos en mm).
    """
    raw = await file.read()
    img_bgr = _decode_image(raw)

    filename    = file.filename or "imagen.jpg"
    name_no_ext = os.path.splitext(filename)[0]

    # Sharpening opcional
    if APPLY_SHARPENING:
        img_bgr = sharpen_image(img_bgr, strength=SHARPENING_STRENGTH)

    # Pipeline
    cmyk_marks, diag_por_canal, k_marks = procesar_imagen_completa(
        img_bgr, _TEMPLATE,
        roi_margin=roi_margin,
        search_radius=110,
        min_pixels=min_pixels,
        channels=channels,  # Pasar los canales seleccionados
    )

    if cmyk_marks is None:
        raise HTTPException(status_code=422, detail="No se detectaron marcas K en la imagen.")

    # Calcular factor óptico según método elegido
    mm_per_px = None
    if calibration_method == CalibrationMethod.MARK_SIZE:
        if not mark_size_mm:
            raise HTTPException(
                status_code=422,
                detail="mark_size_mm requerido cuando calibration_method='mark_size'"
            )
        # k_marks[0] = (cx, cy, score, scale)
        # Tamaño del registro detectado en píxeles
        mark_size_px = 101 * k_marks[0][3]  # template_size * scale
        mm_per_px = calculate_mm_per_pixel(
            calibration_method.value,
            img_bgr.shape[1],
            mark_size_mm=mark_size_mm,
            mark_size_px=mark_size_px,
        )
    else:  # CAMERA_DISTANCE
        mm_per_px = calculate_mm_per_pixel(
            calibration_method.value,
            img_bgr.shape[1],
            camera_distance_mm=camera_distance_mm, 
        )

    # Filtrar canales solicitados
    channels_list = [ch.value for ch in channels]
    
    # Guardar outputs opcionales
    output_files: dict[str, str] = {}
    if save_outputs:
        output_files = save_all_outputs(
            img_bgr, cmyk_marks, diag_por_canal or {}, k_marks,
            output_dir=OUTPUT_DIR,
            name_no_ext=name_no_ext,
            filename=filename,
            roi_margin=roi_margin,
            mm_per_px=mm_per_px,
            calibration_method=calibration_method.value,
            mark_size_mm=mark_size_mm,
            camera_distance_mm=camera_distance_mm,  
        )

    color_results = [
        ColorResult(
            name=ch,
            coordinates={
                "x": int(cmyk_marks[ch][0][0]),
                "y": int(cmyk_marks[ch][0][1]),
            },
            confidence=round(float(cmyk_marks[ch][0][2]), 4),
            extra={"scale": round(float(cmyk_marks[ch][0][3]), 3)},
        )
        for ch in ["C", "M", "Y", "K"]
        if cmyk_marks.get(ch)
    ]
    storage.save(
        image_bytes=raw,
        filename=filename,
        results=color_results,
        metadata={
            "roi_margin": roi_margin,
            "calibration_method": calibration_method.value,
            "mm_per_px": mm_per_px,
        },
    )
    
    channels_detected = sum(
        1 for ch in channels_list if cmyk_marks.get(ch)
    )

    return DetectionResult(
        filename=filename,
        channels_detected=channels_detected,
        C=_build_channel_result('C', cmyk_marks, diag_por_canal) if 'C' in channels_list else None,
        M=_build_channel_result('M', cmyk_marks, diag_por_canal) if 'M' in channels_list else None,
        Y=_build_channel_result('Y', cmyk_marks, diag_por_canal) if 'Y' in channels_list else None,
        K=_build_channel_result('K', cmyk_marks, diag_por_canal),  # K siempre se incluye
        output_files=output_files,
    )


@router.get(
    "/output/{filename}",
    summary="Descarga un archivo de resultado generado",
    response_class=FileResponse,
)
async def get_output_file(filename: str):
    """Descarga uno de los archivos JPG generados por `/analyze`."""
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {filename}")
    return FileResponse(path, media_type="image/jpeg", filename=filename)
