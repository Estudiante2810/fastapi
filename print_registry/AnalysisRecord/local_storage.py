"""
Backend de almacenamiento LOCAL.
Guarda imágenes en disco y resultados en archivos JSON.
No requiere ninguna dependencia externa.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from print_registry.storage.base import AnalysisRecord, ColorResult, StorageBackend


class LocalStorage(StorageBackend):
    """
    Guarda todo en el sistema de archivos local.

    Estructura de directorios:
        base_dir/
        ├── images/          ← imágenes originales
        │   └── {id}_{filename}
        └── results/         ← un JSON por análisis
            └── {id}.json
    """

    def __init__(self, base_dir: str = "print_registry_data"):
        self.base_dir = Path(base_dir)
        self.images_dir = self.base_dir / "images"
        self.results_dir = self.base_dir / "results"

        # Crear directorios si no existen
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------

    def save(
        self,
        image_bytes: bytes,
        filename: str,
        results: list[ColorResult],
        metadata: dict | None = None,
    ) -> AnalysisRecord:
        """Guarda la imagen en disco y los resultados en un JSON."""

        record = AnalysisRecord(
            image_filename=filename,
            colors=results,
            metadata=metadata or {},
        )

        # 1. Guardar imagen con el ID como prefijo para evitar colisiones
        safe_filename = f"{record.id}_{filename}"
        image_path = self.images_dir / safe_filename
        image_path.write_bytes(image_bytes)
        record.image_path = str(image_path)

        # 2. Serializar y guardar el JSON de resultados
        result_path = self.results_dir / f"{record.id}.json"
        result_path.write_text(
            json.dumps(self._record_to_dict(record), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"[LocalStorage] ✓ Guardado: {record.id}")
        print(f"  Imagen   → {image_path}")
        print(f"  Results  → {result_path}")

        return record

    # ------------------------------------------------------------------
    # Leer
    # ------------------------------------------------------------------

    def get(self, record_id: str) -> AnalysisRecord | None:
        """Carga un registro desde su JSON."""
        result_path = self.results_dir / f"{record_id}.json"
        if not result_path.exists():
            return None
        data = json.loads(result_path.read_text(encoding="utf-8"))
        return self._dict_to_record(data)

    def list_all(self) -> list[AnalysisRecord]:
        """Lista todos los registros ordenados del más reciente al más antiguo."""
        records = []
        for path in sorted(self.results_dir.glob("*.json"), reverse=True):
            data = json.loads(path.read_text(encoding="utf-8"))
            records.append(self._dict_to_record(data))
        return records

    # ------------------------------------------------------------------
    # Eliminar
    # ------------------------------------------------------------------

    def delete(self, record_id: str) -> bool:
        """Elimina JSON e imagen asociada."""
        result_path = self.results_dir / f"{record_id}.json"
        if not result_path.exists():
            return False

        # Leer para saber qué imagen borrar
        data = json.loads(result_path.read_text(encoding="utf-8"))
        image_path = Path(data.get("image_path", ""))
        if image_path.exists():
            image_path.unlink()

        result_path.unlink()
        print(f"[LocalStorage] 🗑 Eliminado: {record_id}")
        return True

    # ------------------------------------------------------------------
    # Utilidades de serialización
    # ------------------------------------------------------------------

    def _record_to_dict(self, record: AnalysisRecord) -> dict:
        return {
            "id": record.id,
            "timestamp": record.timestamp.isoformat(),
            "image_filename": record.image_filename,
            "image_path": record.image_path,
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

    def _dict_to_record(self, data: dict) -> AnalysisRecord:
        return AnalysisRecord(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            image_filename=data["image_filename"],
            image_path=data["image_path"],
            colors=[
                ColorResult(
                    name=c["name"],
                    coordinates=c["coordinates"],
                    confidence=c.get("confidence", 1.0),
                    hex_value=c.get("hex_value"),
                    extra=c.get("extra", {}),
                )
                for c in data.get("colors", [])
            ],
            metadata=data.get("metadata", {}),
        )
