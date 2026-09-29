"""
reporte_carritos.py
Genera un reporte de TEXTO con los carritos de compra que gestiona el
ADMIN. Es una funcion PURA: recibe los mismos datos que manda el servidor
(mensaje T_CARRITOS) y devuelve un texto, sin saber nada de sockets.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from persistencia.gestor_persistencia import RAIZ_PROYECTO
except ImportError:  # fallback cuando se ejecuta con cwd=reportes/
    from gestor_persistencia import RAIZ_PROYECTO

ANCHO = 56
RUTA_REPORTE = os.path.join(str(RAIZ_PROYECTO), "data", "reporte_carritos.txt")


def _peso(valor):
    """Formatea $1.000 (formato chileno)."""
    try:
        return f"${float(valor):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def generar_reporte(carritos, catalogo, conectados=None):
    """
    Arma el reporte a partir de los carritos.

    carritos:   {usuario: [{"id": 1, "cantidad": 2}, ...]}
    catalogo:   [{"id": 1, "nombre": "...", "precio": 1000}, ...]
    conectados: lista de usuarios conectados (opcional, solo informativo)
    """
    precios = {p["id"]: p for p in catalogo}
    lineas = ["=" * ANCHO, "REPORTE DE CARRITOS - RETRO VAULT", "=" * ANCHO]
    total_general = total_unidades = 0

    for usuario in sorted(carritos):
        lineas += ["", f"CLIENTE: {usuario}"]
        subtotal = 0
        for item in carritos[usuario]:
            producto = precios.get(item["id"], {})
            nombre = producto.get("nombre", f"Producto #{item['id']}")
            # Recortamos para que la columna no se desalinee
            if len(nombre) > 30:
                nombre = nombre[:27] + "..."
            monto = float(producto.get("precio", 0)) * item["cantidad"]
            subtotal += monto
            total_unidades += item["cantidad"]
            lineas.append(
                f"  - {nombre:<30} x{item['cantidad']:<3} {_peso(monto):>12}")
        lineas.append(f"  {'Subtotal':<36} {_peso(subtotal):>12}")
        total_general += subtotal

    lineas += ["", "-" * ANCHO, f"Clientes con carrito:  {len(carritos)}"]
    if conectados is not None:
        lineas.append(f"Clientes conectados:   {len(conectados)}")
    lineas += [f"Unidades en carritos:  {total_unidades}",
               f"TOTAL GENERAL:         {_peso(total_general)}",
               "=" * ANCHO]
    return "\n".join(lineas)


def guardar_reporte(texto, ruta=RUTA_REPORTE):
    """Guarda el reporte en un archivo UTF-8. Devuelve la ruta."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(texto)
    return ruta
