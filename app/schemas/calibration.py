from enum import Enum


class CalibrationMethod(str, Enum):
    """Método para calcular mm/pixel"""
    CAMERA_DISTANCE = "camera_distance"  # Usar distancia cámara-plano (config fija)
    MARK_SIZE = "mark_size"              # Usar tamaño conocido del registro detectado


class CMYKChannel(str, Enum):
    """Canales CMYK disponibles"""
    C = "C"
    M = "M"
    Y = "Y"
    K = "K"