"""
interfaz_principal.py
Pantalla principal (home) de RetroVault: navbar, banner y catálogo.

Para probar SOLO esta pantalla, ejecuta:
    python interfaz_principal.py
"""

import tkinter as tk
from estilos import *


class TarjetaProducto(tk.Frame):
    """
    Una tarjeta individual de producto dentro del catálogo.

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
        # Placeholder de imagen: NO se generan imágenes de personajes
        # con derechos de autor (Mario, Zelda, etc.). Reemplaza esto
        # por tu propia imagen -> ver nota de PhotoImage más abajo.
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

        # Bono: si el producto está sin stock, deshabilita el botón.
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
        print(f"🛒 Añadido al carro: {self.producto.nombre}")
        if self.on_agregar_carro:
            self.on_agregar_carro(self.producto)


class PantallaPrincipal(tk.Frame):
    """
    Pantalla principal / home de la tienda.

    Parámetros:
        inventario:        lista de objetos Producto a mostrar.
                            Si no se entrega, se usan productos de
                            ejemplo (para poder probar esta pantalla
                            sola, sin el resto del proyecto).
        on_agregar_carro:  función que se llama cuando el usuario
                            hace click en "Añadir al Carro".
    """

    def __init__(self, parent, inventario=None, on_agregar_carro=None):
        super().__init__(parent, bg=BG_DARK)
        self.inventario = inventario if inventario is not None else self._productos_ejemplo()
        self.on_agregar_carro = on_agregar_carro

        self._crear_navbar()
        self._crear_hero()
        self._crear_catalogo()

    def _productos_ejemplo(self):
        """Productos de ejemplo, solo para poder probar esta pantalla sola."""
        class ProductoSimple:
            def __init__(self, nombre, precio, categoria, stock=10):
                self.nombre = nombre
                self.precio = precio
                self.categoria = categoria
                self.stock = stock

        return [
            ProductoSimple("Super Nintendo", 149990, "Consolas", stock=4),
            ProductoSimple("The Legend of Zelda: Ocarina of Time", 89990, "Videojuegos", stock=12),
            ProductoSimple("Super Mario 64", 99990, "Videojuegos", stock=0),  # ejemplo sin stock
        ]

    # ------------------------------------------------------------------
    # NAVBAR
    # ------------------------------------------------------------------
    def _crear_navbar(self):
        navbar = tk.Frame(self, bg=BG_DARK)
        navbar.pack(fill="x", padx=40, pady=20)

        tk.Label(
            navbar, text="RETRO VAULT", font=FUENTE_LOGO, bg=BG_DARK, fg=GREEN
        ).pack(side="left")

        nav_links = tk.Frame(navbar, bg=BG_DARK)
        nav_links.pack(side="left", padx=40)

        self._link_nav(nav_links, "INICIO", activo=True).pack(side="left", padx=8)
        self._link_nav(nav_links, "CATEGORIAS").pack(side="left", padx=8)
        self._link_nav(nav_links, "CONTACTANOS").pack(side="left", padx=8)

        # Buscador
        buscador_frame = tk.Frame(
            navbar, bg=BG_DARK, highlightbackground=GREEN,
            highlightcolor=GREEN, highlightthickness=1
        )
        buscador_frame.pack(side="left", padx=20)

        buscador = tk.Entry(
            buscador_frame, bg=BG_DARK, fg=GRAY_TEXT, relief="flat",
            insertbackground=WHITE, width=22, bd=6
        )
        buscador.insert(0, "Search")
        buscador.pack(side="left", ipady=4)

        # Iconos derecha (carrito / perfil)
        iconos = tk.Frame(navbar, bg=BG_DARK)
        iconos.pack(side="right")

        tk.Label(
            iconos, text="🛒", font=("Arial", 13), bg=GRAY_BTN, fg=WHITE,
            padx=12, pady=6, cursor="hand2"
        ).pack(side="left", padx=4)
        tk.Label(
            iconos, text="👤", font=("Arial", 13), bg=GRAY_BTN, fg=WHITE,
            padx=12, pady=6, cursor="hand2"
        ).pack(side="left", padx=4)

    def _link_nav(self, parent, texto, activo=False):
        return tk.Label(
            parent, text=texto, font=FUENTE_NAV,
            bg=BG_DARK, fg=WHITE if activo else GRAY_TEXT, cursor="hand2"
        )

    # ------------------------------------------------------------------
    # HERO / BANNER
    # ------------------------------------------------------------------
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
            command=lambda: print("Ir a ofertas")
        ).pack(anchor="w")

        # Placeholder del banner (sin personajes con derechos de autor)
        banner = tk.Canvas(hero, width=380, height=160, bg="#12261a", highlightthickness=0)
        banner.pack(side="right", padx=20)
        banner.create_text(
            190, 80, fill=GREEN, font=("Arial", 11, "bold"), justify="center",
            text="🕹️ Banner de ofertas\n(reemplaza con tu propia imagen PNG)"
        )

    # ------------------------------------------------------------------
    # CATÁLOGO DE PRODUCTOS
    # ------------------------------------------------------------------
    def _crear_catalogo(self):
        contenedor = tk.Frame(self, bg=DARK_CARD)
        contenedor.pack(fill="both", expand=True, padx=60, pady=20)

        grid = tk.Frame(contenedor, bg=DARK_CARD)
        grid.pack(padx=20, pady=20)

        for i, producto in enumerate(self.inventario):
            tarjeta = TarjetaProducto(grid, producto, on_agregar_carro=self.on_agregar_carro)
            tarjeta.grid(row=0, column=i, padx=12)


# ==============================================================================
# PRUEBA INDEPENDIENTE
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("RetroVault - Inicio")
    root.geometry("1100x700")
    root.configure(bg=BG_DARK)

    pantalla = PantallaPrincipal(root)
    pantalla.pack(fill="both", expand=True)

    root.mainloop()