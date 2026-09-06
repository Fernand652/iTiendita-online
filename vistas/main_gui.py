"""
main_gui.py
Punto de entrada de la aplicación gráfica de RetroVault.
Conecta LOGIN -> PRINCIPAL -> ADMIN (y de vuelta), todas dentro de
la MISMA ventana, compartiendo las MISMAS instancias de Inventario
y GestorUsuarios -- así un producto creado en Admin aparece de
inmediato en la Principal, sin recargar nada por separado.

Ejecuta:
    python main_gui.py
"""

import tkinter as tk
from estilos import BG_DARK
from login_vista import PantallaLogin
from interfaz_principal import PantallaPrincipal
from interfaz_admin import PantallaAdmin
from carrito_vista import carrito as PantallaCarrito
from usuario import GestorUsuarios
from inventario import Inventario


class RetroVaultApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RetroVault")
        self.root.geometry("1100x700")
        self.root.configure(bg=BG_DARK)

        # Una sola instancia de cada una, compartida por toda la app
        self.gestor_usuarios = GestorUsuarios()
        self.inventario = Inventario()
        # Carrito compartido: lista de {'producto': Producto, 'cantidad': int}
        self.carrito = []

        self.contenedor = tk.Frame(root, bg=BG_DARK)
        self.contenedor.pack(fill="both", expand=True)

        self.mostrar_login()

    def _limpiar_contenedor(self):
        for widget in self.contenedor.winfo_children():
            widget.destroy()

    # ------------------------------------------------------------------
    # ACCIONES DEL CARRITO (compartidas)
    # ------------------------------------------------------------------
    def _calcular_total_carrito(self, items):
        total = 0
        for i in items:
            total += float(i["producto"].precio) * i["cantidad"]
        return total

    def _agregar_al_carrito(self, producto):
        # Si el producto ya está en el carrito, solo aumenta cantidad
        for elemento in self.carrito:
            if elemento["producto"].id == producto.id:
                if elemento["cantidad"] < producto.stock:
                    elemento["cantidad"] += 1
                    print(f"[Carrito] {producto.nombre} x{elemento['cantidad']}")
                else:
                    print(f"[Carrito] Stock maximo ({producto.stock}) en el carrito")
                return
        # Si no está, lo agrega por primera vez
        if producto.stock > 0:
            self.carrito.append({"producto": producto, "cantidad": 1})
            print(f"[Carrito] Anadido: {producto.nombre}")

    # ------------------------------------------------------------------
    # NAVEGACIÓN ENTRE PANTALLAS
    # ------------------------------------------------------------------
    def mostrar_login(self):
        self._limpiar_contenedor()
        pantalla = PantallaLogin(
            self.contenedor,
            on_login_exitoso=self._al_iniciar_sesion,
            gestor_usuarios=self.gestor_usuarios
        )
        pantalla.pack(fill="both", expand=True)

    def mostrar_principal(self):
        self._limpiar_contenedor()
        pantalla = PantallaPrincipal(
            self.contenedor,
            inventario=self.inventario.productos,
            on_ir_admin=self.mostrar_admin,
            on_agregar_carro=self._agregar_al_carrito,
            on_ver_carrito=self.mostrar_carrito
        )
        pantalla.pack(fill="both", expand=True)

    def mostrar_admin(self):
        self._limpiar_contenedor()
        pantalla = PantallaAdmin(
            self.contenedor,
            inventario=self.inventario,
            on_volver=self.mostrar_principal
        )
        pantalla.pack(fill="both", expand=True)

    def mostrar_carrito(self):
        self._limpiar_contenedor()
        pantalla = PantallaCarrito(
            self.contenedor,
            on_volver=self.mostrar_principal,
            fn_calcular_total=self._calcular_total_carrito
        )
        pantalla.pack(fill="both", expand=True)
        pantalla.mostrar_productos(self.carrito)

    def _al_iniciar_sesion(self, usuario):
        print(f"✅ Bienvenido, {usuario}")
        self.mostrar_principal()


if __name__ == "__main__":
    root = tk.Tk()
    app = RetroVaultApp(root)
    root.mainloop()
