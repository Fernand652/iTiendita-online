"""
carrito.py
Pantalla de Carrito de Compras de RetroVault.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
try:
    from vistas.estilos import *
except ImportError:
    try:
        from estilos import *
    except ImportError:
        from vistas.estilos import *  # último intento
try:
    from modelos.producto import Producto
except ImportError:
    try:
        from producto import Producto
    except ImportError:
        try:
            from vistas.producto import Producto
        except ImportError:
            Producto = None  # solo para type hints en demo

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


class carrito(tk.Frame):
    def __init__(self, parent, on_volver=None, on_pagar=None, fn_calcular_total=None, usuario_actual=None, on_cerrar_sesion=None):
        super().__init__(parent, bg=BG_DARK)
        self.parent = parent
        self.on_volver = on_volver
        self.on_pagar = on_pagar
        self.fn_calcular_total = fn_calcular_total
        self.usuario_actual = usuario_actual
        self.on_cerrar_sesion = on_cerrar_sesion
        self.pack(fill="both", expand=True)

        self.lista_actual = []

        self._crear_barra_superior()
        self._crear_interfaz()


    # BARRA SUPERIOR
    def _crear_barra_superior(self):
        barra = tk.Frame(self, bg=BG_DARK)
        barra.pack(fill="x", padx=40, pady=25)

        tk.Label(barra, text="RETRO VAULT", font=FUENTE_LOGO, bg=BG_DARK, fg=GREEN).pack(side="left")

        btn_volver = tk.Label(
            barra, text="VOLVER", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, padx=15, pady=8, cursor="hand2"
        )
        btn_volver.pack(side="right")
        btn_volver.bind("<Button-1>", lambda e: self.volver())

        btn_salir = tk.Label(
            barra, text="SALIR", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, padx=15, pady=8, cursor="hand2"
        )
        btn_salir.pack(side="right", padx=(0, 10))
        btn_salir.bind("<Button-1>", lambda e: self._cerrar_sesion())

        nombre = self.usuario_actual or "Invitado"
        tk.Label(
            barra, text=f"👤 {nombre}", font=FUENTE_NAV,
            bg=BG_DARK, fg=GRAY_TEXT, padx=8, pady=8,
        ).pack(side="right", padx=(0, 10))

    # LAYOUT DE 2 COLUMNAS 
    def _crear_interfaz(self):
        cuerpo = tk.Frame(self, bg=BG_DARK)
        cuerpo.pack(fill="both", expand=True, padx=40, pady=(0, 25))

        tk.Label(cuerpo, text="TU CARRITO", font=FUENTE_TITULO, bg=BG_DARK, fg=WHITE).pack(anchor="w", pady=(0, 20))

        columnas = tk.Frame(cuerpo, bg=BG_DARK)
        columnas.pack(fill="both", expand=True)

        # Columna Izquierda: Items
        self.col_izquierda = tk.Frame(columnas, bg=BG_DARK)
        self.col_izquierda.pack(side="left", fill="both", expand=True, padx=(0, 25))

        # Columna Derecha: Resumen
        resumen = tk.Frame(columnas, bg=DARK_CARD, width=320, padx=25, pady=25)
        resumen.pack(side="right", fill="y")
        resumen.pack_propagate(False)

        tk.Label(resumen, text="RESUMEN", font=FUENTE_TITULO, bg=DARK_CARD, fg=WHITE).pack(anchor="w", pady=(0, 20))
        tk.Frame(resumen, bg=GRAY_BTN, height=1).pack(fill="x", pady=15)

        fila_total = tk.Frame(resumen, bg=DARK_CARD)
        fila_total.pack(fill="x", pady=(0, 25))
        tk.Label(fila_total, text="TOTAL", font=FUENTE_PRECIO, bg=DARK_CARD, fg=WHITE).pack(side="left")
        self.lbl_total = tk.Label(fila_total, text="$0.00", font=FUENTE_HERO, bg=DARK_CARD, fg=GREEN)
        self.lbl_total.pack(side="right")

        tk.Button(
            resumen, text="PAGAR AHORA", font=FUENTE_BOTON,
            bg=GREEN, fg=BLACK, activebackground=GREEN_HOVER,
            relief="flat", bd=0, cursor="hand2", command=self.pagar
        ).pack(fill="x", ipady=10)

        self.lbl_mensaje = tk.Label(
            resumen, text="", font=FUENTE_BODY,
            bg=DARK_CARD, fg="#ff6b6b", wraplength=270, justify="left"
        )
        self.lbl_mensaje.pack(fill="x", pady=(10, 0))


    def _mostrar_mensaje(self, msg, tipo="error"):
        """Error/aviso EN PANTALLA (label Resumen + toast flotante)."""
        self.lbl_mensaje.config(text=msg)
        _toast(self, msg, tipo=tipo)

    def _limpiar_mensaje(self):
        self.lbl_mensaje.config(text="")

    # METODOS DE PRODUCTOS PARA AGREGAR, ELIMINAR Y ACTUALIZAR CANTIDADES
    def mostrar_productos(self, items):
        """
        items puede ser:
        - Una lista de diccionarios: [{'producto': Producto(...), 'cantidad': 1}, ...]
        - O una lista simple de instancias de Producto
        """
        self.lista_actual = []
        for i in items:
            if isinstance(i, dict):
                self.lista_actual.append(i)
            else:
                self.lista_actual.append({"producto": i, "cantidad": 1})

        if not self.lista_actual:
            tk.Label(
                self.col_izquierda, text="Tu carrito esta vacio",
                font=FUENTE_TITULO, bg=BG_DARK, fg=GRAY_TEXT
            ).pack(pady=40)
            self.lbl_total.config(text="$0")
            self._limpiar_mensaje()
            return

        self._limpiar_mensaje()

        for elemento in self.lista_actual:
            prod = elemento["producto"]
            cant = elemento["cantidad"]

            tarjeta = tk.Frame(self.col_izquierda, bg=DARK_CARD, padx=15, pady=15)
            tarjeta.pack(fill="x", pady=6)

            # Miniatura PNG (64x48) si el producto tiene foto, sino nada
            try:
                from vistas.interfaz_principal import cargar_png as _cargar_png
            except ImportError:
                try:
                    from interfaz_principal import cargar_png as _cargar_png
                except ImportError:
                    _cargar_png = None
            if _cargar_png is not None:
                try:
                    thumb = _cargar_png(getattr(prod, "imagen", None), 64, 48)
                except Exception:
                    thumb = None
                if thumb is not None:
                    # guardar referencia en el widget para evitar GC
                    lbl_thumb = tk.Label(tarjeta, image=thumb, bg=DARK_CARD)
                    lbl_thumb.image = thumb
                    lbl_thumb.pack(side="left", padx=(0, 12))

            # Informacion del producto
            info = tk.Frame(tarjeta, bg=DARK_CARD)
            info.pack(side="left", fill="both", expand=True)

            tk.Label(info, text=str(prod.categoria).upper(), font=FUENTE_CATEGORIA, bg=DARK_CARD, fg=GREEN).pack(anchor="w")
            tk.Label(info, text=prod.nombre, font=FUENTE_NOMBRE, bg=DARK_CARD, fg=WHITE).pack(anchor="w", pady=(2, 5))
            tk.Label(info, text=f"${float(prod.precio):.2f} c/u", font=FUENTE_PRECIO, bg=DARK_CARD, fg=GRAY_TEXT).pack(anchor="w")

            # Botones de cantidad y eliminar
            controles = tk.Frame(tarjeta, bg=DARK_CARD)
            controles.pack(side="right")

            # Boton (-) para disminuir la cantidad de productos, respetando el mínimo de 1
            btn_menos = tk.Label(controles, text="-", font=FUENTE_BOTON, bg=GRAY_BTN, fg=WHITE, width=2, cursor="hand2")
            btn_menos.pack(side="left", padx=2)
            btn_menos.bind("<Button-1>", lambda e, el=elemento: self._cambiar_cantidad(el, -1))

            # Indicador de cantidad de productos en el carrito
            lbl_cant = tk.Label(controles, text=str(cant), font=FUENTE_BODY, bg=DARK_CARD, fg=WHITE, width=3)
            lbl_cant.pack(side="left", padx=4)

            # Boton (+) para aumentar la cantidad de productos, respetando el stock disponible
            btn_mas = tk.Label(controles, text="+", font=FUENTE_BOTON, bg=GRAY_BTN, fg=WHITE, width=2, cursor="hand2")
            btn_mas.pack(side="left", padx=2)
            btn_mas.bind("<Button-1>", lambda e, el=elemento: self._cambiar_cantidad(el, 1))

            # Boton (X) para eliminar el producto del carrito
            btn_del = tk.Label(controles, text="X", font=FUENTE_BOTON, bg=DARK_CARD, fg=RED_BADGE, cursor="hand2", padx=8)
            btn_del.pack(side="left", padx=(8, 0))
            btn_del.bind("<Button-1>", lambda e, el=elemento: self._eliminar_producto(el))

        self._actualizar_total()

    def _cambiar_cantidad(self, elemento, delta):
        nueva = elemento["cantidad"] + delta
        if nueva <= 0:
            self._eliminar_producto(elemento)
        elif nueva <= elemento["producto"].stock:
            elemento["cantidad"] = nueva
            self.actualizar_carrito(self.lista_actual)
        else:
            self._mostrar_mensaje(f"Stock máximo disponible: {elemento['producto'].stock}", tipo="error")

    def _eliminar_producto(self, elemento):
        if elemento in self.lista_actual:
            self.lista_actual.remove(elemento)
            self.actualizar_carrito(self.lista_actual)

    def _actualizar_total(self):
        if self.fn_calcular_total:
            total = self.fn_calcular_total(self.lista_actual)
            self.lbl_total.config(text=f"${total:.2f}")

    def actualizar_carrito(self, productos):
        for widget in self.col_izquierda.winfo_children():
            widget.destroy()
        self.mostrar_productos(productos)

    def volver(self):
        if self.on_volver:
            self.on_volver()
        else:
            self._mostrar_mensaje("Volver no disponible en vista aislada", tipo="info")

    def _cerrar_sesion(self):
        if self.on_cerrar_sesion:
            self.on_cerrar_sesion()
        else:
            self._mostrar_mensaje("Cerrar sesión no disponible en vista aislada", tipo="info")

    def pagar(self):
        if not self.lista_actual:
            self._mostrar_mensaje("Tu carrito está vacío, agrega productos primero", tipo="error")
            return
        if self.on_pagar:
            self._limpiar_mensaje()
            _toast(self, "Procediendo al pago…", tipo="exito")
            self.after(400, self.on_pagar)
        else:
            total_txt = self.lbl_total.cget("text")
            self._limpiar_mensaje()
            _toast(self, f"Pago por {total_txt} ¡Gracias!", tipo="exito")



# PRUEBA INDEPENDIENTE(para probar solo esta pantalla)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("RetroVault - Carrito")
    root.geometry("1000x650")
    root.configure(bg=BG_DARK)
    root.resizable(False, False)

    # Función externa que calcula el total con las cantidades
    def mi_calculador(items):
        return sum(float(i["producto"].precio) * i["cantidad"] for i in items)

    pantalla = carrito(
        root,
        fn_calcular_total=mi_calculador,
        on_volver=lambda: print("Volver"),
        on_pagar=lambda: print("Pagar")
    )

    demo = [
        {"producto": Producto(1, "Super Mario 64", 19900, 10, "N64"), "cantidad": 1},
        {"producto": Producto(2, "The Legend of Zelda", 45000, 5, "N64"), "cantidad": 2},
        {"producto": Producto(3, "Game Boy Color", 100000, 2, "Consolas"), "cantidad": 1}
    ]

    pantalla.actualizar_carrito(demo)

    root.mainloop()