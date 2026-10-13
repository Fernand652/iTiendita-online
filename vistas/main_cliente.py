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
    parser = argparse.ArgumentParser(description='RetroVault - CLIENTE')
    parser.add_argument('--host', default=HOST, help='IP del ADMIN')
    parser.add_argument('--puerto', type=int, default=PUERTO, help='Puerto')
    return parser.parse_args()


def main():
    args = _argumentos()
    conexion = ConexionServidor(args.host, args.puerto)
    if not conexion.conectar():
        messagebox.showwarning('Sin servidor', conexion.error or 'No se pudo conectar')
        conexion = None
    if conexion is not None:
        conexion.start()
    root = tk.Tk()
    app = RetroVaultApp(root, conexion=conexion)
    root.title('RetroVault - CLIENTE')
    def _al_cerrar():
        try:
            if conexion is not None:
                conexion.cerrar()
        finally:
            root.destroy()
    root.protocol('WM_DELETE_WINDOW', _al_cerrar)
    if conexion is not None:
        print(f'[CLIENTE] Conectado a {args.host}:{args.puerto}')
    root.mainloop()


if __name__ == '__main__':
    main()
