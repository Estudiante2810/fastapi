"""
main.py
-------
Punto de entrada de la aplicación FastAPI — Detección de marcas CMYK v3.2
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path

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

# Servir archivos estáticos (HTML, CSS, JS)
static_dir = Path(__file__).parent / "app" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", tags=["health"])
def root():
    """Sirve la página principal del frontend."""
    static_dir = Path(__file__).parent / "app" / "static"
    html_file = static_dir / "index.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    return {"status": "ok", "version": "3.2.0"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
