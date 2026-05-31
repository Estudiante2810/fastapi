# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# En Windows:
.venv\Scripts\activate
# En Linux/Mac:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar localmente
uvicorn main:app --reload


La API estará disponible en `http://localhost:8000`

## Documentación de la API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc