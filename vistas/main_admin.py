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
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except OSError:
        return None


def _argumentos():
    parser = argparse.ArgumentParser(description='RetroVault - ADMIN')
    parser.add_argument('--host', default=HOST, help='IP donde escuchar')
    parser.add_argument('--puerto', type=int, default=PUERTO, help='Puerto')
    return parser.parse_args()


def main():
    args = _argumentos()
    root = tk.Tk()
    inventario = Inventario()
    servidor = ServidorCarritos(inventario, host=args.host, puerto=args.puerto)
    servidor.start()
    # La interfaz y el servidor comparten el mismo Inventario: este equipo
    # es la única fuente de verdad para catálogo, stock y carritos.
    app = RetroVaultApp(root, servidor=servidor, inventario=inventario)
    root.title('RetroVault - ADMIN')

    def _avisar_si_fallo():
        if servidor.error:
            messagebox.showerror('No se pudo iniciar el servidor', servidor.error)
        else:
            root.after(300, _avisar_si_fallo)
    root.after(300, _avisar_si_fallo)

    def _al_cerrar():
        try:
            servidor.detener()
        finally:
            root.destroy()
    root.protocol('WM_DELETE_WINDOW', _al_cerrar)

    print(f'[ADMIN] Servidor escuchando en {args.host}:{args.puerto}')
    if args.host in ('127.0.0.1', 'localhost'):
        print('[ADMIN] Para red: py vistas/main_admin.py --host 0.0.0.0')
    elif args.host == '0.0.0.0':
        ip_lan = _ip_lan()
        if ip_lan:
            print(f'[ADMIN] Las cajas cliente deben usar: py vistas/main_cliente.py --host {ip_lan}')
    root.mainloop()


if __name__ == '__main__':
    main()
