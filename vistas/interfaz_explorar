"""
interfaz_explorar.py
Pantalla que muestra TODO el catálogo (a diferencia de Principal,
que solo muestra un preview de 4 productos). Tiene scroll vertical
y un filtro de texto -- pensado para que la barra de búsqueda de
la Principal se conecte aquí más adelante (pasando el texto como
filtro_inicial).

Para probar SOLO esta pantalla, ejecuta:
    python interfaz_explorar.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk
try:
    from vistas.estilos import *
except ImportError:
    from estilos import *
try:
    from modelos.inventario import Inventario
except ImportError:
    try:
        from inventario import Inventario
    except ImportError:
        from vistas.inventario import Inventario  # compat legacy (ya eliminado)
try:
    from vistas.interfaz_principal import TarjetaProducto  # reusamos la misma tarjeta, no se duplica código
except ImportError:
    from interfaz_principal import TarjetaProducto

try:
    from vistas.toast import mostrar_toast as _mostrar_toast_fn
except ImportError:
    try:
        from toast import mostrar_toast as _mostrar_toast_fn
    except ImportError:
        _mostrar_toast_fn = None


def _toast(parent, mensaje, tipo="error"):
    if _mostrar_toast_fn is None:
        return
    try:
        _mostrar_toast_fn(parent, mensaje, tipo=tipo)
    except Exception:
        pass


class PantallaExplorar(tk.Frame):
    """
    Catálogo completo, con scroll.

    Parámetros:
        inventario:       instancia de Inventario a mostrar.
        on_volver:        función al hacer click en "VOLVER".
        on_agregar_carro: función al hacer click en "Añadir al Carro".
        filtro_inicial:   texto ya aplicado al abrir esta pantalla
                          (para cuando la búsqueda de la Principal
                          redirija acá con lo que el usuario escribió).
    """

    COLUMNAS_POR_FILA = 3

    def __init__(self, parent, inventario=None, on_volver=None, on_agregar_carro=None, filtro_inicial="", on_ver_carrito=None, usuario_actual=None, on_cerrar_sesion=None):
        super().__init__(parent, bg=BG_DARK)
        # Acepta instancia de Inventario o lista directa
        if inventario is None:
            self.inventario = Inventario()
        elif hasattr(inventario, "productos"):
            self.inventario = inventario
        else:
            # lista suelta: la envolvemos en un objeto simple con .productos
            class _Inv:
                pass
            _inv = _Inv()
            _inv.productos = inventario
            self.inventario = _inv
        self.on_volver = on_volver
        self.on_agregar_carro = on_agregar_carro
        self.on_ver_carrito = on_ver_carrito
        self.usuario_actual = usuario_actual
        self.on_cerrar_sesion = on_cerrar_sesion

        self._crear_barra_superior()
        self._crear_fila_rango()
        self._crear_area_scroll()

        # Se limpia el recolector de eventos de rueda del mouse al
        # salir de esta pantalla -- si no, después de volver a
        # Principal/Admin, seguiría intentando scrollear un canvas
        # que ya no existe.
        self.bind("<Destroy>", self._al_destruir)

        if filtro_inicial:
            self.entry_filtro.insert(0, filtro_inicial)
        self._aplicar_filtro()

    # BARRA SUPERIOR
    def _crear_barra_superior(self):
        barra = tk.Frame(self, bg=BG_DARK)
        barra.pack(fill="x", padx=40, pady=20)

        tk.Label(
            barra, text="RETRO VAULT — Catálogo Completo", font=FUENTE_LOGO,
            bg=BG_DARK, fg=GREEN
        ).pack(side="left")

        volver = tk.Label(
            barra, text="← VOLVER", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, padx=15, pady=8, cursor="hand2"
        )
        volver.pack(side="right")
        volver.bind("<Button-1>", lambda e: self.on_volver() if self.on_volver else None)

        salir = tk.Label(
            barra, text="SALIR", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, padx=15, pady=8, cursor="hand2"
        )
        salir.pack(side="right", padx=(0, 10))
        salir.bind("<Button-1>", lambda e: self._cerrar_sesion())

        nombre = self.usuario_actual or "Invitado"
        tk.Label(
            barra, text=f"👤 {nombre}", font=FUENTE_NAV,
            bg=BG_DARK, fg=GRAY_TEXT, padx=8, pady=8,
        ).pack(side="right", padx=(0, 10))

        if self.on_ver_carrito is not None:
            carrito_btn = tk.Label(
                barra, text="🛒 CARRITO", font=FUENTE_NAV,
                bg=GRAY_BTN, fg=WHITE, padx=15, pady=8, cursor="hand2"
            )
            carrito_btn.pack(side="right", padx=(0, 10))
            carrito_btn.bind("<Button-1>", lambda e: self.on_ver_carrito())

        filtro_frame = tk.Frame(barra, bg=BG_DARK, highlightbackground=GREEN, highlightthickness=1)
        filtro_frame.pack(side="right", padx=20)

        self.entry_filtro = tk.Entry(
            filtro_frame, bg=BG_DARK, fg=WHITE, relief="flat",
            insertbackground=WHITE, width=25, bd=6
        )
        self.entry_filtro.pack(side="left", ipady=4)
        self.entry_filtro.bind("<KeyRelease>", self._aplicar_filtro)

    def _categorias_values(self):
        """["Todas"] + categorías actuales (para el combobox)."""
        if hasattr(self.inventario, "obtener_categorias"):
            return ["Todas"] + self.inventario.obtener_categorias()
        cats = []
        for p in self.inventario.productos:
            if p.categoria not in cats:
                cats.append(p.categoria)
        return ["Todas"] + cats

    def _crear_fila_rango(self):
        """Segunda fila: rango de precios inclusivo Min–Max + categoría + Limpiar (live)."""
        fila = tk.Frame(self, bg=BG_DARK)
        fila.pack(fill="x", padx=40, pady=(0, 4))

        tk.Label(fila, text="Min $", font=FUENTE_NAV, bg=BG_DARK, fg=GRAY_TEXT).pack(side="left")
        self.entry_min = tk.Entry(
            fila, bg=BG_DARK, fg=WHITE, relief="flat", insertbackground=WHITE,
            width=10, bd=4, highlightbackground=GREEN, highlightthickness=1,
        )
        self.entry_min.pack(side="left", padx=(6, 16), ipady=4)
        self.entry_min.bind("<KeyRelease>", self._aplicar_filtro)

        tk.Label(fila, text="Max $", font=FUENTE_NAV, bg=BG_DARK, fg=GRAY_TEXT).pack(side="left")
        self.entry_max = tk.Entry(
            fila, bg=BG_DARK, fg=WHITE, relief="flat", insertbackground=WHITE,
            width=10, bd=4, highlightbackground=GREEN, highlightthickness=1,
        )
        self.entry_max.pack(side="left", padx=(6, 16), ipady=4)
        self.entry_max.bind("<KeyRelease>", self._aplicar_filtro)

        tk.Label(fila, text="Categoría", font=FUENTE_NAV, bg=BG_DARK, fg=GRAY_TEXT).pack(side="left")
        self.combo_categoria = ttk.Combobox(
            fila, font=FUENTE_BODY, width=18, state="readonly",
            values=self._categorias_values(),
        )
        self.combo_categoria.set("Todas")
        self.combo_categoria.pack(side="left", padx=(6, 16))
        self.combo_categoria.bind("<<ComboboxSelected>>", self._aplicar_filtro)

        limpiar = tk.Label(
            fila, text="LIMPIAR", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, padx=15, pady=6, cursor="hand2"
        )
        limpiar.pack(side="left")
        limpiar.bind("<Button-1>", lambda e: self._limpiar_filtros())

    def _limpiar_filtros(self):
        self.entry_filtro.delete(0, tk.END)
        self.entry_min.delete(0, tk.END)
        self.entry_max.delete(0, tk.END)
        self.combo_categoria.set("Todas")
        self._aplicar_filtro()


    # ÁREA CON SCROLL
    # Tkinter no trae un contenedor con scroll automático -- se arma
    # con un Canvas + Scrollbar + un Frame adentro del Canvas. Es la
    # forma estándar de hacerlo en Tkinter puro.

    def _crear_area_scroll(self):
        contenedor = tk.Frame(self, bg=BG_DARK)
        contenedor.pack(fill="both", expand=True, padx=40, pady=(0, 20))

        self.lbl_estado = tk.Label(
            contenedor, text="", font=FUENTE_BODY,
            bg=BG_DARK, fg=GREEN, anchor="w"
        )
        self.lbl_estado.pack(fill="x", pady=(0, 8))

        self.canvas = tk.Canvas(contenedor, bg=DARK_CARD, highlightthickness=0)
        scrollbar = tk.Scrollbar(contenedor, orient="vertical", command=self.canvas.yview)
        self.frame_scrollable = tk.Frame(self.canvas, bg=DARK_CARD)

        self.frame_scrollable.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.configure(yscrollcommand=scrollbar.set)

        # El contenedor ocupa todo el ancho de la caja: sin esto el frame
        # mide solo lo que su contenido pide y sobra caja vacia a la derecha.
        self._ventana_scroll = self.canvas.create_window((0, 0), window=self.frame_scrollable, anchor="nw")
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._ventana_scroll, width=e.width)
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Soporte para la rueda del mouse (Windows/Mac). En Linux el
        # scroll con rueda puede no funcionar por cómo maneja esos
        # eventos ese sistema, pero la scrollbar de al lado siempre
        # funciona igual.
        self.canvas.bind_all("<MouseWheel>", self._sobre_rueda_mouse)

    def _sobre_rueda_mouse(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _al_destruir(self, event):
        if event.widget == self:
            self.unbind_all("<MouseWheel>")


    # FILTRADO Y RENDERIZADO
    def _mostrar_estado(self, msg, es_error=False):
        """Avisos/errores EN PANTALLA (label + toast flotante)."""
        try:
            from vistas.estilos import GREEN as _GREEN
        except ImportError:
            try:
                from estilos import GREEN as _GREEN
            except ImportError:
                _GREEN = "green"
        self.lbl_estado.config(text=msg, fg="#ff6b6b" if es_error else _GREEN)
        _toast(self, msg, tipo="error" if es_error else "exito")

    def _cerrar_sesion(self):
        if self.on_cerrar_sesion:
            self.on_cerrar_sesion()
        else:
            self._mostrar_estado("Cerrar sesion no disponible en vista aislada", es_error=True)

    def _on_agregar(self, producto):
        """Wrapper que muestra el resultado de añadir EN PANTALLA."""
        if self.on_agregar_carro is None:
            self._mostrar_estado("Carrito no disponible en vista aislada", es_error=True)
            return
        resultado = self.on_agregar_carro(producto)
        if isinstance(resultado, tuple) and len(resultado) == 2:
            ok, msg = resultado
            self._mostrar_estado(msg, es_error=not ok)
        elif isinstance(resultado, str) and resultado:
            self._mostrar_estado(resultado, es_error=False)
        else:
            self._mostrar_estado(f"Añadido: {producto.nombre}", es_error=False)

    def _set_conteo(self, n, total):
        """Conteo silencioso en lbl_estado (sin toast para no spamear al tipear)."""
        try:
            from vistas.estilos import GREEN as _GREEN
        except ImportError:
            try:
                from estilos import GREEN as _GREEN
            except ImportError:
                _GREEN = "green"
        self.lbl_estado.config(text=f"{n} de {total} productos", fg=_GREEN)

    def _aplicar_filtro(self, event=None):
        texto = self.entry_filtro.get().strip()
        min_txt = self.entry_min.get().strip()
        max_txt = self.entry_max.get().strip()

        # Cotas no numéricas → error visible, se ignora esa cota
        hubo_error = False
        minimo = Inventario.parse_precio_filtro(min_txt)
        maximo = Inventario.parse_precio_filtro(max_txt)
        if min_txt and minimo is None:
            self._mostrar_estado("El minimo debe ser un numero", es_error=True)
            minimo = None
            hubo_error = True
        if max_txt and maximo is None:
            self._mostrar_estado("El maximo debe ser un numero", es_error=True)
            maximo = None
            hubo_error = True
        if minimo is not None and maximo is not None and minimo > maximo:
            self._mostrar_estado("El minimo no puede ser mayor al maximo", es_error=True)
            self._renderizar([])
            return

        base = self.inventario.buscar_por_nombre(texto) if hasattr(self.inventario, "buscar_por_nombre") else [
            p for p in self.inventario.productos
            if not texto or texto.lower() in p.nombre.lower() or texto.lower() in p.categoria.lower()
        ]
        # Categoria exacta (combobox): refresca valores por si admin creo una nueva
        categoria = self.combo_categoria.get().strip() if hasattr(self, "combo_categoria") else "Todas"
        try:
            if hasattr(self, "combo_categoria"):
                actual = self._categorias_values()
                if list(self.combo_categoria["values"]) != actual:
                    self.combo_categoria["values"] = actual
                    if categoria not in actual:
                        self.combo_categoria.set("Todas")
                        categoria = "Todas"
        except Exception:
            pass
        if hasattr(self.inventario, "filtrar_por_categoria"):
            base = self.inventario.filtrar_por_categoria(categoria, base)
        elif categoria and categoria.lower() != "todas":
            base = [p for p in base if p.categoria.lower() == categoria.lower()]
        if hasattr(self.inventario, "filtrar_por_rango_precio"):
            productos = self.inventario.filtrar_por_rango_precio(minimo, maximo, base)
        else:
            productos = [
                p for p in base
                if (minimo is None or float(p.precio) >= minimo)
                and (maximo is None or float(p.precio) <= maximo)
            ]

        if not hubo_error:
            self._set_conteo(len(productos), len(self.inventario.productos))
        self._renderizar(productos)

    def _renderizar(self, productos):
        for widget in self.frame_scrollable.winfo_children():
            widget.destroy()

        if not productos:
            tk.Label(
                self.frame_scrollable, text="No se encontraron productos",
                font=FUENTE_BODY, bg=DARK_CARD, fg=GRAY_TEXT
            ).grid(row=0, column=0, columnspan=self.COLUMNAS_POR_FILA, padx=20, pady=40)
            return

        for i, producto in enumerate(productos):
            fila = i // self.COLUMNAS_POR_FILA
            columna = i % self.COLUMNAS_POR_FILA
            tarjeta = TarjetaProducto(self.frame_scrollable, producto, on_agregar_carro=self._on_agregar)
            tarjeta.grid(row=fila, column=columna, padx=12, pady=12, sticky="nsew")

        # 3 columnas fijas que reparten todo el ancho por igual
        for c in range(self.COLUMNAS_POR_FILA):
            self.frame_scrollable.grid_columnconfigure(c, weight=1, uniform="cols")


# PRUEBA INDEPENDIENTE

if __name__ == "__main__":
    root = tk.Tk()
    root.title("RetroVault - Explorar")
    root.geometry("1100x700")
    root.configure(bg=BG_DARK)

    pantalla = PantallaExplorar(root)
    pantalla.pack(fill="both", expand=True)

    root.mainloop()