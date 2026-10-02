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

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import messagebox

from modelos.inventario import Inventario
from red.protocolo import HOST, PUERTO
from red.servidor import ServidorCarritos
from vistas.main_gui import RetroVaultApp


def main():
    root = tk.Tk()

    # El ADMIN es el dueño del catálogo: este Inventario autoguarda.
    inventario = Inventario()

    # El servidor corre en un hilo para que la ventana no se congele.
    servidor = ServidorCarritos(inventario, host=HOST, puerto=PUERTO)
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

    print(f"[ADMIN] Servidor escuchando en {HOST}:{PUERTO}")
    print("[ADMIN] Los CLIENTES deben apuntar a esa misma IP y puerto.")
    root.mainloop()


if __name__ == "__main__":
    main()