"""
main.py
-------
Punto de entrada de la aplicación FastAPI — Detección de marcas CMYK v3.2
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as detection_router

app = FastAPI(
    title="Detección de Marcas CMYK",
    description=(
        "API para detectar y medir el desalineamiento de marcas de registro "
        "CMYK en imágenes de impresión. Versión 3.2."
    ),
    version="3.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detection_router, prefix="/api/v1")


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "version": "3.2.0"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
