"""
config.py
---------
Parámetros globales y rangos HSV para la detección de marcas CMYK.
"""

import numpy as np

# --- Rangos HSV extendidos para detección en crops ---
CMY_CROP_RANGES = {
    'C': {
        'hsv_ranges': [
            (np.array([90,  30, 50]), np.array([125, 255, 220])),
            (np.array([88,  15, 30]), np.array([130,  80, 160])),
        ],
        'label_color': (255, 255, 0),
        'nombre': 'Cyan',
        'color_display': (200, 200, 0),
    },
    'M': {
        'hsv_ranges': [
            (np.array([  0, 50, 30]), np.array([ 15, 255, 255])),
            (np.array([160, 30, 30]), np.array([179, 255, 255])),
            (np.array([130, 25, 25]), np.array([165, 255, 255])),
            (np.array([140, 15, 15]), np.array([179, 120, 200])),
        ],
        'label_color': (255, 0, 255),
        'nombre': 'Magenta',
        'color_display': (200, 0, 200),
        'usar_lab_bgr': True,
        'gray_threshold': 30,
    },
    'Y': {
        'hsv_ranges': [
            (np.array([10,  8, 20]), np.array([45, 255, 220])),
            (np.array([ 5,  5, 15]), np.array([55, 160, 180])),
            (np.array([15, 15, 10]), np.array([38,  80, 140])),
        ],
        'label_color': (0, 255, 255),
        'nombre': 'Amarillo',
        'color_display': (0, 200, 200),
    },
}

COLORS_LABEL = {
    'C': (255, 255, 0),
    'M': (255, 0, 255),
    'Y': (0, 255, 255),
    'K': (180, 180, 180),
}
offsets_label = {'C': (-80, -30), 'M': (15, -30), 'Y': (-80, 40), 'K': (15, 40)}

# Parámetros ópticos
distancia_camara_plano_mm = 100
focal_mm = 4.4
sensor_width_mm = 5.37
FACTOR_CORRECION_MM = 0.934

# Sharpening
APPLY_SHARPENING    = False
SHARPENING_STRENGTH = 1.0

# Clustering (v3.2)
CLUSTERING_METHOD = 'promedio_ponderado'
CLUSTERING_SIGMA  = 40.0

TEMPLATE_SIZE = 101  # Tamaño del template de detección en píxeles

RING_RADIUS_PX = 40                    # radio del círculo de la marca, a escala 1.0
MARK_DIAMETER_PX = 2 * RING_RADIUS_PX

# ═══════════════════════════════════════════════════════════════════════════
# NORMALIZACIÓN DE FONDO BLANCO (v3.2+)
# ═══════════════════════════════════════════════════════════════════════════
WHITE_BG_NORMALIZE = True              # Activar/desactivar normalización
WHITE_L_THRESHOLD = 150                # Threshold de luminancia (L en LAB)
WHITE_TOLERANCE_MIN = 15               # Tolerancia mínima (RGB equivalente)
WHITE_TOLERANCE_MAX = 50               # Tolerancia máxima (RGB equivalente)
WHITE_SIGMA_FACTOR = 1.0   

def calculate_mm_per_pixel(
    method: str,
    image_width_px: int,
    mark_size_mm: float = None,
    mark_size_px: float = None,
    camera_distance_mm: float = None,  
):
    """
    Calcula mm/pixel según el método elegido.
    
    Args:
        method: "camera_distance" o "mark_size"
        image_width_px: Ancho de la imagen en píxeles
        mark_size_mm: Tamaño conocido del registro en mm (para MARK_SIZE)
        mark_size_px: Tamaño del registro detectado en píxeles (para MARK_SIZE)
        camera_distance_mm: Distancia cámara-plano en mm (para CAMERA_DISTANCE)
    """
    if method == "camera_distance":
        # Usar parámetro proporcionado o default para evitar errores
        dist = camera_distance_mm if camera_distance_mm is not None else distancia_camara_plano_mm
        tamano_pixel_mm = sensor_width_mm / image_width_px
        # incluimos factor de correccion de mm para distancia
        return ((tamano_pixel_mm * dist) / focal_mm) * FACTOR_CORRECION_MM 
    
    elif method == "mark_size":
        if not mark_size_mm or not mark_size_px:
            raise ValueError("mark_size_mm y mark_size_px requeridos para MARK_SIZE")
        return mark_size_mm / mark_size_px
    
    else:
        raise ValueError(f"Método desconocido: {method}")


SIZE_ADAPTIVE_ENABLED = True
BASE_TEMPLATE_SIZE = 101
BASE_SEARCH_RADIUS = 110
BASE_ROI_MARGIN = 230
BASE_NMS_RADIUS = 110
MIN_TEMPLATE_SIZE_PX = 20
MIN_ROI_MARGIN        = 150   # px — nunca menos que esto
MIN_SEARCH_RADIUS     = 80    # px — nunca menos que esto
PX_MIN_ACCEPT_LOW     = 200
SCORE_NORMALIZER_LOW  = 50