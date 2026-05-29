"""
schemas.py
----------
Modelos Pydantic para request/response de la API de detección CMYK.
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class CalibrationMethod(str, Enum):
    """Método para calcular mm/pixel"""
    CAMERA_DISTANCE = "camera_distance"  # Usar distancia cámara-plano
    MARK_SIZE = "mark_size"               # Usar tamaño conocido del registro

class CMYKChannel(str, Enum):
    """Canales CMYK a analizar"""
    C = "C"
    M = "M"
    Y = "Y"
    K = "K"


class MarkPosition(BaseModel):
    x: int = Field(..., description="Coordenada X del centro de la marca (píxeles)")
    y: int = Field(..., description="Coordenada Y del centro de la marca (píxeles)")
    score: float = Field(..., description="Score de confianza de la detección (0–1)")
    scale: float = Field(..., description="Escala relativa de la plantilla detectada")


class ChannelResult(BaseModel):
    detected: bool
    mark: MarkPosition | None = None
    pixel_count: int = 0


class DetectionResult(BaseModel):
    filename: str
    channels_detected: int = Field(..., description="Número de canales detectados (0–4)")
    C: Optional[ChannelResult] = None
    M: Optional[ChannelResult] = None
    Y: Optional[ChannelResult] = None
    K: Optional[ChannelResult] = None
    output_files: dict[str, str] = Field(
        default_factory=dict,
        description="Rutas a los archivos JPG generados",
    )


class ErrorResponse(BaseModel):
    detail: str
