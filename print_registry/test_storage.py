import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from print_registry.storage import ColorResult, LocalStorage

storage = LocalStorage(base_dir="test_output")

FAKE_IMAGE = bytes([
    0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A,0x00,0x00,0x00,0x0D,0x49,0x48,0x44,0x52,
    0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,0x08,0x02,0x00,0x00,0x00,0x90,0x77,0x53,
    0xDE,0x00,0x00,0x00,0x0C,0x49,0x44,0x41,0x54,0x08,0xD7,0x63,0xF8,0xCF,0xC0,0x00,
    0x00,0x00,0x02,0x00,0x01,0xE2,0x21,0xBC,0x33,0x00,0x00,0x00,0x00,0x49,0x45,0x4E,
    0x44,0xAE,0x42,0x60,0x82,
])

colores = [
    ColorResult("Cyan",    {"x":120,"y":340,"width":50,"height":30}, 0.97, "#00AEEF"),
    ColorResult("Magenta", {"x":200,"y":150,"width":45,"height":28}, 0.94, "#EC008C"),
    ColorResult("Yellow",  {"x":310,"y":220,"width":60,"height":35}, 0.99, "#FFF200"),
    ColorResult("Black",   {"x":80, "y":400,"width":40,"height":40}, 0.98, "#231F20"),
]

print("── GUARDANDO ──────────────────────────────────")
record = storage.save(FAKE_IMAGE, "muestra_cmyk.png", colores, {"job": "Cartel Verano 2025"})

print("\n── RECUPERANDO ────────────────────────────────")
r = storage.get(record.id)
print(f"ID: {r.id}")
for c in r.colors:
    print(f"  · {c.name} ({c.hex_value}) en {c.coordinates}")

print("\n── LISTANDO TODOS ─────────────────────────────")
print(f"Total registros: {len(storage.list_all())}")

print("\n── ELIMINANDO ─────────────────────────────────")
storage.delete(record.id)
print(f"Registros tras borrar: {len(storage.list_all())}")
print("\n✓ Prueba completada sin errores.")
