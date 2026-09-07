"""
interfaz_principal.py
Pantalla principal (home) de RetroVault: navbar, banner y catalogo.

Para probar SOLO esta pantalla, ejecuta:
    python interfaz_principal.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
try:
    from vistas.estilos import *
except ImportError:
    from estilos import *

try:
    from vistas.toast import mostrar_toast
except ImportError:
    try:
        from toast import mostrar_toast
    except ImportError:
        mostrar_toast = None


def _toast(parent, mensaje, tipo="error"):
    if mostrar_toast is None:
        return
    try:
        mostrar_toast(parent, mensaje, tipo=tipo)
    except Exception:
        pass


def _ruta_abs_imagen(ruta_rel):
    """Resuelve una ruta relativa (data/imagenes/xxx.png) a absoluta."""
    if not ruta_rel:
        return None
    if os.path.isabs(ruta_rel):
        return ruta_rel if os.path.exists(ruta_rel) else None
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    abs_path = os.path.join(base, ruta_rel.replace("/", os.sep))
    return abs_path if os.path.exists(abs_path) else None


def cargar_png(ruta_rel, max_w=190, max_h=140):
    """
    Carga un PNG nativo con tkinter y lo reescala por enteros.
    Retorna PhotoImage o None (placeholder). Solo PNG (sin Pillow).
    """
    abs_path = _ruta_abs_imagen(ruta_rel)
    if abs_path is None or not abs_path.lower().endswith(".png"):
        return None
    try:
        img = tk.PhotoImage(file=abs_path)
    except Exception:
        return None
    try:
        fx = max(1, -(-img.width() // max_w))  # ceil
        fy = max(1, -(-img.height() // max_h))
        f = max(fx, fy)
        if f > 1:
            img = img.subsample(f, f)
    except Exception:
        pass
    return img


class TarjetaProducto(tk.Frame):
    """
    Una tarjeta individual de producto dentro del catalogo.

    Recibe un objeto "producto" con atributos .nombre, .precio,
    .categoria (y opcionalmente .stock) -> es 100% compatible con
    tu clase Producto del Item 1 / Item 3, así que puedes pasarle
    directamente los productos de tu Inventario real.
    """

    def __init__(self, parent, producto, on_agregar_carro=None):
        super().__init__(parent, bg=DARK_CARD, padx=15, pady=15)
        self.producto = producto
        self.on_agregar_carro = on_agregar_carro
        self._construir()

    def _construir(self):
        # Foto real del producto (PNG en data/imagenes/) o placeholder 🎮.
        # Las fotos las carga el admin con Examinar PNG; sin foto o ruta
        # rota se muestra el placeholder sin romper la tarjeta.
        self._img = cargar_png(getattr(self.producto, "imagen", None), 190, 140)
        if self._img is not None:
            tk.Label(self, image=self._img, bg=DARK_CARD, width=190, height=140).pack()
        else:
            imagen = tk.Canvas(self, width=190, height=140, bg="#e4e4e4", highlightthickness=0)
            imagen.pack()
            imagen.create_text(95, 70, text="🎮", font=("Arial", 36))

        tk.Label(
            self, text=self.producto.categoria.upper(),
            font=FUENTE_CATEGORIA, bg=DARK_CARD, fg=GRAY_TEXT
        ).pack(anchor="w", pady=(12, 2))

        tk.Label(
            self, text=self.producto.nombre, font=FUENTE_NOMBRE,
            bg=DARK_CARD, fg=WHITE, wraplength=190, justify="left"
        ).pack(anchor="w")

        precio_formateado = f"${self.producto.precio:,.0f}".replace(",", ".")
        tk.Label(
            self, text=precio_formateado, font=FUENTE_PRECIO,
            bg=DARK_CARD, fg=WHITE
        ).pack(anchor="w", pady=(6, 12))

        # Bono: si el producto esta sin stock, deshabilita el boton.
        # Esto conecta directo con el atributo stock que ya manejas
        # en el Item 1 (CRUD) y el Item 3 (menor stock por categoría).
        sin_stock = getattr(self.producto, "stock", 1) <= 0

        tk.Button(
            self,
            text="Sin Stock" if sin_stock else "Añadir al Carro",
            font=FUENTE_BOTON,
            bg=GRAY_TEXT if sin_stock else GREEN,
            fg=WHITE if sin_stock else BLACK,
            relief="flat", bd=0,
            state="disabled" if sin_stock else "normal",
            cursor="arrow" if sin_stock else "hand2",
            command=self._agregar
        ).pack(fill="x", ipady=6)

    def _agregar(self):
        if self.on_agregar_carro:
            self.on_agregar_carro(self.producto)


class PantallaPrincipal(tk.Frame):
    """
    Pantalla principal / home de la tienda.

    Parametros:
        inventario:        lista de objetos Producto a mostrar.
                           Si no se entrega, se usan productos de
                           ejemplo (para poder probar esta pantalla
                           sola, sin el resto del proyecto).
        on_agregar_carro:  función que se llama cuando el usuario
                           hace click en "Añadir al Carro".
    """

    def __init__(self, parent, inventario=None, on_agregar_carro=None, on_ir_admin=None, on_ver_carrito=None, on_ir_explorar=None, usuario_actual=None, es_admin=False, on_cerrar_sesion=None):
        super().__init__(parent, bg=BG_DARK)
        # Acepta tanto lista de productos como instancia de Inventario
        if inventario is None:
            self.inventario = self._productos_ejemplo()
        elif hasattr(inventario, "productos"):
            self.inventario = inventario.productos
        else:
            self.inventario = inventario
        self.on_agregar_carro = on_agregar_carro
        self.on_ir_admin = on_ir_admin
        self.on_ver_carrito = on_ver_carrito
        self.on_ir_explorar = on_ir_explorar
        self.usuario_actual = usuario_actual
        self.es_admin = bool(es_admin)
        self.on_cerrar_sesion = on_cerrar_sesion

        self._crear_navbar()
        self._crear_hero()
        self._crear_catalogo()

    def _productos_ejemplo(self):
        """Productos de ejemplo, solo para poder probar esta pantalla sola."""
        class ProductoSimple:
            def __init__(self, id, nombre, precio, categoria, stock=10):
                self.id = id
                self.nombre = nombre
                self.precio = precio
                self.categoria = categoria
                self.stock = stock

        return [
            ProductoSimple(1, "Super Nintendo", 149990, "Consolas", stock=4),
            ProductoSimple(2, "The Legend of Zelda: Ocarina of Time", 89990, "Videojuegos", stock=12),
            ProductoSimple(3, "Super Mario 64", 99990, "Videojuegos", stock=0),  # ejemplo sin stock
        ]

    # NAVBAR
    def _crear_navbar(self):
        navbar = tk.Frame(self, bg=BG_DARK)
        navbar.pack(fill="x", padx=40, pady=20)

        tk.Label(
            navbar, text="RETRO VAULT", font=FUENTE_LOGO, bg=BG_DARK, fg=GREEN
        ).pack(side="left")

        nav_links = tk.Frame(navbar, bg=BG_DARK)
        nav_links.pack(side="left", padx=40)

        self._link_nav(nav_links, "INICIO", activo=True).pack(side="left", padx=8)
        link_categorias = self._link_nav(nav_links, "CATEGORIAS")
        link_categorias.pack(side="left", padx=8)
        link_categorias.bind("<Button-1>", lambda e: self._ir_explorar(limpio=True))
        self._link_nav(nav_links, "CONTACTANOS").pack(side="left", padx=8)

        # ADMIN oculto para usuarios normales: solo se crea si es_admin
        if self.es_admin:
            admin_link = self._link_nav(nav_links, "ADMIN")
            admin_link.pack(side="left", padx=8)
            admin_link.bind("<Button-1>", lambda e: self._ir_admin())

        # Buscador con eventos de placeholder y filtrado
        buscador_frame = tk.Frame(
            navbar, bg=BG_DARK, highlightbackground=GREEN,
            highlightcolor=GREEN, highlightthickness=1
        )
        buscador_frame.pack(side="left", padx=20)

        self.buscador = tk.Entry(
            buscador_frame, bg=BG_DARK, fg=GRAY_TEXT, relief="flat",
            insertbackground=WHITE, width=22, bd=6
        )
        self.buscador.insert(0, "Search")
        self.buscador.pack(side="left", ipady=4)

        # Eventos para controlar el borrado automático y la búsqueda
        self.buscador.bind("<FocusIn>", self._on_focus_in)
        self.buscador.bind("<FocusOut>", self._on_focus_out)
        self.buscador.bind("<KeyRelease>", lambda e: self._filtrar_catalogo())

        # Iconos derecha (carrito / perfil)
        iconos = tk.Frame(navbar, bg=BG_DARK)
        iconos.pack(side="right")

        lbl_carrito = tk.Label(
            iconos, text="🛒", font=("Arial", 13), bg=GRAY_BTN, fg=WHITE,
            padx=12, pady=6, cursor="hand2"
        )
        lbl_carrito.pack(side="left", padx=4)
        lbl_carrito.bind("<Button-1>", lambda e: self._abrir_carrito())

        nombre = self.usuario_actual or "Invitado"
        lbl_user = tk.Label(
            iconos, text=f"👤 {nombre}", font=FUENTE_NAV,
            bg=BG_DARK, fg=GRAY_TEXT, padx=8, pady=6,
        )
        lbl_user.pack(side="left", padx=4)

        lbl_salir = tk.Label(
            iconos, text="SALIR", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, padx=12, pady=6, cursor="hand2"
        )
        lbl_salir.pack(side="left", padx=4)
        lbl_salir.bind("<Button-1>", lambda e: self._cerrar_sesion())

    def _ir_admin(self):
        if self.on_ir_admin:
            self.on_ir_admin()
        else:
            self._mostrar_estado("Admin no disponible en vista aislada", es_error=True)

    def _cerrar_sesion(self):
        if self.on_cerrar_sesion:
            self.on_cerrar_sesion()
        else:
            self._mostrar_estado("Cerrar sesión no disponible en vista aislada", es_error=True)

    def _on_focus_in(self, event):
        """Borra 'Search' cuando el usuario hace clic dentro."""
        if self.buscador.get() == "Search":
            self.buscador.delete(0, tk.END)
            self.buscador.config(fg=WHITE)

    def _on_focus_out(self, event):
        """Restaura 'Search' si la caja queda vacia al salir de ella."""
        if not self.buscador.get().strip():
            self.buscador.insert(0, "Search")
            self.buscador.config(fg=GRAY_TEXT)
            self._filtrar_catalogo()

    def _abrir_carrito(self):
        if self.on_ver_carrito:
            self.on_ver_carrito()
        else:
            self._mostrar_estado("Carrito no disponible en vista aislada", es_error=True)

    def _mostrar_estado(self, msg, es_error=False):
        """Avisos/errores EN PANTALLA (label catálogo + toast flotante)."""
        if hasattr(self, "lbl_estado"):
            self.lbl_estado.config(text=msg, fg="#ff6b6b" if es_error else GREEN)
        _toast(self, msg, tipo="error" if es_error else "exito")

    def _on_agregar(self, producto):
        """Wrapper que muestra el resultado de añadir EN PANTALLA."""
        if self.on_agregar_carro is None:
            self._mostrar_estado("Carrito no disponible en vista aislada", es_error=True)
            return
        resultado = self.on_agregar_carro(producto)
        # main_gui retorna (ok, msg); en standalone puede retornar None
        if isinstance(resultado, tuple) and len(resultado) == 2:
            ok, msg = resultado
            self._mostrar_estado(msg, es_error=not ok)
        elif isinstance(resultado, str) and resultado:
            self._mostrar_estado(resultado, es_error=False)
        else:
            self._mostrar_estado(f"Añadido: {producto.nombre}", es_error=False)

    def _ir_explorar(self, limpio=False):
        if self.on_ir_explorar:
            if limpio:
                # CATEGORIAS abre Explorar limpio: combo en Todas, sin texto
                self.on_ir_explorar(filtro_inicial="")
                return
            texto = self.buscador.get().strip()
            if texto == "Search":
                texto = ""
            self.on_ir_explorar(filtro_inicial=texto)
        else:
            self._mostrar_estado("Explorar no disponible en vista aislada", es_error=True)

    def _link_nav(self, parent, texto, activo=False):
        return tk.Label(
            parent, text=texto, font=FUENTE_NAV,
            bg=BG_DARK, fg=WHITE if activo else GRAY_TEXT, cursor="hand2"
        )

    # HERO / BANNER
    def _crear_hero(self):
        hero = tk.Frame(self, bg=BG_DARK)
        hero.pack(fill="x", padx=60, pady=20)

        izquierda = tk.Frame(hero, bg=BG_DARK)
        izquierda.pack(side="left", fill="y")

        tk.Label(
            izquierda, text="REVIVE LAS OFERTAS", font=FUENTE_HERO,
            bg=BG_DARK, fg=WHITE, justify="left"
        ).pack(anchor="w")
        tk.Label(
            izquierda, text="DEL INVIERNO", font=FUENTE_HERO,
            bg=BG_DARK, fg=WHITE, justify="left"
        ).pack(anchor="w", pady=(0, 20))

        tk.Button(
            izquierda, text="EXPLORAR OFERTAS", font=FUENTE_BOTON,
            bg=GREEN, fg=BLACK, relief="flat", bd=0, cursor="hand2",
            padx=20, pady=10,
            command=self._ir_explorar
        ).pack(anchor="w")

        # Placeholder del banner (sin personajes con derechos de autor)
        banner = tk.Canvas(hero, width=380, height=160, bg="#12261a", highlightthickness=0)
        banner.pack(side="right", padx=20)
        banner.create_text(
            190, 80, fill=GREEN, font=("Arial", 11, "bold"), justify="center",
            text="Banner de ofertas\n(Colocar imagen aqui)"
        )

    # CATALOGO DE PRODUCTOS
    def _crear_catalogo(self):
        contenedor = tk.Frame(self, bg=DARK_CARD)
        contenedor.pack(fill="both", expand=True, padx=60, pady=20)

        self.lbl_estado = tk.Label(
            contenedor, text="", font=FUENTE_BODY,
            bg=DARK_CARD, fg=GREEN, anchor="w"
        )
        self.lbl_estado.pack(fill="x", padx=20, pady=(12, 0))

        self.grid_catalogo = tk.Frame(contenedor, bg=DARK_CARD)
        self.grid_catalogo.pack(padx=20, pady=20)

        self._renderizar_tarjetas(self.inventario)

    def _renderizar_tarjetas(self, productos):
        for widget in self.grid_catalogo.winfo_children():
            widget.destroy()

        if not productos:
            tk.Label(
                self.grid_catalogo, text="No se encontraron productos",
                font=FUENTE_BODY, bg=DARK_CARD, fg=GRAY_TEXT
            ).pack(padx=20, pady=40)
            return

        for i, producto in enumerate(productos):
            tarjeta = TarjetaProducto(self.grid_catalogo, producto, on_agregar_carro=self._on_agregar)
            tarjeta.grid(row=0, column=i, padx=12)

    def _filtrar_catalogo(self):
        texto = self.buscador.get().strip()

        if not texto or texto == "Search":
            self._renderizar_tarjetas(self.inventario)
            return

        resultados = []
        for p in self.inventario:
            id_prod = str(getattr(p, "id", ""))
            if texto == id_prod or texto.lower() in p.nombre.lower():
                resultados.append(p)

        self._renderizar_tarjetas(resultados)

# PRUEBA INDEPENDIENTE
if __name__ == "__main__":
    root = tk.Tk()
    root.title("RetroVault - Inicio")
    root.geometry("1100x700")
    root.configure(bg=BG_DARK)

    pantalla = PantallaPrincipal(root)
    pantalla.pack(fill="both", expand=True)

    root.mainloop()