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
from app.core.output_builder import save_all_outputs, calcular_distancias_a_k
from app.schemas.detection import DetectionResult, ChannelResult, MarkPosition, AdjustRequest
from app.schemas.calibration import CalibrationMethod, CMYKChannel


from print_registry.storage.base import ColorResult
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

    distances_to_k = calcular_distancias_a_k(cmyk_marks, k_marks, mm_per_px)

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
    record = storage.save(
        image_bytes=raw,
        filename=filename,
        results=color_results,
        output_files=output_files,
        metadata={
            "roi_margin": roi_margin,
            "calibration_method": calibration_method.value,
            "mm_per_px": mm_per_px,
            "camera_distance_mm": camera_distance_mm,
            "mark_size_mm": mark_size_mm,
        },
    )
    id = record.id
    
    channels_detected = sum(
        1 for ch in channels_list if cmyk_marks.get(ch)
    )



    return DetectionResult(
        id=record.id,
        mm_per_px = mm_per_px,
        filename=filename,
        channels_detected=channels_detected,
        C=_build_channel_result('C', cmyk_marks, diag_por_canal) if 'C' in channels_list else None,
        M=_build_channel_result('M', cmyk_marks, diag_por_canal) if 'M' in channels_list else None,
        Y=_build_channel_result('Y', cmyk_marks, diag_por_canal) if 'Y' in channels_list else None,
        K=_build_channel_result('K', cmyk_marks, diag_por_canal),  # K siempre se incluye
        distances_to_k=distances_to_k,
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

@router.get(
    "/history",
    summary="Lista todos los análisis pasados",
)
async def get_history():
    """Devuelve todos los registros guardados, más recientes primero."""
    records = storage.list_all()
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat(),
            "image_filename": r.image_filename,
            "colors": [
                {
                    "name": c.name,
                    "coordinates": c.coordinates,
                    "confidence": c.confidence,
                    "hex_value": c.hex_value,
                    "extra": c.extra,
                }
                for c in r.colors
            ],
            "metadata": r.metadata,
        }
        for r in records
    ]


@router.get(
    "/history/{record_id}",
    summary="Obtiene el detalle de un análisis pasado por ID",
)
async def get_history_detail(record_id: str):
    record = storage.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Registro no encontrado: {record_id}")
    return {
        "id": record.id,
        "timestamp": record.timestamp.isoformat(),
        "image_filename": record.image_filename,
        "colors": [
            {
                "name": c.name,
                "coordinates": c.coordinates,
                "confidence": c.confidence,
                "hex_value": c.hex_value,
                "extra": c.extra,
            }
            for c in record.colors
        ],
        "metadata": record.metadata,
    }


@router.get(
    "/history/{record_id}/images",
    summary="Lista todas las imágenes guardadas de un análisis pasado",
)
async def list_history_images(record_id: str):
    """Devuelve los nombres de todos los archivos en la carpeta image_path."""
    record = storage.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Registro no encontrado: {record_id}")

    folder = record.image_path
    if not folder or not os.path.isdir(folder):
        raise HTTPException(status_code=404, detail="Carpeta de imágenes no encontrada.")

    filenames = sorted(
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
    )
    return {"id": record_id, "filenames": filenames}

@router.get(
    "/history/{record_id}/images/{filename}",
    summary="Descarga una imagen específica de un análisis pasado",
    response_class=FileResponse,
)
async def get_history_image(record_id: str, filename: str):
    """Sirve un archivo puntual dentro de la carpeta image_path."""
    record = storage.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Registro no encontrado: {record_id}")

    folder = record.image_path
    if not folder or not os.path.isdir(folder):
        raise HTTPException(status_code=404, detail="Carpeta de imágenes no encontrada.")

    # Evitar path traversal (ej: ../../etc/passwd)
    safe_name = os.path.basename(filename)
    file_path = os.path.join(folder, safe_name)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {filename}")

    return FileResponse(file_path, media_type="image/jpeg", filename=safe_name)



