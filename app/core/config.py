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
distancia_camara_plano_mm = 110
focal_mm = 4.0
sensor_width_mm = 5.6

# Sharpening
APPLY_SHARPENING    = False
SHARPENING_STRENGTH = 1.0

# Clustering (v3.2)
CLUSTERING_METHOD = 'promedio_ponderado'
CLUSTERING_SIGMA  = 40.0
