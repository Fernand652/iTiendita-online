"""
main_gui.py
Punto de entrada ÚNICO de la aplicación gráfica RetroVault.

Conecta las 6 vistas en la MISMA ventana, compartiendo las MISMAS
instancias de Inventario y GestorUsuarios (persistencia en data/*.json):

  LOGIN <-> CREAR CUENTA -> PRINCIPAL <-> EXPLORAR <-> CARRITO + ADMIN

Sesión: self.usuario_actual (str o None). ADMIN solo para rol admin.
SALIR limpia el carrito y vuelve al login.

Ejecución desde la raíz del proyecto:
    python vistas/main_gui.py
    python -m vistas.main_gui
"""

import os
import sys

# Permite `python vistas/main_gui.py` desde la raíz y también
# `python -m vistas.main_gui`: la raíz siempre queda en sys.path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk

try:
    from vistas.estilos import BG_DARK
    from vistas.login_vista import PantallaLogin
    from vistas.interfaz_crear_cuenta import PantallaCrearCuenta
    from vistas.interfaz_principal import PantallaPrincipal
    from vistas.interfaz_explorar import PantallaExplorar
    from vistas.interfaz_admin import PantallaAdmin
    from vistas.carrito_vista import carrito as PantallaCarrito
    from vistas.toast import mostrar_toast
    from modelos.usuario import GestorUsuarios
    from modelos.inventario import Inventario
except ImportError:  # fallback cuando se ejecuta con cwd=vistas/
    from estilos import BG_DARK
    from login_vista import PantallaLogin
    from interfaz_crear_cuenta import PantallaCrearCuenta
    from interfaz_principal import PantallaPrincipal
    from interfaz_explorar import PantallaExplorar
    from interfaz_admin import PantallaAdmin
    from carrito_vista import carrito as PantallaCarrito
    try:
        from toast import mostrar_toast
    except ImportError:
        mostrar_toast = None
    from modelos.usuario import GestorUsuarios
    from modelos.inventario import Inventario


def _toast(widget, mensaje, tipo="error"):
    if mostrar_toast is None:
        return
    try:
        mostrar_toast(widget, mensaje, tipo=tipo)
    except Exception:
        pass


class RetroVaultApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RetroVault")
        self.root.geometry("1100x700")
        self.root.configure(bg=BG_DARK)

        # Una sola instancia de cada una, compartida por toda la app.
        # La persistencia vive en data/productos.json y data/usuarios.json
        # (ver persistencia/gestor_persistencia.py).
        self.gestor_usuarios = GestorUsuarios()
        self.inventario = Inventario()
        # Sesión actual: nombre de usuario logueado o None (invitado)
        self.usuario_actual = None
        # Carrito compartido: lista de {'producto': Producto, 'cantidad': int}
        self.carrito = []

        self.contenedor = tk.Frame(root, bg=BG_DARK)
        self.contenedor.pack(fill="both", expand=True)

        self.mostrar_login()

    def _limpiar_contenedor(self):
        for widget in self.contenedor.winfo_children():
            widget.destroy()

    def _es_admin(self):
        """True solo si hay sesión y el usuario es admin."""
        return self.gestor_usuarios.es_admin(self.usuario_actual)
    # sesion
    def cerrar_sesion(self):
        """Cierra sesión: limpia usuario + carrito y vuelve al login."""
        self.usuario_actual = None
        self.carrito.clear()
        self.mostrar_login()
        # El login se acaba de crear; el toast vive en la raíz así que sobrevive
        _toast(self.root, "Sesión cerrada", tipo="info")
    # acciones del carrito  

    def _calcular_total_carrito(self, items):
        total = 0
        for i in items:
            total += float(i["producto"].precio) * i["cantidad"]
        return total

    def _agregar_al_carrito(self, producto):
        """
        Añade al carrito compartido y retorna (ok, msg) para que
        Principal/Explorar lo muestren EN PANTALLA (lbl_estado).
        """
        # Si el producto ya está en el carrito, solo aumenta cantidad
        for elemento in self.carrito:
            if elemento["producto"].id == producto.id:
                if elemento["cantidad"] < producto.stock:
                    elemento["cantidad"] += 1
                    return True, f"Añadido: {producto.nombre} x{elemento['cantidad']}"
                else:
                    return False, f"Stock máximo ({producto.stock}) en el carrito"
        # Si no está, lo agrega por primera vez
        if producto.stock > 0:
            self.carrito.append({"producto": producto, "cantidad": 1})
            return True, f"Añadido: {producto.nombre}"
        return False, f"{producto.nombre} sin stock"
    # navegacion entre las 6 pantallas
    def _requiere_sesion(self):
        """Gate anti-invitado: sin sesión vuelve al login con aviso."""
        if self.usuario_actual is None:
            self.mostrar_login()
            _toast(self.root, "Inicia sesión primero", tipo="error")
            return False
        return True

    def mostrar_login(self):
        self._limpiar_contenedor()
        pantalla = PantallaLogin(
            self.contenedor,
            on_login_exitoso=self._al_iniciar_sesion,
            on_crear_cuenta=self.mostrar_crear_cuenta,
            gestor_usuarios=self.gestor_usuarios,
        )
        pantalla.pack(fill="both", expand=True)

    def mostrar_crear_cuenta(self):
        self._limpiar_contenedor()
        pantalla = PantallaCrearCuenta(
            self.contenedor,
            on_registro_exitoso=self._al_registrarse,
            on_ir_a_login=self.mostrar_login,
            gestor_usuarios=self.gestor_usuarios,
        )
        pantalla.pack(fill="both", expand=True)

    def mostrar_principal(self):
        if not self._requiere_sesion():
            return
        self._limpiar_contenedor()
        pantalla = PantallaPrincipal(
            self.contenedor,
            inventario=self.inventario,
            on_ir_admin=self.mostrar_admin,
            on_agregar_carro=self._agregar_al_carrito,
            on_ver_carrito=self.mostrar_carrito,
            on_ir_explorar=self.mostrar_explorar,
            usuario_actual=self.usuario_actual,
            es_admin=self._es_admin(),
            on_cerrar_sesion=self.cerrar_sesion,
        )
        pantalla.pack(fill="both", expand=True)

    def mostrar_explorar(self, filtro_inicial=""):
        if not self._requiere_sesion():
            return
        self._limpiar_contenedor()
        pantalla = PantallaExplorar(
            self.contenedor,
            inventario=self.inventario,
            on_volver=self.mostrar_principal,
            on_agregar_carro=self._agregar_al_carrito,
            filtro_inicial=filtro_inicial,
            on_ver_carrito=self.mostrar_carrito,
            usuario_actual=self.usuario_actual,
            on_cerrar_sesion=self.cerrar_sesion,
        )
        pantalla.pack(fill="both", expand=True)

    def mostrar_admin(self):
        # Gate: un usuario normal NUNCA entra al apartado admin
        if not self._es_admin():
            _toast(self.root, "Acceso denegado: solo administradores", tipo="error")
            self.mostrar_principal()
            return
        self._limpiar_contenedor()
        pantalla = PantallaAdmin(
            self.contenedor,
            inventario=self.inventario,
            on_volver=self.mostrar_principal,
            usuario_actual=self.usuario_actual,
            on_cerrar_sesion=self.cerrar_sesion,
        )
        pantalla.pack(fill="both", expand=True)

    def mostrar_carrito(self):
        if not self._requiere_sesion():
            return
        self._limpiar_contenedor()
        pantalla = PantallaCarrito(
            self.contenedor,
            on_volver=self.mostrar_principal,
            fn_calcular_total=self._calcular_total_carrito,
            usuario_actual=self.usuario_actual,
            on_cerrar_sesion=self.cerrar_sesion,
        )
        pantalla.pack(fill="both", expand=True)
        pantalla.mostrar_productos(self.carrito)

    def _al_iniciar_sesion(self, usuario):
        # Guarda la sesión y navega (el login ya mostró toast de bienvenida)
        self.usuario_actual = usuario
        self.mostrar_principal()

    def _al_registrarse(self, datos_usuario):
        # Los nuevos registros son siempre "normal"; guarda sesión y navega
        self.usuario_actual = datos_usuario.get("correo")
        self.mostrar_principal()


if __name__ == "__main__":
    root = tk.Tk()
    app = RetroVaultApp(root)
    root.mainloop()
