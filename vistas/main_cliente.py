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
    root = tk.Tk()
    # No mostramos la tienda antes de verificar la conexión: una caja sin
    # servidor no puede trabajar con su catálogo local, porque daría la falsa
    # impresión de estar sincronizada.
    root.withdraw()
    conexion = ConexionServidor(args.host, args.puerto)
    if not conexion.conectar():
        messagebox.showerror(
            'No se pudo conectar con el ADMIN',
            conexion.error or 'Revisa la IP del ADMIN y la red privada de Windows.',
            parent=root,
        )
        root.destroy()
        return
    conexion.start()
    root.deiconify()
    app = RetroVaultApp(root, conexion=conexion)
    root.title('RetroVault - CLIENTE')
    def _al_cerrar():
        try:
            conexion.cerrar()
        finally:
            root.destroy()
    root.protocol('WM_DELETE_WINDOW', _al_cerrar)
    print(f'[CLIENTE] Conectado al catálogo compartido en {args.host}:{args.puerto}')
    root.mainloop()


if __name__ == '__main__':
    main()
