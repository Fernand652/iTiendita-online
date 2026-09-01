import tkinter as tk
from estilos import *
from producto import Producto



class carrito(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.pack()

        self.label = tk.Label(self, text="Carrito de compras")
        self.label.pack(pady=10)

        self.boton_volver = tk.Button(self, text="Volver", command=self.volver)
        self.boton_volver.pack(pady=10)


    def mostrar_productos(self, productos):
        for producto in productos:
            label_producto = tk.Label(self, text=f"{producto.nombre} - ${producto.precio}")
            label_producto.pack(pady=5)

    def actualizar_carrito(self, productos):
        # Limpiar los widgets existentes
        for widget in self.winfo_children():
            if isinstance(widget, tk.Label) and " - $" in widget.cget("text"):
                widget.destroy()

        # Mostrar los productos actualizados
        self.mostrar_productos(productos)