# Sistema de detección y medición de registro CMYK

Aplicación web basada en visión computacional para detectar marcas de registro de impresión CMYK y medir el desalineamiento de los registros cian, magenta y amarillo con respecto al registro negro (K).

El sistema está diseñado como una herramienta de asistencia para el operador de prensa. Recibe una imagen capturada por cámara, localiza las marcas de registro, calcula sus posiciones relativas y presenta los resultados en píxeles y milímetros.

## 1. Objetivo del sistema

### 1.1 Objetivo general

Desarrollar un sistema de asistencia basado en visión computacional capaz de detectar y medir el error de registro en impresiones CMYK mediante el análisis de las marcas de registro, utilizando el registro negro como referencia, con el fin de generar información objetiva que oriente al prensista en la corrección manual del desalineamiento de los registros de color.

> Estado: **parcialmente cumplido**. El sistema detecta, mide y permite ajustar manualmente las posiciones, pero todavía no genera instrucciones automáticas para los controles mecánicos de la máquina.

### 1.2 Objetivos específicos

1. **Diseñar una aplicación que guíe al usuario en la captura de imágenes óptimas mediante una cámara fija.**

   **Cumplimiento parcial.** La interfaz permite activar la cámara, capturar una imagen y también cargar una imagen desde el equipo. La caja física mantiene la cámara aproximadamente a 100 mm de los registros, pero el software no verifica por sí mismo la distancia ni la calidad óptica de la captura.

2. **Desarrollar un algoritmo capaz de identificar la forma de la marca de registro y localizar las posiciones de los registros de color.**

   **Cumplido.** El sistema detecta la marca K mediante template matching multiescala y localiza C, M y Y mediante máscaras de color, análisis en espacios HSV/LAB/BGR, operaciones morfológicas, centroide ponderado y mediana ponderada.

3. **Calcular el desplazamiento relativo de C, M y Y con respecto a K.**

   **Cumplido.** La API devuelve desplazamientos en los ejes X e Y y la distancia total respecto al registro K.

4. **Relacionar las medidas en píxeles con dimensiones físicas reales.**

   **Cumplido.** El sistema incluye calibración mediante distancia cámara-plano y mediante el tamaño conocido de la marca de registro.

5. **Estimar la relación entre las pulsaciones de los controles mecánicos y el desplazamiento observado.**

   **No implementado actualmente.** El proyecto calcula el desplazamiento de la impresión, pero aún no contiene un modelo experimental que relacione milímetros de desplazamiento con pulsaciones o pasos mecánicos de la máquina.

6. **Generar recomendaciones sobre la dirección y magnitud del ajuste requerido.**

   **No implementado automáticamente.** La interfaz permite ajustar manualmente las posiciones y visualizar las distancias, pero todavía no genera instrucciones como “mover el registro C hacia la izquierda X pulsaciones”.

7. **Evaluar el desempeño mediante métricas de precisión en detección y medición.**

   **Parcialmente cumplido.** Se realizaron pruebas con conjuntos de imágenes y se registraron fallos de detección. Sin embargo, el repositorio todavía no incluye una suite automatizada con métricas reproducibles de precisión, recall, error medio y desviación de la medición.

## 2. Flujo de procesamiento

El procesamiento principal sigue estas etapas:

1. El usuario captura una imagen desde la cámara web o selecciona un archivo de imagen.
2. La imagen se envía mediante `POST /api/v1/detection/analyze`.
3. El backend decodifica la imagen usando OpenCV y la convierte al formato BGR.
4. Se aplica preprocesamiento en LAB con CLAHE para mejorar el contraste.
5. Se genera una plantilla sintética de la marca de registro, formada por un círculo y una cruz.
6. Se detecta la marca negra K mediante template matching a múltiples escalas.
7. Se utiliza K como referencia espacial para construir una región de interés (ROI).
8. Dentro de la ROI se procesan los canales C, M y Y seleccionados.
9. Para cada canal se aplican rangos HSV y máscaras complementarias LAB/BGR según el color.
10. Se normaliza opcionalmente el fondo blanco y se excluyen zonas grises o poco cromáticas.
11. Se aplican operaciones morfológicas de cierre y apertura para limpiar las máscaras.
12. La posición del registro se calcula mediante template matching, centroide ponderado y mediana ponderada.
13. Se calcula la conversión de píxeles a milímetros.
14. Se calculan `dx`, `dy` y la distancia respecto a K.
15. Se generan imágenes de resultado, máscaras y paneles de cálculo.
16. Se guarda la imagen original y los metadatos en el historial local.
17. El usuario puede visualizar el resultado, consultar el historial y ajustar posiciones manualmente.

## 3. Tecnologías utilizadas

### Software

