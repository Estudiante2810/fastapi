# Detección de Marcas CMYK - API v3.2.0

API para detectar y medir el desalineamiento de marcas de registro CMYK en imágenes de impresión.

## Requisitos Locales

- Python 3.11+
- pip

## Instalación Local

```bash
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
```

La API estará disponible en `http://localhost:8000`

## Documentación de la API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Despliegue en Render

### Paso 1: Preparar el repositorio Git

```bash
git init
git add .
git commit -m "Initial commit - CMYK Detection API"
```

### Paso 2: Crear un repositorio en GitHub

1. Ve a [GitHub](https://github.com/new) y crea un nuevo repositorio
2. Sigue las instrucciones para pushear tu código

```bash
git remote add origin https://github.com/tu-usuario/tu-repo.git
git branch -M main
git push -u origin main
```

### Paso 3: Conectar a Render

1. Ve a [Render.com](https://render.com/)
2. Inicia sesión con tu cuenta de GitHub
3. Haz clic en **"New +"** y selecciona **"Web Service"**
4. Conecta tu repositorio de GitHub
5. Configura los siguientes valores:

   - **Name**: `fastapi-cmyk-detection` (o tu preferencia)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port 8000`
   - **Plan**: Free (o el que prefieras)

6. Haz clic en **"Deploy"**

### Paso 4: Verificar el despliegue

Una vez que Render haya construido y desplegado tu aplicación:

- Tu API será accesible en: `https://fastapi-cmyk-detection.onrender.com`
- Documentación Swagger: `https://fastapi-cmyk-detection.onrender.com/docs`
- Health check: `https://fastapi-cmyk-detection.onrender.com/health`

## Variables de Entorno

Actualmente el proyecto no requiere variables de entorno específicas. Si necesitas agregar alguna:

1. Ve a tu servicio en Render
2. Ve a **"Environment"**
3. Agrega tus variables

## Solución de Problemas

### La aplicación no inicia
- Verifica los logs en Render
- Asegúrate de que `requirements.txt` contenga todas las dependencias
- Comprueba que `main.py` esté en la raíz del proyecto

### Errores de importación
- Revisa que la estructura de carpetas sea correcta
- Los archivos `__init__.py` deben existir en directorios de paquetes Python

### Timeout en Render
- El plan Free de Render tiene limitaciones
- Considera actualizar a un plan pagado para mejor rendimiento

## Endpoints

- `GET /` - Health check
- `GET /health` - Status de la API
- Ver `/docs` para la documentación completa de endpoints

## Versión

API v3.2.0
