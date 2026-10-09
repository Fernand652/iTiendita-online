import json
import os

RUTA_VENTAS = os.path.join(os.path.dirname(__file__), "..", "data", "ventas.json")

def cargar_ventas():
    if not os.path.exists(RUTA_VENTAS):
        return []
    try:
        with open(RUTA_VENTAS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def registrar_venta(datos_venta):
    ventas = cargar_ventas()
    ventas.append(datos_venta)
    os.makedirs(os.path.dirname(RUTA_VENTAS), exist_ok=True)
    with open(RUTA_VENTAS, "w", encoding="utf-8") as f:
        json.dump(ventas, f, indent=4, ensure_ascii=False)