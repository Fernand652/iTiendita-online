"""
main_cliente.py
============================
Punto de entrada del CLIENTE.

El cliente NO es dueño del catálogo: se conecta por socket al servidor del
ADMIN y de ahí le llegan el catálogo y el stock real. Cada vez que toca el
carrito lo ve al instante (modelo optimista) y avisa por socket; el servidor
es el único que descuenta stock de verdad.

Qué hace al arrancar:
  1. Intenta conectarse al ADMIN. Si no está, avisa y ofrece seguir igual en
      modo local (para poder probar la app sin el servidor).
  2. Abre la app pasándole la conexión.

La diferencia con el ADMIN es solo esta línea:
    RetroVaultApp(root, servidor=servidor)   # admin: recibe carritos
    RetroVaultApp(root, conexion=conexion)   # cliente: manda su carrito

Ejecución desde la raíz del proyecto:
    python vistas/main_cliente.py
    python -m vistas.main_cliente

Ojo: HOST en red/protocolo.py tiene que ser la IP de la máquina donde corrió
el ADMIN. Si prueban los dos en la misma máquina, 127.0.0.1 funciona.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import messagebox

from red.cliente import ConexionServidor
from red.protocolo import HOST, PUERTO
from vistas.main_gui import RetroVaultApp


def _argumentos():
    parser = argparse.ArgumentParser(
        description="RetroVault - CLIENTE: se conecta al servidor del ADMIN."
    )
    parser.add_argument(
        "--host", default=HOST, metavar="IP",
        help=f"IP del ADMIN. Si el ADMIN corrió --host 0.0.0.0, usá acá su IP "
             f"de red local (por defecto: {HOST}, misma máquina).",
    )
    parser.add_argument(
        "--puerto", type=int, default=PUERTO, metavar="N",
        help=f"puerto del ADMIN (por defecto: {PUERTO}).",
    )
    return parser.parse_args()


def main():
    args = _argumentos()

    # Conectamos ANTES de abrir la app: si el ADMIN no está, el catálogo que
    # vería sería el de esta máquina y no el real.
    conexion = ConexionServidor(args.host, args.puerto)
    if not conexion.conectar():
        messagebox.showwarning(
            "Sin servidor",
            (conexion.error or "No se pudo conectar con el servidor.")
            + "\n\n¿Querés abrir igual en modo local?",
        )
        conexion = None

    if conexion is not None:
        # El hilo de escucha arranca acá: se queda esperando todo lo que mande
        # el servidor y lo deja en la bandeja (self.cola).
        conexion.start()

    root = tk.Tk()
    app = RetroVaultApp(root, conexion=conexion)
    root.title("RetroVault - CLIENTE")

    def _al_cerrar():
        try:
            if conexion is not None:
                conexion.cerrar()
        finally:
            root.destroy()
    root.protocol("WM_DELETE_WINDOW", _al_cerrar)

    if conexion is not None:
        print(f"[CLIENTE] Conectado a {args.host}:{args.puerto}")
        print("[CLIENTE] Esperando el catalogo del servidor...")
    else:
        print("[CLIENTE] Modo local: sin servidor, el stock no se sincroniza.")
    root.mainloop()


if __name__ == "__main__":
    main()