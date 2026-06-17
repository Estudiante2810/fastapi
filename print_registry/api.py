"""
Ejemplo de integración con FastAPI.
Muestra cómo conectar el módulo de storage al endpoint de análisis.

Ejecutar:
    uvicorn print_registry.api:app --reload
"""

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .storage import AnalysisRecord, ColorResult, LocalStorage

app = FastAPI(title="Print Registry API")

# ─── Configuración del backend ─────────────────────────────────────────────────
# Fase 1: almacenamiento local
storage = LocalStorage(base_dir="print_registry_data")

# Fase 2: cambia SOLO esta línea cuando tengas Firebase listo
# from .storage import FirebaseStorage
# storage = FirebaseStorage(
#     credentials_path="serviceAccountKey.json",
#     bucket_name="tu-proyecto.appspot.com",
# )
# ───────────────────────────────────────────────────────────────────────────────


def run_color_detection(image_bytes: bytes) -> list[ColorResult]:
    """
    REEMPLAZA esta función con tu lógica real de detección.
    Debe devolver una lista de ColorResult.
    """
    return [
        ColorResult(
            name="Cyan",
            coordinates={"x": 120, "y": 340, "width": 50, "height": 30},
            confidence=0.97,
            hex_value="#00AEEF",
        ),
        ColorResult(
            name="Magenta",
            coordinates={"x": 200, "y": 150, "width": 45, "height": 28},
            confidence=0.94,
            hex_value="#EC008C",
        ),
    ]


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/analyze", response_model=dict, summary="Analiza una imagen de imprenta")
async def analyze_image(
    file: UploadFile = File(..., description="Imagen a analizar"),
    job_name: str = Form(default="", description="Nombre del trabajo (opcional)"),
    operator: str = Form(default="", description="Operador (opcional)"),
):
    image_bytes = await file.read()

    # 1. Detectar colores
    results = run_color_detection(image_bytes)

    # 2. Guardar imagen + resultados
    record = storage.save(
        image_bytes=image_bytes,
        filename=file.filename,
        results=results,
        metadata={"job_name": job_name, "operator": operator},
    )

    return _record_to_response(record)


@app.get("/records", summary="Lista todos los análisis guardados")
def list_records():
    records = storage.list_all()
    return [_record_to_response(r) for r in records]


@app.get("/records/{record_id}", summary="Obtiene un análisis por ID")
def get_record(record_id: str):
    record = storage.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return _record_to_response(record)


@app.delete("/records/{record_id}", summary="Elimina un análisis")
def delete_record(record_id: str):
    deleted = storage.delete(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"deleted": record_id}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _record_to_response(record: AnalysisRecord) -> dict:
    return {
        "id": record.id,
        "timestamp": record.timestamp.isoformat(),
        "image_filename": record.image_filename,
        "image_path": record.image_path,
        "colors_detected": len(record.colors),
        "colors": [
            {
                "name": c.name,
                "coordinates": c.coordinates,
                "confidence": c.confidence,
                "hex_value": c.hex_value,
            }
            for c in record.colors
        ],
        "metadata": record.metadata,
    }
