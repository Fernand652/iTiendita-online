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
    try:
        from persistencia.gestor_persistencia import (
            RUTA_VENTAS_JSON,
            cargar_json,
            guardar_json,
        )
    except ImportError:
        RUTA_VENTAS_JSON, cargar_json, guardar_json = None, None, None
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
    try:
        from persistencia.gestor_persistencia import (
            RUTA_VENTAS_JSON,
            cargar_json,
            guardar_json,
        )
    except ImportError:
        RUTA_VENTAS_JSON, cargar_json, guardar_json = None, None, None


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
        # Carritos por cliente: {usuario: [{'producto': Producto, 'cantidad': int}]}
        # Cada CLIENTE arma el suyo; el ADMIN los consume desde mostrar_admin.
        # self.carrito siempre apunta a la lista del usuario activo.
        self.carritos = {}
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
        """Cierra sesión: guarda el carrito del usuario y vuelve al login."""
        # El carrito queda guardado en self.carritos[usuario] con su stock
        # reservado; no se vacía ni se devuelve (el pedido sigue vigente).
        self.usuario_actual = None
        self.carrito = []
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
        Reserva 1 unidad en el inventario y la suma al carrito del usuario
        activo. Retorna (ok, msg) para mostrar EN PANTALLA.
        """
        if self.usuario_actual is None:
            return False, "Inicia sesión primero"
        # Si el producto ya está en el carrito, solo aumenta cantidad
        for elemento in self.carrito:
            if elemento["producto"].id == producto.id:
                if producto.stock <= 0:
                    return False, f"Stock máximo ({elemento['cantidad']}) en el carrito"
                if not self.inventario.descontar_stock(producto.id, 1):
                    return False, f"Sin stock disponible de {producto.nombre}"
                elemento["cantidad"] += 1
                return True, f"Añadido: {producto.nombre} x{elemento['cantidad']}"
        # Si no está, lo agrega por primera vez
        if producto.stock <= 0:
            return False, f"{producto.nombre} sin stock"
        if not self.inventario.descontar_stock(producto.id, 1):
            return False, f"{producto.nombre} sin stock"
        self.carrito.append({"producto": producto, "cantidad": 1})
        return True, f"Añadido: {producto.nombre}"

    def _restar_del_carrito(self, elemento):
        """Quita 1 unidad del carrito y la devuelve al stock."""
        if elemento not in self.carrito:
            return self.carrito
        self.inventario.devolver_stock(elemento["producto"].id, 1)
        elemento["cantidad"] -= 1
        if elemento["cantidad"] <= 0:
            self.carrito.remove(elemento)
        return self.carrito

    def _eliminar_del_carrito(self, elemento):
        """Saca el producto del carrito y devuelve todo su stock reservado."""
        if elemento not in self.carrito:
            return self.carrito
        self.inventario.devolver_stock(
            elemento["producto"].id, elemento["cantidad"]
        )
        self.carrito.remove(elemento)
        return self.carrito

    def _vaciar_carrito(self):
        """Vacía el carrito del usuario activo y restaura el stock."""
        for elemento in list(self.carrito):
            self.inventario.devolver_stock(
                elemento["producto"].id, elemento["cantidad"]
            )
        self.carrito.clear()
        return self.carrito

    def _registrar_venta(self):
        """Guarda la venta en data/ventas.json para que el ADMIN la consuma."""
        if RUTA_VENTAS_JSON is None or cargar_json is None:
            return
        try:
            from datetime import datetime
            fecha = datetime.now().isoformat(timespec="seconds")
        except Exception:
            fecha = ""
        items = [
            {
                "id": el["producto"].id,
                "nombre": el["producto"].nombre,
                "precio": el["producto"].precio,
                "cantidad": el["cantidad"],
            }
            for el in self.carrito
        ]
        total = sum(float(i["precio"]) * i["cantidad"] for i in items)
        ventas = cargar_json(str(RUTA_VENTAS_JSON), default=[]) or []
        ventas.append(
            {
                "cliente": self.usuario_actual,
                "fecha": fecha,
                "items": items,
                "total": total,
            }
        )
        guardar_json(str(RUTA_VENTAS_JSON), ventas)

    def _confirmar_pago(self):
        """Confirma la venta: la registra y vacía SIN devolver stock."""
        if not self.carrito:
            return False
        self._registrar_venta()
        self.carrito.clear()
        return True
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
            carritos=self.carritos,
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
            on_agregar=self._agregar_al_carrito,
            on_restar=self._restar_del_carrito,
            on_eliminar=self._eliminar_del_carrito,
            on_vaciar=self._vaciar_carrito,
            on_pagar_confirmado=self._confirmar_pago,
            usuario_actual=self.usuario_actual,
            on_cerrar_sesion=self.cerrar_sesion,
        )
        pantalla.pack(fill="both", expand=True)
        pantalla.mostrar_productos(self.carrito)

    def _al_iniciar_sesion(self, usuario):
        # Guarda la sesión, recupera el carrito propio del cliente y navega
        # (el login ya mostró toast de bienvenida)
        self.usuario_actual = usuario
        if usuario not in self.carritos:
            self.carritos[usuario] = []
        self.carrito = self.carritos[usuario]
        self.mostrar_principal()

    def _al_registrarse(self, datos_usuario):
        # Los nuevos registros son siempre "normal"; guarda sesión y navega
        self.usuario_actual = datos_usuario.get("correo")
        if self.usuario_actual not in self.carritos:
            self.carritos[self.usuario_actual] = []
        self.carrito = self.carritos[self.usuario_actual]
        self.mostrar_principal()


if __name__ == "__main__":
    root = tk.Tk()
    app = RetroVaultApp(root)
    root.mainloop()