- Python 3.11.
- FastAPI para la API web.
- Uvicorn como servidor ASGI.
- OpenCV para lectura, procesamiento y análisis de imágenes.
- NumPy para operaciones numéricas y manipulación de matrices.
- Matplotlib para generar paneles de diagnóstico.
- Pydantic para validación de solicitudes y respuestas.
- HTML, CSS y JavaScript para la interfaz web.
- JSON y almacenamiento local en archivos para conservar el historial.
- Render para el despliegue del servicio web.

### Hardware de captura

- Cámara USB EMEET C950 con resolución 4K.
- Luz BG-01 para mantener una iluminación controlada.
- Caja física de aproximadamente 150 mm.
- La cámara se posiciona aproximadamente a 100 mm de las marcas de registro.

La configuración física busca mantener constante la distancia cámara-plano, la iluminación y el campo de visión para que la calibración y los rangos de color sean reproducibles.

## 4. Estructura del proyecto

```text
.
├── main.py                         # Entrada de la aplicación FastAPI
├── requirements.txt                # Dependencias Python
├── render.yaml                     # Configuración de despliegue en Render
├── Procfile                        # Comando de inicio del servidor
├── app/
│   ├── api/v1/router.py            # Endpoints de detección e historial
│   ├── core/config.py              # Parámetros ópticos y de detección
│   ├── core/image_utils.py         # Preprocesamiento y template matching
│   ├── core/output_builder.py      # Imágenes y paneles de salida
│   ├── core/detection/             # Pipeline de detección CMYK
│   ├── schemas/                    # Modelos Pydantic y enumeraciones
│   └── static/                     # Interfaz HTML, CSS y JavaScript
├── print_registry/
│   ├── storage/base.py             # Interfaz abstracta de almacenamiento
│   └── AnalysisRecord/             # Implementación de almacenamiento local
└── docs/diagramas.md               # Diagramas Mermaid del sistema
```

## 5. API principal

### Analizar una imagen

```http
POST /api/v1/detection/analyze
Content-Type: multipart/form-data
```

Parámetro obligatorio:

- `file`: imagen JPG, JPEG o PNG.

Parámetros opcionales principales:

- `save_outputs`: guarda las imágenes de salida.
- `calibration_method`: `camera_distance` o `mark_size`.
- `camera_distance_mm`: distancia cámara-plano.
- `mark_size_mm`: tamaño conocido de la marca.
- `channels`: canales a analizar, normalmente `C`, `M` y `Y`.
- `roi_margin`: margen de la región de interés.
- `min_pixels`: cantidad mínima de píxeles para aceptar un canal.

Otros endpoints disponibles:

| Método | Ruta | Función |
|---|---|---|
| `GET` | `/health` | Verifica que el servidor esté activo |
| `GET` | `/` | Sirve la interfaz web principal |
| `POST` | `/api/v1/detection/analyze` | Analiza una imagen |
| `GET` | `/api/v1/detection/history` | Lista análisis anteriores |
| `GET` | `/api/v1/detection/history/{id}` | Consulta un análisis específico |
| `GET` | `/api/v1/detection/history/{id}/images` | Lista imágenes de un análisis |
| `GET` | `/api/v1/detection/history/{id}/images/{filename}` | Descarga una imagen histórica |
| `POST` | `/api/v1/detection/{id}/adjust` | Ajusta manualmente las posiciones |
| `GET` | `/docs` | Documentación Swagger |
| `GET` | `/redoc` | Documentación ReDoc |

## 6. Ejemplo de respuesta

```json
{
  "id": "7d4f8a3f-1cc0-4d97-9f2d-7c9d9c2b6c55",
  "mm_per_px": 0.0214,
  "filename": "muestra_01.jpg",
  "channels_detected": 3,
  "C": {
    "detected": true,
    "mark": {
      "x": 1240,
      "y": 815,
      "score": 0.873,
      "scale": 1.12
    },
    "pixel_count": 2450
  },
  "M": {
    "detected": true,
    "mark": {
      "x": 1248,
      "y": 811,
      "score": 0.841,
      "scale": 1.11
    },
    "pixel_count": 2210
  },
  "Y": {
    "detected": true,
    "mark": {
      "x": 1236,
      "y": 820,
      "score": 0.806,
      "scale": 1.1
    },
    "pixel_count": 1980
  },
  "K": {
    "detected": true,
    "mark": {
      "x": 1240,
      "y": 815,
      "score": 0.932,
      "scale": 1.12
    },
    "pixel_count": 0
  },
  "distances_to_k": {
    "C": {
      "detected": true,
      "dx_mm": 0.171,
      "dy_mm": -0.086,
      "dist_mm": 0.191,
      "dist_px": 8.94
    },
    "M": {
      "detected": true,
      "dx_mm": 0.171,
      "dy_mm": -0.086,
      "dist_mm": 0.191,
      "dist_px": 8.94
    },
    "Y": {
      "detected": true,
      "dx_mm": -0.086,
      "dy_mm": 0.107,
      "dist_mm": 0.137,
      "dist_px": 6.4
    }
  },
  "output_files": {
    "resultado": "resultado.jpg",
    "mascaras": "mascaras.jpg",
    "calculos_mm": "calculos_mm.jpg"
  }
}
```

