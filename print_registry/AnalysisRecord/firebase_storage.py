"""
Backend de almacenamiento FIREBASE.
Guarda imágenes en Firebase Storage y resultados en Firestore.

Para activar este backend instala:
    pip install firebase-admin

Y configura tu archivo de credenciales de servicio desde:
    https://console.firebase.google.com → Configuración del proyecto → Cuentas de servicio
"""

from .base import AnalysisRecord, ColorResult, StorageBackend


class FirebaseStorage(StorageBackend):
    """
    Backend para Firebase: Storage (imágenes) + Firestore (resultados).

    Uso:
        storage = FirebaseStorage(
            credentials_path="serviceAccountKey.json",
            bucket_name="tu-proyecto.appspot.com",
            collection="print_analyses",
        )
    """

    COLLECTION = "print_analyses"

    def __init__(
        self,
        credentials_path: str,
        bucket_name: str,
        collection: str = COLLECTION,
    ):
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore, storage
        except ImportError:
            raise ImportError(
                "Instala firebase-admin para usar este backend:\n"
                "  pip install firebase-admin"
            )

        # Inicializar Firebase solo una vez
        if not firebase_admin._apps:
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})

        self._db = firestore.client()
        self._bucket = storage.bucket()
        self._collection = collection

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
        from datetime import datetime
        import uuid

        record = AnalysisRecord(
            image_filename=filename,
            colors=results,
            metadata=metadata or {},
        )

        # 1. Subir imagen a Firebase Storage
        blob_path = f"images/{record.id}_{filename}"
        blob = self._bucket.blob(blob_path)
        blob.upload_from_string(image_bytes, content_type=self._guess_mime(filename))
        blob.make_public()
        record.image_path = blob.public_url

        # 2. Guardar documento en Firestore
        doc_data = self._record_to_dict(record)
        self._db.collection(self._collection).document(record.id).set(doc_data)

        print(f"[FirebaseStorage] ✓ Guardado: {record.id}")
        print(f"  Imagen   → {record.image_path}")
        print(f"  Firestore → {self._collection}/{record.id}")

        return record

    # ------------------------------------------------------------------
    # Leer
    # ------------------------------------------------------------------

    def get(self, record_id: str) -> AnalysisRecord | None:
        doc = self._db.collection(self._collection).document(record_id).get()
        if not doc.exists:
            return None
        return self._dict_to_record(doc.to_dict())

    def list_all(self) -> list[AnalysisRecord]:
        docs = (
            self._db.collection(self._collection)
            .order_by("timestamp", direction="DESCENDING")
            .stream()
        )
        return [self._dict_to_record(d.to_dict()) for d in docs]

    # ------------------------------------------------------------------
    # Eliminar
    # ------------------------------------------------------------------

    def delete(self, record_id: str) -> bool:
        doc_ref = self._db.collection(self._collection).document(record_id)
        doc = doc_ref.get()
        if not doc.exists:
            return False

        # Eliminar imagen en Storage
        data = doc.to_dict()
        blob_path = f"images/{record_id}_{data.get('image_filename', '')}"
        blob = self._bucket.blob(blob_path)
        if blob.exists():
            blob.delete()

        doc_ref.delete()
        print(f"[FirebaseStorage] 🗑 Eliminado: {record_id}")
        return True

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _guess_mime(self, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower()
        return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "tiff": "image/tiff"}.get(ext, "application/octet-stream")

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
        from datetime import datetime
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
