"""
main_admin.py
============================
Punto de entrada del ADMIN.

Esta es la "caja automática" central: el ADMIN levanta el SERVIDOR de sockets
y además usa la app en su misma máquina. Los CLIENTES se conectan a esta
máquina.

Qué hace al arrancar:
  1. Crea el Inventario REAL (el único que puede escribir data/productos.json).
  2. Levanta el ServidorCarritos en un hilo aparte, escuchando en HOST:PUERTO.
  3. Abre la app pasándole el servidor: el admin navega igual que siempre y
     además ve por socket los carritos de los clientes remotos en su panel.

La diferencia con el CLIENTE es solo esta línea:
    RetroVaultApp(root, servidor=servidor)   # admin: recibe carritos
    RetroVaultApp(root, conexion=conexion)   # cliente: manda su carrito

Ejecución desde la raíz del proyecto:
    python vistas/main_admin.py
    python -m vistas.main_admin

Para que los compañeros se conecten desde otra máquina, en red/protocolo.py
tiene que estar HOST con la IP de ESTA máquina (en Windows: ipconfig).
"""

import argparse
import os
import sys
import socket

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import messagebox

from modelos.inventario import Inventario
from red.protocolo import HOST, PUERTO
from red.servidor import ServidorCarritos
from vistas.main_gui import RetroVaultApp


def _ip_lan():
    """
    Devuelve la IP de esta máquina en la red local, para que no haga falta
    que el admin corra `ipconfig` a mano.

    Para detectarla conectamos (sin enviar nada) a una dirección pública:
    el SO responde con la IP de la interfaz que saldría. Si no hay red,
    devolvemos None y listo.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


def _argumentos():
    parser = argparse.ArgumentParser(
        description="RetroVault - ADMIN: levanta el servidor y abre el panel."
    )
    parser.add_argument(
        "--host", default=HOST, metavar="IP",
        help=f"ip donde ESCUCHAR. Usa 0.0.0.0 para aceptar clientes de otras "
             f"máquinas (por defecto: {HOST}, sólo esta máquina).",
    )
    parser.add_argument(
        "--puerto", type=int, default=PUERTO, metavar="N",
        help=f"puerto del servidor (por defecto: {PUERTO}).",
    )
    return parser.parse_args()


def main():
    args = _argumentos()
    root = tk.Tk()

    # El ADMIN es el dueño del catálogo: este Inventario autoguarda.
    inventario = Inventario()

    # El servidor corre en un hilo para que la ventana no se congele.
    servidor = ServidorCarritos(inventario, host=args.host, puerto=args.puerto)
    servidor.start()

    app = RetroVaultApp(root, servidor=servidor)
    root.title("RetroVault - ADMIN")

    # Si el puerto estaba ocupado, avisamos clarito en vez de fallar mudo.
    def _avisar_si_fallo():
        if servidor.error:
            messagebox.showerror("No se pudo iniciar el servidor", servidor.error)
        else:
            root.after(300, _avisar_si_fallo)
    root.after(300, _avisar_si_fallo)

    def _al_cerrar():
        try:
            servidor.detener()
        finally:
            root.destroy()
    root.protocol("WM_DELETE_WINDOW", _al_cerrar)

    print(f"[ADMIN] Servidor escuchando en {args.host}:{args.puerto}")
    if args.host in ("127.0.0.1", "localhost"):
        print("[ADMIN] Sólo acepta clientes de ESTA máquina.")
        print('[ADMIN] Para red: py vistas/main_admin.py --host 0.0.0.0')
    else:
        ip = _ip_lan()
        donde = f"{ip}:{args.puerto}" if ip else f"{args.host}:{args.puerto}"
        print("[ADMIN] Para red local, los clientes usan:")
        print(f"[ADMIN]   py vistas/main_cliente.py --host {donde}")
    root.mainloop()


if __name__ == "__main__":
    main()