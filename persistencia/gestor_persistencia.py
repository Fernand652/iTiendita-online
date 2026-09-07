"""
gestor_persistencia.py
Punto único de persistencia JSON del proyecto.

- Toda la persistencia vive en data/*.json
- Los modelos NO hardcodean rutas: importan estas constantes.
- Incluye helpers genéricos + migración legacy CSV -> JSON (una vez).
"""

from pathlib import Path
import csv
import json

# Raíz del proyecto = carpeta que contiene data/, modelos/, vistas/, ...
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

RUTA_PRODUCTOS_JSON = RAIZ_PROYECTO / "data" / "productos.json"
RUTA_USUARIOS_JSON = RAIZ_PROYECTO / "data" / "usuarios.json"
# Legacy: solo se usa para migrar una vez, luego se elimina el CSV.
RUTA_PRODUCTOS_CSV_LEGACY = RAIZ_PROYECTO / "data" / "productos.csv"


def _asegurar_carpeta_data():
    (RAIZ_PROYECTO / "data").mkdir(parents=True, exist_ok=True)


def cargar_json(ruta, default):
    """Lee un JSON y devuelve `default` si no existe o está corrupto."""
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def guardar_json(ruta, datos):
    """Guarda `datos` (lista/dict) en `ruta` creando la carpeta si falta."""
    _asegurar_carpeta_data()
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)


def migrar_csv_a_json(csv_path=RUTA_PRODUCTOS_CSV_LEGACY,
                      json_path=RUTA_PRODUCTOS_JSON):
    """
    Migra data/productos.csv al formato JSON una sola vez.
    - Si el JSON ya existe, solo agrega IDs que falten (no pisa).
    - Si el CSV no existe, no hace nada.
    Retorna la lista final de dicts.
    """
    productos = cargar_json(json_path, default=None)
    if productos is None:
        productos = []
    ids_existentes = {p.get("id") for p in productos}

    csv_path = Path(csv_path)
    if not csv_path.exists():
        if not Path(json_path).exists():
            guardar_json(json_path, productos)
        return productos

    with open(csv_path, newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        for fila in lector:
            if not fila or not fila.get("ID"):
                continue
            try:
                pid = int(float(fila["ID"]))
                if pid in ids_existentes:
                    continue
                precio = float(fila["Precio"])
                if precio.is_integer():
                    precio = int(precio)
                stock_f = float(fila["Stock"])
                stock = int(stock_f) if stock_f.is_integer() else stock_f
                productos.append({
                    "id": pid,
                    "nombre": fila["Nombre"],
                    "precio": precio,
                    "stock": stock,
                    "categoria": fila["Categoria"],
                    "imagen": None,
                })
                ids_existentes.add(pid)
            except (ValueError, KeyError):
                continue

    guardar_json(json_path, productos)
    return productos
