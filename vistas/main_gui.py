"""
main_gui.py
Punto de entrada ÚNICO de la aplicación gráfica RetroVault.

Conecta las 6 vistas en la MISMA ventana, compartiendo las MISMAS
instancias de Inventario y GestorUsuarios (persistencia en data/*.json):

  PRINCIPAL (invitado) <-> EXPLORAR <-> CARRITO -> LOGIN/CREAR CUENTA -> PRINCIPAL + ADMIN

Sesión: self.usuario_actual (str o None). None = invitado: puede ver
catálogo, explorar y agregar al carrito, pero al PAGAR se le exige
iniciar sesión. ADMIN solo para rol admin.
SALIR vuelve al modo invitado (limpia carrito).

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
    from modelos.producto import Producto
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
    from modelos.producto import Producto
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
    """
    La app.

    Por defecto trabaja SOLA en esta máquina, como siempre: el carrito y el
    stock viven acá.

    Si se le pasa un servidor o una conexión por socket, además Avisa por
    socket en cada cambio del carrito. La lógica del carrito NO cambia: es la
    misma para los dos modos, solo se agrega el aviso.

    Regla de oro de los sockets: el hilo del socket nunca toca la ventana.
    Deja los mensajes en una bandeja y el hilo principal de Tk los lee con
    root.after(). Ver _bombeo_de_eventos.
    """

    def __init__(self, root, servidor=None, conexion=None):
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
        # A dónde volver después de loguearse (principal o carrito)
        self._destino_post_login = "principal"

        # Si somos el ADMIN: el hilo del servidor de sockets.
        self.servidor = servidor
        # Si somos un CLIENTE: la conexión al servidor de la otra máquina.
        self.conexion = conexion
        # Identidad con la que el servidor guarda nuestro carrito mientras
        # somos invitados (todavía no hay usuario con nombre).
        self._id_remoto = self.usuario_actual or "invitado"

        # Foto del catálogo, para detectar cuándo lo editamos y avisarle a
        # los clientes conectados.
        self._huella_catalogo = self._calcular_huella()

        self.contenedor = tk.Frame(root, bg=BG_DARK)
        self.contenedor.pack(fill="both", expand=True)

        # Arranque como invitado: catálogo visible sin pedir login
        self.mostrar_principal()

        # Con sockets hay que estar escuchando la bandeja con root.after.
        if self.servidor is not None or self.conexion is not None:
            self._bombeo_de_eventos()

    # ------------------------------------------------------------------
    # AVISOS POR SOCKET
    # ------------------------------------------------------------------
    def _items_para_red(self):
        """
        El carrito local convertido a la forma simple que viaja por JSON.

        Por el socket no pueden viajar objetos Producto, solo datos simples.
        """
        return [{"id": el["producto"].id, "cantidad": el["cantidad"]}
                for el in self.carrito]

    def _notificar_carrito(self):
        """
        Le manda el carrito al servidor (si estamos conectados por socket).

        El stock lo descuenta el servidor, no nosotros: por eso el aviso va
        después de modificar el carrito, no antes.
        """
        if self.conexion is None or not self.conexion.conectado:
            return
        if self.conexion.usuario != self._id_remoto:
            # Todavía no nos registramos (invitado): no vale la pena mandar.
            return
        self.conexion.enviar_carrito(self._items_para_red())

    def _calcular_huella(self):
        """
        Una "foto" barata del catálogo. Si cambia, el ADMIN editó algo y hay
        que avisarle a los clientes conectados.

        No comparamos los objetos Producto con == (no están definidos para
        eso); comparamos los valores que importan.
        """
        return tuple(
            (p.id, p.nombre, p.precio, p.stock) for p in self.inventario.productos
        )

    def _bombeo_de_eventos(self):
        """
        Lee las bandejas de los sockets y las vuelca en la ventana.

        Hay DOS posibles fuentes: la del servidor (estamos en el ADMIN) y la
        de la conexión (estamos en un CLIENTE). En los dos casos el hilo del
        socket solo dejó el mensaje en su cola; el vaciado se hace acá, en el
        hilo principal de Tk. Por eso la ventana nunca se congela.
        """
        mensajes = []
        if self.servidor is not None:
            while True:
                mensaje = self.servidor.sacar_evento()
                if mensaje is None:
                    break
                mensajes.append(mensaje)
        if self.conexion is not None:
            while True:
                mensaje = self.conexion.sacar_mensaje()
                if mensaje is None:
                    break
                mensajes.append(mensaje)

        for mensaje in mensajes:
            self._al_recibir_mensaje(mensaje)

        # Si somos el ADMIN y el catálogo cambió, avisamos a los clientes.
        if self.servidor is not None and self.servidor.activo:
            nueva = self._calcular_huella()
            if nueva != self._huella_catalogo:
                self._huella_catalogo = nueva
                self.servidor.difundir_inventario()

        self.root.after(100, self._bombeo_de_eventos)

    def _al_recibir_mensaje(self, mensaje):
        """Aplica un mensaje que llegó por socket a la ventana."""
        from red.protocolo import (
            T_CARRITOS, T_INVENTARIO, T_STOCK, T_CARRITO_ESTADO,
            T_PAGO_OK, T_ERROR, T_DESCONECTADO,
        )

        tipo = mensaje.get("type")
        if tipo == T_CARRITOS:
            # Somos el ADMIN: así están los carritos de todos.
            # Al panel solo le alcanza con la cantidad de cada item.
            self.carritos.update(mensaje.get("carritos") or {})
            self._refrescar_admin()
        elif tipo == T_INVENTARIO and self.conexion is not None:
            # Somos el CLIENTE: el catálogo con el stock REAL.
            productos = mensaje.get("productos")
            if productos:
                self.inventario.productos = [
                    Producto.from_dict(d) for d in productos
                    if isinstance(d, dict) and "id" in d
                ]
                self._refrescar_todas()
        elif tipo == T_STOCK:
            producto = self.inventario.buscar_por_id(mensaje.get("id"))
            if producto is not None:
                producto.stock = mensaje.get("stock", producto.stock)
            self._refrescar_todas()
        elif tipo == T_CARRITO_ESTADO:
            # El servidor dijo cómo quedó el carrito de verdad (no había
            # stock para todo lo que pedimos). Ajustamos la pantalla.
            self._aplicar_carrito_del_servidor(mensaje.get("items") or [])
        elif tipo == T_PAGO_OK:
            _toast(self.root, f"¡Compra confirmada! Total: ${mensaje.get('total', 0):,.0f}",
                   tipo="info")
        elif tipo == T_DESCONECTADO:
            _toast(self.root, "Se perdió la conexión con el servidor", tipo="error")
        elif tipo == T_ERROR:
            _toast(self.root, mensaje.get("mensaje", "Error del servidor"),
                   tipo="error")

    def _aplicar_carrito_del_servidor(self, items):
        """Rehace el carrito local con lo que el servidor dice que quedó."""
        self.carrito = []
        for item in items or []:
            producto = self.inventario.buscar_por_id(item.get("id"))
            if producto is not None:
                self.carrito.append({"producto": producto,
                                     "cantidad": int(item["cantidad"])})
        self.carritos[self._id_remoto] = self.carrito
        self._refrescar_carrito()

    def _refrescar_admin(self):
        """Redibuja la pantalla de admin si es la que está visible."""
        for hijo in self.contenedor.winfo_children():
            refrescar = getattr(hijo, "_refrescar_tabla", None)
            if refrescar is not None:
                refrescar()

    def _refrescar_carrito(self):
        """Redibuja la pantalla del carrito si es la que está visible."""
        for hijo in self.contenedor.winfo_children():
            mostrar = getattr(hijo, "mostrar_productos", None)
            if mostrar is not None:
                mostrar(self.carrito)

    def _refrescar_todas(self):
        """Redibuja la pantalla del catálogo si es la que está visible."""
        for hijo in self.contenedor.winfo_children():
            for atributo in ("_cargar_productos", "_cargar", "_refrescar"):
                metodo = getattr(hijo, atributo, None)
                if callable(metodo):
                    try:
                        metodo()
                    except Exception:
                        pass
                    return

    def _limpiar_contenedor(self):
        for widget in self.contenedor.winfo_children():
            widget.destroy()

    def _es_admin(self):
        """True solo si hay sesión y el usuario es admin."""
        return self.gestor_usuarios.es_admin(self.usuario_actual)
    # sesion
    def cerrar_sesion(self):
        """Cierra sesión: preserva el carrito del usuario y vuelve a modo invitado."""
        # El carrito queda guardado en self.carritos[usuario] con su stock
        # reservado; no se vacía ni se devuelve. Se arranca carrito invitado nuevo.
        self.usuario_actual = None
        self.carrito = []
        self._destino_post_login = "principal"
        # Volvemos a ser invitados: el carrito siguiente solo es local hasta
        # que se inicie sesión otra vez.
        self._id_remoto = "invitado"
        self.mostrar_principal()
        # El toast vive en la raíz así que sobrevive al cambio de pantalla
        _toast(self.root, "Sesión cerrada", tipo="info")
    # acciones del carrito  

    def _calcular_total_carrito(self, items):
        total = 0
        for i in items:
            total += float(i["producto"].precio) * i["cantidad"]
        return total

    def _agregar_al_carrito(self, producto):
        """
        Reserva 1 unidad en el inventario y la suma al carrito activo
        (invitado o usuario). Retorna (ok, msg) para mostrar EN PANTALLA.
        El invitado puede agregar; solo PAGAR exige login.
        """
        # Si el producto ya está en el carrito, solo aumenta cantidad
        for elemento in self.carrito:
            if elemento["producto"].id == producto.id:
                if producto.stock <= 0:
                    return False, f"Stock máximo ({elemento['cantidad']}) en el carrito"
                if not self.inventario.descontar_stock(producto.id, 1):
                    return False, f"Sin stock disponible de {producto.nombre}"
                elemento["cantidad"] += 1
                self._notificar_carrito()
                return True, f"Añadido: {producto.nombre} x{elemento['cantidad']}"
        # Si no está, lo agrega por primera vez
        if producto.stock <= 0:
            return False, f"{producto.nombre} sin stock"
        if not self.inventario.descontar_stock(producto.id, 1):
            return False, f"{producto.nombre} sin stock"
        self.carrito.append({"producto": producto, "cantidad": 1})
        self._notificar_carrito()
        return True, f"Añadido: {producto.nombre}"

    def _restar_del_carrito(self, elemento):
        """Quita 1 unidad del carrito y la devuelve al stock."""
        if elemento not in self.carrito:
            return self.carrito
        self.inventario.devolver_stock(elemento["producto"].id, 1)
        elemento["cantidad"] -= 1
        if elemento["cantidad"] <= 0:
            self.carrito.remove(elemento)
        self._notificar_carrito()
        return self.carrito

    def _eliminar_del_carrito(self, elemento):
        """Saca el producto del carrito y devuelve todo su stock reservado."""
        if elemento not in self.carrito:
            return self.carrito
        self.inventario.devolver_stock(
            elemento["producto"].id, elemento["cantidad"]
        )
        self.carrito.remove(elemento)
        self._notificar_carrito()
        return self.carrito

    def _vaciar_carrito(self):
        """Vacía el carrito del usuario activo y restaura el stock."""
        for elemento in list(self.carrito):
            self.inventario.devolver_stock(
                elemento["producto"].id, elemento["cantidad"]
            )
        self.carrito.clear()
        self._notificar_carrito()
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
        if self.conexion is not None and self.conexion.conectado:
            # Con sockets el SERVER es quien cobra y descuenta. Le pedimos
            # confirmar y esperamos su respuesta; si el stock no alcanzan nos
            # va a corregir el carrito con T_CARRITO_ESTADO.
            self.conexion.pagar()
            return True
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

    def _ir_a_login_preservando_carrito(self, destino="principal"):
        """Lleva al login SIN borrar el carrito (flujo invitado -> comprar)."""
        self._destino_post_login = destino
        self.mostrar_login()

    def _exigir_login_para_comprar(self, destino="carrito"):
        """Gate solo para PAGAR: el invitado puede mirar y agregar, pero para
        comprar debe iniciar sesión. No borra el carrito."""
        if self.usuario_actual is None:
            self._ir_a_login_preservando_carrito(destino=destino)
            _toast(self.root, "Inicia sesión para comprar", tipo="info")
            return False
        return True

    def mostrar_login(self):
        self._limpiar_contenedor()
        pantalla = PantallaLogin(
            self.contenedor,
            on_login_exitoso=self._al_iniciar_sesion,
            on_crear_cuenta=self.mostrar_crear_cuenta,
            gestor_usuarios=self.gestor_usuarios,
            on_continuar_invitado=self.mostrar_principal,
        )
        pantalla.pack(fill="both", expand=True)

    def mostrar_crear_cuenta(self):
        self._limpiar_contenedor()
        pantalla = PantallaCrearCuenta(
            self.contenedor,
            on_registro_exitoso=self._al_registrarse,
            on_ir_a_login=self.mostrar_login,
            gestor_usuarios=self.gestor_usuarios,
            on_continuar_invitado=self.mostrar_principal,
        )
        pantalla.pack(fill="both", expand=True)

    def mostrar_principal(self):
        # Modo invitado permitido: sin sesión se muestra igual con usuario "Invitado"
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
            on_ir_login=lambda: self._ir_a_login_preservando_carrito(destino="principal"),
        )
        pantalla.pack(fill="both", expand=True)

    def mostrar_explorar(self, filtro_inicial=""):
        # Modo invitado permitido
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
            on_ir_login=lambda: self._ir_a_login_preservando_carrito(destino="principal"),
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
        # Modo invitado permitido: ver y agregar sí, pagar exige login
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
            on_ir_login=lambda: self._ir_a_login_preservando_carrito(destino="carrito"),
            on_exigir_login=lambda: self._exigir_login_para_comprar(destino="carrito"),
        )
        pantalla.pack(fill="both", expand=True)
        pantalla.mostrar_productos(self.carrito)

    def _al_iniciar_sesion(self, usuario):
        # Guarda la sesión, recupera el carrito propio y fusiona lo que el
        # invitado ya había agregado (stock ya reservado, solo se traspasa).
        invitados = list(self.carrito) if self.usuario_actual is None and self.carrito else []
        self.usuario_actual = usuario
        self._id_remoto = usuario
        if usuario not in self.carritos:
            self.carritos[usuario] = []
        self.carrito = self.carritos[usuario]
        for g in invitados:
            gid = g["producto"].id
            for el in self.carrito:
                if el["producto"].id == gid:
                    el["cantidad"] += g["cantidad"]
                    break
            else:
                self.carrito.append(g)
        destino = self._destino_post_login or "principal"
        self._destino_post_login = "principal"
        # Con sockets: recién ahora tenemos nombre, así que recién ahora nos
        #.presentamos al servidor y le mandamos el carrito (que incluía lo que
        # el invitado había armado).
        if self.conexion is not None and self.conexion.conectado:
            self.conexion.registrarse(usuario)
            self._notificar_carrito()
        if destino == "carrito":
            self.mostrar_carrito()
        else:
            self.mostrar_principal()

    def _al_registrarse(self, datos_usuario):
        # Los nuevos registros son siempre "normal"; mismo merge de invitado.
        invitados = list(self.carrito) if self.usuario_actual is None and self.carrito else []
        self.usuario_actual = datos_usuario.get("correo")
        self._id_remoto = self.usuario_actual
        if self.usuario_actual not in self.carritos:
            self.carritos[self.usuario_actual] = []
        self.carrito = self.carritos[self.usuario_actual]
        for g in invitados:
            gid = g["producto"].id
            for el in self.carrito:
                if el["producto"].id == gid:
                    el["cantidad"] += g["cantidad"]
                    break
            else:
                self.carrito.append(g)
        destino = self._destino_post_login or "principal"
        self._destino_post_login = "principal"
        if self.conexion is not None and self.conexion.conectado:
            self.conexion.registrarse(self.usuario_actual)
            self._notificar_carrito()
        if destino == "carrito":
            self.mostrar_carrito()
        else:
            self.mostrar_principal()


if __name__ == "__main__":
    root = tk.Tk()
    app = RetroVaultApp(root)
    root.mainloop()