@router.post(
    "/{record_id}/adjust",
    summary="Ajusta manualmente las posiciones de los registros y recalcula distancias",
)
async def adjust_positions(record_id: str, body: AdjustRequest):
    import cv2
    import numpy as np
    from app.core.output_builder import build_result_image, build_calc_panel

    record = storage.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Registro no encontrado: {record_id}")

    metadata = record.metadata or {}
    mm_per_px = metadata.get("mm_per_px")
    roi_margin = metadata.get("roi_margin", 230)
    calibration_method = metadata.get("calibration_method", "camera_distance")
    camera_distance_mm = metadata.get("camera_distance_mm")
    mark_size_mm = metadata.get("mark_size_mm")

    if mm_per_px is None:
        raise HTTPException(status_code=422, detail="mm_per_px no disponible en el registro original")

    # Cargar imagen original
    img_folder = record.image_path
    if not img_folder or not os.path.isdir(img_folder):
        raise HTTPException(status_code=404, detail="Carpeta de imagen original no encontrada")
    
    img_path = os.path.join(img_folder, record.image_filename)
    if not os.path.isfile(img_path):
        raise HTTPException(status_code=404, detail="Imagen original no encontrada")
    
    img_bgr = cv2.imread(img_path)
    if img_bgr is None:
        raise HTTPException(status_code=500, detail="No se pudo decodificar la imagen original")

    # Reconstruir cmyk_marks con posiciones ajustadas
    cmyk_marks = {}
    for ch in ['C', 'M', 'Y', 'K']:
        if ch in body.positions:
            pos = body.positions[ch]
            # Buscar score y scale original del color correspondiente
            orig_score = 1.0
            orig_scale = 1.0
            for c in record.colors:
                if c.name == ch:
                    orig_score = c.confidence
                    orig_scale = c.extra.get("scale", 1.0)
                    break
            cmyk_marks[ch] = [(pos.x, pos.y, orig_score, orig_scale)]

    # Construir k_marks desde la posición K ajustada
    k_marks = []
    if 'K' in cmyk_marks:
        kx, ky, ks, kscale = cmyk_marks['K'][0]
        k_marks = [(kx, ky, ks, kscale)]
    else:
        raise HTTPException(status_code=422, detail="Se requiere posición K")

    # Generar nuevas imágenes
    result_img = build_result_image(img_bgr, cmyk_marks, k_marks, record.image_filename, roi_margin)
    calc_img = build_calc_panel(
        img_bgr, cmyk_marks, k_marks, record.image_filename,
        calibration_method=calibration_method,
        mark_size_mm=mark_size_mm,
        camera_distance_mm=camera_distance_mm,
        mm_per_px=mm_per_px,
    )

    distances_to_k = calcular_distancias_a_k(cmyk_marks, k_marks, mm_per_px)

    # Guardar en resultados/ con nombre basado en record_id
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    adj_result_path = os.path.join(OUTPUT_DIR, f"{record_id}_ajustado_resultado.jpg")
    adj_calc_path = os.path.join(OUTPUT_DIR, f"{record_id}_ajustado_calculos_mm.jpg")
    cv2.imwrite(adj_result_path, result_img)
    cv2.imwrite(adj_calc_path, calc_img)

    output_files = {
        "resultado": adj_result_path,
        "calculos_mm": adj_calc_path,
    }

    # Construir ChannelResults con confianza 1.0 (ajuste manual)
    def make_ch(ch):
        if ch not in body.positions:
            return None
        p = body.positions[ch]
        return ChannelResult(
            detected=True,
            mark=MarkPosition(x=p.x, y=p.y, score=1.0, scale=1.0),
            pixel_count=0,
        )

    return DetectionResult(
        id=record_id,
        mm_per_px=mm_per_px,
        filename=record.image_filename,
        channels_detected=len([ch for ch in ['C', 'M', 'Y', 'K'] if ch in body.positions and ch != 'K']),
        C=make_ch('C'),
        M=make_ch('M'),
        Y=make_ch('Y'),
        K=make_ch('K'),
        distances_to_k=distances_to_k,
        output_files=output_files,
    )