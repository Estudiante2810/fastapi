"""
Base interface for storage backends.
Implementa esta clase para agregar cualquier nuevo backend (Firebase, S3, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid
import json
import os

@dataclass
class ColorResult:
    """Resultado de detección de un color en la imagen."""
    name: str
    coordinates: dict[str, float]
    confidence: float = 1.0
    hex_value: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisRecord:
    """Registro completo de un análisis de imprenta."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    image_filename: str = ""
    image_path: str = ""
    colors: list[ColorResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class StorageBackend(ABC):
    """
    Interfaz abstracta que deben implementar todos los backends de almacenamiento.
    Cambia el backend sin tocar el resto de tu aplicación.
    """

    @abstractmethod
    def save(self, 
             image_bytes: bytes, 
             filename: str, 
             results: list[ColorResult], 
             output_files: dict | None = None,
             metadata: dict | None = None
    ) -> AnalysisRecord:
        """
        Guarda la imagen y los resultados de detección.

        Args:
            image_bytes: Contenido binario de la imagen.
            filename:    Nombre original del archivo.
            results:     Lista de colores detectados.
            metadata:    Información opcional (cliente, operador, etc.)

        Returns:
            AnalysisRecord con id, rutas y datos guardados.
        """
        ...

    @abstractmethod
    def get(self, record_id: str) -> AnalysisRecord | None:
        """Recupera un registro por su ID."""
        ...

    @abstractmethod
    def list_all(self) -> list[AnalysisRecord]:
        """Lista todos los registros guardados."""
        ...

    @abstractmethod
    def delete(self, record_id: str) -> bool:
        """Elimina un registro. Devuelve True si existía."""
        ...