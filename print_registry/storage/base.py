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
    name: str                          # Nombre del color (ej: "Cyan", "PANTONE 485")
    coordinates: dict[str, float]      # {"x": 120, "y": 340, "width": 50, "height": 30}
    confidence: float = 1.0            # Confianza de detección (0.0 - 1.0)
    hex_value: str | None = None       # Color hex opcional (ej: "#00AEEF")
    extra: dict[str, Any] = field(default_factory=dict)  # Metadatos adicionales


@dataclass
class AnalysisRecord:
    """Registro completo de un análisis de imprenta."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    image_filename: str = ""
    image_path: str = ""               # Ruta local o URL remota
    colors: list[ColorResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)  # Info extra (cliente, trabajo, etc.)


class StorageBackend(ABC):
    """
    Interfaz abstracta que deben implementar todos los backends de almacenamiento.
    Cambia el backend sin tocar el resto de tu aplicación.
    """

    @abstractmethod
    def save(self, image_bytes: bytes, filename: str, results: list[ColorResult], metadata: dict | None = None) -> AnalysisRecord:
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

class LocalStorage(StorageBackend):
    def __init__(self, base_dir: str = "print_registry_data"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def save(self, image_bytes, filename, results, metadata=None) -> AnalysisRecord:
        record = AnalysisRecord(
            image_filename=filename,
            colors=results,
            metadata=metadata or {},
        )
        # Guarda imagen
        img_path = os.path.join(self.base_dir, record.id + "_" + filename)
        with open(img_path, "wb") as f:
            f.write(image_bytes)
        record.image_path = img_path
        # Guarda JSON
        json_path = os.path.join(self.base_dir, record.id + ".json")
        with open(json_path, "w") as f:
            json.dump({"id": record.id, "filename": filename, "metadata": metadata}, f)
        return record

    def get(self, record_id):
        # Implementación básica
        return None

    def list_all(self):
        return []

    def delete(self, record_id):
        return False