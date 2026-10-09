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

def normalizar_run(run): 
    if not run:
        return ""
    limpio = str(run).replace(".","")
    limpio = limpio.replace("-","").strip()
    return limpio.upper()

def buscar_ventas_por_clientes(ventas, run_cliente):
    run_buscado = normalizar_run(run_cliente)
    if not run_buscado:
        return []

    buscado_plano = str(run_cliente or "").strip().lower()
    resultado = []
    for v in ventas:
        # Compat: ventas nuevas guardan "cliente", legacy usaba "run_cliente".
        valor = v.get("run_cliente", "") or v.get("cliente", "")
        if normalizar_run(valor) == run_buscado:
            resultado.append(v)
        elif str(valor or "").strip().lower() == buscado_plano:
            resultado.append(v)

    resultado.sort(key=lambda x: str(x.get("fecha","")))
    return resultado

def generar_historial_clientes(run_cliente, ventas_cliente):
    lineas = [
        "=" * ANCHO,
        f"HISTORIAL CLIENTE : {run_cliente}",
        "=" * ANCHO,
    ]
    if not ventas_cliente:
        lineas.append("")
        lineas.append("SIN COMPRAS REGISTRADAS") 
        lineas.append("=" * ANCHO)
        return "\n".join(lineas)

    total_acumulado = 0.0

    for idx, v in enumerate(ventas_cliente, 1):
        fecha = v.get("fecha","Sin fecha")
        try:
            monto = float(v.get("total",0.0))
        except (TypeError, ValueError):
            monto = 0.0
        total_acumulado += monto
        id_venta = v.get("id_venta", idx)

        lineas.append("")
        lineas.append(f"Venta #{id_venta} | Fecha: {fecha}")
        lineas.append("-" * ANCHO)

        # Compat: ventas nuevas guardan "items", legacy usaba "productos".
        productos = v.get("items", []) or v.get("productos", [])
        for prod in productos:
            nom = prod.get("nombre", "Producto")
            if len(nom) > 28:
                nom = nom[:25] + "..."
            try:
                cant = int(prod.get("cantidad", 1))
            except (TypeError, ValueError):
                cant = 1
            try:
                precio = float(prod.get("subtotal", float(prod.get("precio", 0.0)) * cant))
            except (TypeError, ValueError):
                precio = 0.0
            lineas.append(f"  - {nom:<28} x{cant:<3} {_peso(precio):>12}")

        try:
            subtotal = float(v.get("subtotal", monto / 1.19 if monto else 0.0))
        except (TypeError, ValueError, ZeroDivisionError):
            subtotal = 0.0
        try:
            iva = float(v.get("iva", monto - subtotal))
        except (TypeError, ValueError):
            iva = 0.0
        lineas.append(f"  {'Subtotal':<34} {_peso(subtotal):>12}")
        lineas.append(f"  {'IVA (19%)':<34} {_peso(iva):>12}")
        lineas.append(f"  {'Total venta':<34} {_peso(monto):>12}")

    lineas.append("")
    lineas.append("=" * ANCHO)
    lineas.append(f"Total compras:        {len(ventas_cliente)}")
    lineas.append(f"MONTO TOTAL HISTORICO:{_peso(total_acumulado):>14}")
    lineas.append("=" * ANCHO)

    return "\n".join(lineas)
            
             
        