Los valores del ejemplo son ilustrativos. Los resultados reales dependen de la imagen, la iluminación, la escala de la marca y el método de calibración utilizado. En la implementación actual, `output_files` puede contener rutas del almacenamiento del servidor; para una versión pública conviene transformarlas en URLs de descarga.

## 7. Instalación y ejecución

### Crear el entorno virtual

```bash
python -m venv .venv
```

### Activar el entorno virtual

En Windows:

```powershell
.venv\Scripts\activate
```

En Linux o macOS:

```bash
source .venv/bin/activate
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```

### Ejecutar localmente

```bash
uvicorn main:app --reload
```

La aplicación estará disponible en:

- Interfaz: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Salud del servicio: `http://localhost:8000/health`

## 8. Limitaciones actuales

### Sensibilidad a la superposición de registros

Una parte de los fallos de detección se relaciona con la superposición entre registros de color. En las pruebas reportadas, fallaron 40 de 500 imágenes, equivalente a aproximadamente 8 %, y 81 de 1000 imágenes, equivalente a aproximadamente 8,1 %.

En estos casos, la superposición reduce la cantidad de píxeles visibles de un color particular. Cuando los píxeles restantes son insuficientes, la máscara de color no alcanza una forma consistente para localizar la marca. Este comportamiento no necesariamente representa un error en la clasificación del color, sino una limitación de la información visible en la imagen.

### Restricciones de memoria durante el procesamiento por lotes

El procesamiento de imágenes 4K a gran escala, especialmente en lotes de 1000 imágenes, puede superar la memoria disponible del equipo. Las ejecuciones prolongadas produjeron errores de tipo `Insufficient memory`.

Para completar los análisis fue necesario utilizar mecanismos de checkpointing del caché, reducir el espacio de búsqueda multiescala y reiniciar el proceso en ejecuciones prolongadas. Esto indica que el sistema funciona mejor con procesamiento por lotes pequeños o con una estrategia de procesamiento y liberación de memoria entre imágenes.

### Dependencia de una cámara específica

Las recomendaciones de captura están condicionadas por la cámara USB EMEET C950 4K utilizada durante el desarrollo. Sus características, como el sensor pequeño, la longitud focal fija, el campo de visión aproximado de 70 grados y la sensibilidad de píxel propia de una cámara USB 4K de consumo, pueden afectar los resultados.

Por esta razón, la generalización a otras cámaras requiere una validación adicional de los rangos de color, la escala de la plantilla y la calibración óptica.

### Condiciones controladas de iluminación y distancia

El algoritmo depende de una iluminación relativamente estable y de una distancia cámara-plano conocida. Cambios importantes en sombras, reflejos, inclinación, distancia o balance de blancos pueden modificar los valores HSV y LAB y producir falsos positivos o fallos de detección.

### Calibración aproximada

La conversión de píxeles a milímetros depende de los parámetros de la cámara, la distancia cámara-plano y un factor de corrección experimental. Para obtener mayor precisión en otros equipos se debe realizar una calibración específica.

### Recomendaciones mecánicas no automatizadas

El sistema muestra el desplazamiento relativo y permite ajustar las posiciones manualmente, pero todavía no traduce automáticamente el error medido a pulsaciones de los controles mecánicos de la prensa.

### Persistencia local

El historial se guarda en carpetas y archivos JSON locales. Esta solución es adecuada para demostraciones y pruebas individuales, pero no es ideal para múltiples usuarios, múltiples instancias o despliegues donde el disco local no sea persistente.

### Seguridad pendiente

Antes de utilizar el sistema en un entorno público se recomienda añadir autenticación, limitar el tamaño de los archivos, validar nombres de archivo, restringir CORS y proteger las rutas de descarga.

## 9. Trabajo futuro

- Incorporar un conjunto de datos etiquetado y métricas automatizadas.
- Generar instrucciones de corrección para el prensista.
- Establecer la relación entre desplazamiento en milímetros y pulsaciones mecánicas.
- Optimizar el procesamiento de imágenes 4K y liberar memoria entre lotes.
- Validar el sistema con diferentes cámaras y condiciones de iluminación.
- Migrar el historial a una base de datos o almacenamiento persistente.
- Añadir autenticación y control de acceso.

## 10. Documentación adicional

Los diagramas de arquitectura, casos de uso y secuencia se encuentran en [`docs/diagramas.md`](docs/diagramas.md).
