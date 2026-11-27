"""Vista MI PERFIL: datos del cliente, sus pedidos y su lista de deseados."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk

try:
    from vistas.estilos import (
        BG_DARK, DARK_CARD, GREEN, WHITE, GRAY_TEXT, GRAY_BTN,
        FUENTE_TITULO, FUENTE_NAV, FUENTE_BODY, FUENTE_BOTON, FUENTE_NOMBRE,
    )
except ImportError:
    from estilos import (
        BG_DARK, DARK_CARD, GREEN, WHITE, GRAY_TEXT, GRAY_BTN,
        FUENTE_TITULO, FUENTE_NAV, FUENTE_BODY, FUENTE_BOTON, FUENTE_NOMBRE,
    )

try:
    from vistas.toast import mostrar_toast
except ImportError:
    try:
        from toast import mostrar_toast
    except ImportError:
        mostrar_toast = None


def _toast(widget, mensaje, tipo="error"):
    if mostrar_toast is None:
        return
    try:
        mostrar_toast(widget, mensaje, tipo=tipo)
    except Exception:
        pass


def _fmt_clp(valor):
    try:
        return "$" + f"{float(valor):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


class PantallaMiPerfil(tk.Frame):
    """Perfil del usuario activo con tres secciones claras."""

    def __init__(self, parent, usuario=None, gestor_usuarios=None,
                 lista_deseos=None, inventario=None, obtener_pedidos=None,
                 on_volver=None, on_ir_login=None, on_quitar=None,
                 on_ver_producto=None, on_agregar_carro=None, on_cerrar_sesion=None):
        super().__init__(parent, bg=BG_DARK)
        self.usuario = usuario
        self.gestor_usuarios = gestor_usuarios
        self.lista_deseos = lista_deseos
        self.inventario = inventario
        self.obtener_pedidos = obtener_pedidos
        self.on_volver = on_volver
        self.on_ir_login = on_ir_login
        self.on_quitar = on_quitar
        self.on_ver_producto = on_ver_producto
        self.on_agregar_carro = on_agregar_carro
        self.on_cerrar_sesion = on_cerrar_sesion
        self._crear_ui()
        self.refrescar()

    def _crear_ui(self):
        barra = tk.Frame(self, bg=BG_DARK)
        barra.pack(fill="x", padx=24, pady=(18, 10))

        tk.Label(barra, text="MI PERFIL", font=FUENTE_TITULO,
                 bg=BG_DARK, fg=GREEN).pack(side="left")
        tk.Button(
            barra, text="← VOLVER", font=FUENTE_NAV, bg=GRAY_BTN, fg=WHITE,
            relief="flat", bd=0, cursor="hand2", padx=12, pady=6,
            command=self._volver,
        ).pack(side="right")
        if self.usuario and self.on_cerrar_sesion:
            tk.Button(
                barra, text="CERRAR SESIÓN", font=FUENTE_NAV,
                bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0,
                cursor="hand2", padx=12, pady=6,
                command=self.on_cerrar_sesion,
            ).pack(side="right", padx=8)

        cuerpo = tk.Frame(self, bg=BG_DARK)
        cuerpo.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        self._lienzo = tk.Canvas(cuerpo, bg=BG_DARK, highlightthickness=0)
        barra_scroll = tk.Scrollbar(cuerpo, orient="vertical",
                                    command=self._lienzo.yview)
        self._contenido = tk.Frame(self._lienzo, bg=BG_DARK)
        self._ventana_contenido = self._lienzo.create_window(
            (0, 0), window=self._contenido, anchor="nw"
        )
        self._lienzo.configure(yscrollcommand=barra_scroll.set)
        barra_scroll.pack(side="right", fill="y")
        self._lienzo.pack(side="left", fill="both", expand=True)

        self._contenido.bind(
            "<Configure>",
            lambda _e: self._lienzo.configure(scrollregion=self._lienzo.bbox("all")),
        )
        self._lienzo.bind(
            "<Configure>",
            lambda e: self._lienzo.itemconfigure(self._ventana_contenido, width=e.width),
        )

    def refrescar(self):
        posicion = self._lienzo.yview()[0]
        for widget in self._contenido.winfo_children():
            widget.destroy()
        self._seccion_datos()
        self._seccion_pedidos()
        self._seccion_deseos()
        self._contenido.update_idletasks()
        self._lienzo.yview_moveto(posicion)

    def _seccion(self, titulo):
        marco = tk.Frame(self._contenido, bg=DARK_CARD, padx=18, pady=14)
        marco.pack(fill="x", pady=(0, 14))
        tk.Label(marco, text=titulo, font=FUENTE_NAV, bg=DARK_CARD,
                 fg=GREEN).pack(anchor="w", pady=(0, 8))
        return marco

    @staticmethod
    def _mensaje(marco, texto):
        tk.Label(marco, text=texto, font=FUENTE_BODY, bg=DARK_CARD,
                 fg=GRAY_TEXT, wraplength=720, justify="left",
                 anchor="w").pack(fill="x", anchor="w")

    def _seccion_datos(self):
        marco = self._seccion("DATOS DEL USUARIO")
        if not self.usuario:
            self._mensaje(marco, "No hay sesión activa. Inicia sesión para ver tus datos.")
            if self.on_ir_login is not None:
                tk.Button(
                    marco, text="INICIAR SESIÓN", font=FUENTE_BOTON,
                    bg=GREEN, fg="#1a1a1a", relief="flat", bd=0,
                    cursor="hand2", command=self.on_ir_login,
                ).pack(anchor="w", pady=(10, 0), ipady=5)
            return

        usuario_obj = None
        obtener = getattr(self.gestor_usuarios, "obtener_usuario", None)
        if callable(obtener):
            try:
                usuario_obj = obtener(self.usuario)
            except Exception:
                usuario_obj = None

        if usuario_obj is None:
            self._mensaje(
                marco,
                f"Sesión activa: {self.usuario}. No se encontraron datos registrados.",
            )
            return

        campos = (
            ("Usuario / correo", getattr(usuario_obj, "nombre", self.usuario)),
            ("Nombres", getattr(usuario_obj, "nombres", "") or "No registrado"),
            ("Apellidos", getattr(usuario_obj, "apellidos", "") or "No registrado"),
            ("País", getattr(usuario_obj, "pais", "") or "No registrado"),
        )
        for etiqueta, valor in campos:
            fila = tk.Frame(marco, bg=DARK_CARD)
            fila.pack(fill="x", pady=2)
            tk.Label(fila, text=f"{etiqueta}:", font=FUENTE_BODY, bg=DARK_CARD,
                     fg=GRAY_TEXT, width=18, anchor="w").pack(side="left")
            tk.Label(fila, text=str(valor), font=FUENTE_BODY, bg=DARK_CARD,
                     fg=WHITE, anchor="w").pack(side="left")

    def _pedidos_del_usuario(self):
        if not self.usuario or not callable(self.obtener_pedidos):
            return []
        try:
            datos = self.obtener_pedidos() or []
        except Exception:
            datos = []
        pedidos = []
        for pedido in datos:
            if not isinstance(pedido, dict):
                continue
            cliente = str(pedido.get("cliente") or "").strip().lower()
            if cliente == str(self.usuario).strip().lower():
                pedidos.append(pedido)
        pedidos.sort(key=lambda p: str(p.get("fecha") or ""), reverse=True)
        return pedidos

    def _seccion_pedidos(self):
        marco = self._seccion("MIS PEDIDOS")
        pedidos = self._pedidos_del_usuario()
        if not pedidos:
            if self.usuario:
                self._mensaje(marco, "Todavía no tienes pedidos realizados.")
            else:
                self._mensaje(marco, "Inicia sesión para ver tus pedidos.")
            return

        for pedido in pedidos:
            tarjeta = tk.Frame(marco, bg=BG_DARK, padx=12, pady=8)
            tarjeta.pack(fill="x", pady=4)
            fecha = str(pedido.get("fecha") or "").replace("T", " ")[:16] or "Sin fecha"
            estado = str(pedido.get("estado") or "Pendiente")
            cabecera = (
                f"{pedido.get('id_pedido', '?')}  |  {fecha}  |  {estado}  |  "
                f"{_fmt_clp(pedido.get('total', 0))}"
            )
            tk.Label(tarjeta, text=cabecera, font=FUENTE_NAV, bg=BG_DARK,
                     fg=WHITE, anchor="w").pack(fill="x")
            items = pedido.get("items") or []
            if not isinstance(items, list):
                items = []
            if not items:
                tk.Label(tarjeta, text="  (sin detalle de productos)",
                         font=FUENTE_BODY, bg=BG_DARK, fg=GRAY_TEXT,
                         anchor="w").pack(fill="x")
            for item in items:
                if not isinstance(item, dict):
                    continue
                nombre = item.get("nombre") or f"Producto #{item.get('id', '?')}"
                cantidad = item.get("cantidad", 0)
                tk.Label(tarjeta, text=f"  - {nombre} x{cantidad}",
                         font=FUENTE_BODY, bg=BG_DARK, fg=GRAY_TEXT,
                         anchor="w").pack(fill="x")

    def _buscar_producto(self, id_producto):
        if self.inventario is None:
            return None
        buscar = getattr(self.inventario, "buscar_por_id", None)
        if callable(buscar):
            try:
                return buscar(id_producto)
            except Exception:
                return None
        if isinstance(self.inventario, (list, tuple)):
            for producto in self.inventario:
                if getattr(producto, "id", None) == id_producto:
                    return producto
        return None

    def _deseos_del_usuario(self):
        if not self.usuario or self.lista_deseos is None:
            return [], []
        try:
            datos = self.lista_deseos.datos_de(self.usuario) or {}
        except Exception:
            datos = {}
        favoritos = list(datos.get("favoritos") or [])
        suscripciones = list(datos.get("suscripciones") or [])
        deseados = []
        for id_producto in favoritos + suscripciones:
            producto = self._buscar_producto(id_producto)
            if producto is None:
                continue
            registro = (producto, id_producto in favoritos, id_producto in suscripciones)
            if registro not in deseados:
                deseados.append(registro)
        return deseados, suscripciones

    def _seccion_deseos(self):
        marco = self._seccion("MI LISTA DE DESEOS")
        if not self.usuario:
            self._mensaje(marco, "Inicia sesión para ver tu lista de deseados.")
            return

        deseados, _suscripciones = self._deseos_del_usuario()
        if not deseados:
            self._mensaje(marco, "Aún no tienes productos guardados en deseados.")
            return

        for producto, es_favorito, es_suscripcion in deseados:
            tarjeta = tk.Frame(marco, bg=BG_DARK, padx=12, pady=8)
            tarjeta.pack(fill="x", pady=4)
            tk.Label(tarjeta, text=producto.nombre, font=FUENTE_NOMBRE,
                     bg=BG_DARK, fg=WHITE, anchor="w").pack(fill="x")
            stock = getattr(producto, "stock", 0)
            estado = "Sin stock" if stock <= 0 else f"Stock: {stock}"
            if es_suscripcion:
                estado += " | Suscrito a reposición"
            tk.Label(
                tarjeta,
                text=f"{_fmt_clp(producto.precio)} | {estado}",
                font=FUENTE_BODY, bg=BG_DARK, fg=GRAY_TEXT, anchor="w",
            ).pack(fill="x", pady=(2, 6))

            acciones = tk.Frame(tarjeta, bg=BG_DARK)
            acciones.pack(fill="x")
            if self.on_ver_producto is not None:
                tk.Button(
                    acciones, text="VER DETALLE", font=FUENTE_BODY,
                    bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0,
                    cursor="hand2", padx=8, pady=3,
                    command=lambda p=producto: self._ver_detalle(p),
                ).pack(side="left", padx=(0, 6))
            if es_favorito and self.on_quitar is not None:
                tk.Button(
                    acciones, text="QUITAR FAVORITO", font=FUENTE_BODY,
                    bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0,
                    cursor="hand2", padx=8, pady=3,
                    command=lambda p=producto: self._quitar(p, False),
                ).pack(side="left", padx=(0, 6))
            if es_suscripcion and self.on_quitar is not None:
                tk.Button(
                    acciones, text="CANCELAR SUSCRIPCIÓN", font=FUENTE_BODY,
                    bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0,
                    cursor="hand2", padx=8, pady=3,
                    command=lambda p=producto: self._quitar(p, True),
                ).pack(side="left", padx=(0, 6))
            if stock > 0 and self.on_agregar_carro is not None:
                tk.Button(
                    acciones, text="AGREGAR AL CARRITO", font=FUENTE_BODY,
                    bg=GREEN, fg="#1a1a1a", relief="flat", bd=0,
                    cursor="hand2", padx=8, pady=3,
                    command=lambda p=producto: self._agregar(p),
                ).pack(side="left")

            # Mantener las acciones accesibles también en ventanas pequeñas.
            botones = acciones.winfo_children()
            for boton in botones:
                boton.pack_forget()

            def distribuir(evento, botones=botones):
                fila = columna = ocupado = 0
                for boton in botones:
                    ancho = boton.winfo_reqwidth() + 6
                    if ocupado and ocupado + ancho > evento.width:
                        fila, columna, ocupado = fila + 1, 0, 0
                    boton.grid(row=fila, column=columna, sticky="w", padx=(0, 6), pady=3)
                    columna += 1
                    ocupado += ancho

            acciones.bind("<Configure>", distribuir)
            for columna, boton in enumerate(botones):
                boton.grid(row=0, column=columna, sticky="w", padx=(0, 6), pady=3)

    def _volver(self):
        if self.on_volver is not None:
            self.on_volver()

    def _ver_detalle(self, producto):
        try:
            self.on_ver_producto(producto)
        except Exception:
            pass

    def _agregar(self, producto):
        if not callable(self.on_agregar_carro):
            return
        try:
            resultado = self.on_agregar_carro(producto)
        except Exception:
            resultado = (False, "No se pudo agregar al carrito")
        if isinstance(resultado, tuple) and len(resultado) == 2 and not resultado[0]:
            _toast(self, resultado[1], tipo="error")

    def _quitar(self, producto, es_suscripcion):
        if not callable(self.on_quitar):
            return
        try:
            resultado = self.on_quitar(producto, es_suscripcion)
        except Exception as error:
            _toast(self, f"No se pudo quitar el producto: {error}", tipo="error")
            return
        if isinstance(resultado, tuple) and len(resultado) == 2:
            ok, mensaje = resultado
        else:
            ok, mensaje = bool(resultado), ""
        self.refrescar()
        _toast(self, mensaje or ("Producto quitado" if ok else "No se pudo quitar"),
               tipo="exito" if ok else "error")
