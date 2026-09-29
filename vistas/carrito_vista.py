"""
carrito.py
Pantalla de Carrito de Compras de RetroVault.
Implementa Item 4: Cálculo de subtotal, IVA (19%), total y comprobante de venta.
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
        from vistas.estilos import *

try:
    from modelos.producto import Producto
except ImportError:
    try:
        from producto import Producto
    except ImportError:
        try:
            from vistas.producto import Producto
        except ImportError:
            Producto = None

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

        # Variables Item 4: Totales e IVA
        self.subtotal_actual = 0.0
        self.iva_actual = 0.0
        self.total_actual = 0.0

        self._crear_barra_superior()
        self._crear_interfaz()

    # BARRA SUPERIOR (Respeta la navegación existente del grupo)
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

        # Columna Izquierda: Items del carrito (Manejado por Requisito 1)
        self.col_izquierda = tk.Frame(columnas, bg=BG_DARK)
        self.col_izquierda.pack(side="left", fill="both", expand=True, padx=(0, 25))

        # Columna Derecha: Resumen (Item 4: Desglose claro y separado)
        resumen = tk.Frame(columnas, bg=DARK_CARD, width=320, padx=25, pady=25)
        resumen.pack(side="right", fill="y")
        resumen.pack_propagate(False)

        tk.Label(resumen, text="RESUMEN", font=FUENTE_TITULO, bg=DARK_CARD, fg=WHITE).pack(anchor="w", pady=(0, 15))
        tk.Frame(resumen, bg=GRAY_BTN, height=1).pack(fill="x", pady=10)

        # 1. Desglose Subtotal
        fila_subtotal = tk.Frame(resumen, bg=DARK_CARD)
        fila_subtotal.pack(fill="x", pady=4)
        tk.Label(fila_subtotal, text="Subtotal", font=FUENTE_BODY, bg=DARK_CARD, fg=GRAY_TEXT).pack(side="left")
        self.lbl_subtotal = tk.Label(fila_subtotal, text="$0,00", font=FUENTE_BODY, bg=DARK_CARD, fg=WHITE)
        self.lbl_subtotal.pack(side="right")

        # 2. Desglose IVA 19%
        fila_iva = tk.Frame(resumen, bg=DARK_CARD)
        fila_iva.pack(fill="x", pady=4)
        tk.Label(fila_iva, text="IVA (19%)", font=FUENTE_BODY, bg=DARK_CARD, fg=GRAY_TEXT).pack(side="left")
        self.lbl_iva = tk.Label(fila_iva, text="$0,00", font=FUENTE_BODY, bg=DARK_CARD, fg=WHITE)
        self.lbl_iva.pack(side="right")

        tk.Frame(resumen, bg=GRAY_BTN, height=1).pack(fill="x", pady=12)

        # 3. Total Final
        fila_total = tk.Frame(resumen, bg=DARK_CARD)
        fila_total.pack(fill="x", pady=(0, 20))
        tk.Label(fila_total, text="TOTAL", font=FUENTE_PRECIO, bg=DARK_CARD, fg=WHITE).pack(side="left")
        self.lbl_total = tk.Label(fila_total, text="$0,00", font=FUENTE_HERO, bg=DARK_CARD, fg=GREEN)
        self.lbl_total.pack(side="right")

        # Botón Pagar / Confirmar venta
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
        self.lbl_mensaje.config(text=msg)
        _toast(self, msg, tipo=tipo)

    def _limpiar_mensaje(self):
        self.lbl_mensaje.config(text="")

    # METODOS DE GESTIÓN DE PRODUCTOS (Requisito 1: intactos)
    def mostrar_productos(self, items):
        self.lista_actual = []
        for i in items:
            if isinstance(i, dict):
                self.lista_actual.append(i)
            else:
                self.lista_actual.append({"producto": i, "cantidad": 1})

        if not self.lista_actual:
            tk.Label(
                self.col_izquierda, text="Tu carrito está vacío",
                font=FUENTE_TITULO, bg=BG_DARK, fg=GRAY_TEXT
            ).pack(pady=40)
            self._actualizar_totales()
            self._limpiar_mensaje()
            return

        self._limpiar_mensaje()

        for elemento in self.lista_actual:
            prod = elemento["producto"]
            cant = elemento["cantidad"]

            tarjeta = tk.Frame(self.col_izquierda, bg=DARK_CARD, padx=15, pady=15)
            tarjeta.pack(fill="x", pady=6)

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
                    lbl_thumb = tk.Label(tarjeta, image=thumb, bg=DARK_CARD)
                    lbl_thumb.image = thumb
                    lbl_thumb.pack(side="left", padx=(0, 12))

            info = tk.Frame(tarjeta, bg=DARK_CARD)
            info.pack(side="left", fill="both", expand=True)

            tk.Label(info, text=str(prod.categoria).upper(), font=FUENTE_CATEGORIA, bg=DARK_CARD, fg=GREEN).pack(anchor="w")
            tk.Label(info, text=prod.nombre, font=FUENTE_NOMBRE, bg=DARK_CARD, fg=WHITE).pack(anchor="w", pady=(2, 5))
            tk.Label(info, text=f"${float(prod.precio):,.0f} c/u", font=FUENTE_PRECIO, bg=DARK_CARD, fg=GRAY_TEXT).pack(anchor="w")

            controles = tk.Frame(tarjeta, bg=DARK_CARD)
            controles.pack(side="right")

            btn_menos = tk.Label(controles, text="-", font=FUENTE_BOTON, bg=GRAY_BTN, fg=WHITE, width=2, cursor="hand2")
            btn_menos.pack(side="left", padx=2)
            btn_menos.bind("<Button-1>", lambda e, el=elemento: self._cambiar_cantidad(el, -1))

            lbl_cant = tk.Label(controles, text=str(cant), font=FUENTE_BODY, bg=DARK_CARD, fg=WHITE, width=3)
            lbl_cant.pack(side="left", padx=4)

            btn_mas = tk.Label(controles, text="+", font=FUENTE_BOTON, bg=GRAY_BTN, fg=WHITE, width=2, cursor="hand2")
            btn_mas.pack(side="left", padx=2)
            btn_mas.bind("<Button-1>", lambda e, el=elemento: self._cambiar_cantidad(el, 1))

            btn_del = tk.Label(controles, text="X", font=FUENTE_BOTON, bg=DARK_CARD, fg=RED_BADGE, cursor="hand2", padx=8)
            btn_del.pack(side="left", padx=(8, 0))
            btn_del.bind("<Button-1>", lambda e, el=elemento: self._eliminar_producto(el))

        self._actualizar_totales()

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

    # LÓGICA ITEM 4: SUB-TOTAL, IVA (19%) Y TOTAL
    def _actualizar_totales(self):
        if not self.lista_actual:
            self.subtotal_actual = 0.0
            self.iva_actual = 0.0
            self.total_actual = 0.0
        else:
            # Subtotal: Suma de (precio * cantidad) de cada item
            self.subtotal_actual = sum(float(i["producto"].precio) * i["cantidad"] for i in self.lista_actual)
            # IVA: 19% sobre el subtotal
            self.iva_actual = self.subtotal_actual * 0.19
            # Total: Subtotal + IVA
            self.total_actual = self.subtotal_actual + self.iva_actual

        # Formato numérico estándar chileno
        sub_str = f"{self.subtotal_actual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        iva_str = f"{self.iva_actual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        tot_str = f"{self.total_actual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        self.lbl_subtotal.config(text=f"${sub_str}")
        self.lbl_iva.config(text=f"${iva_str}")
        self.lbl_total.config(text=f"${tot_str}")

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

    # SUBFUNCIONALIDAD ITEM 4: COMPROBANTE DE COMPRA
    def _generar_comprobante(self):
        modal = tk.Toplevel(self)
        modal.title("Comprobante de Venta")
        modal.geometry("450x520")
        modal.configure(bg=DARK_CARD)
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()

        tk.Label(modal, text="COMPROBANTE DE COMPRA", font=FUENTE_TITULO, bg=DARK_CARD, fg=GREEN).pack(pady=(20, 5))
        cliente = self.usuario_actual or "Cliente General"
        tk.Label(modal, text=f"Cliente: {cliente}", font=FUENTE_BODY, bg=DARK_CARD, fg=WHITE).pack(pady=(0, 10))

        tk.Frame(modal, bg=GRAY_BTN, height=1).pack(fill="x", padx=20, pady=5)

        # Detalle de artículos comprados
        frame_items = tk.Frame(modal, bg=DARK_CARD)
        frame_items.pack(fill="both", expand=True, padx=25, pady=10)

        for el in self.lista_actual:
            p = el["producto"]
            c = el["cantidad"]
            sub = float(p.precio) * c
            sub_fmt = f"{sub:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            fila = tk.Frame(frame_items, bg=DARK_CARD)
            fila.pack(fill="x", pady=2)
            tk.Label(fila, text=f"{p.nombre} x{c}", font=FUENTE_BODY, bg=DARK_CARD, fg=WHITE).pack(side="left")
            tk.Label(fila, text=f"${sub_fmt}", font=FUENTE_BODY, bg=DARK_CARD, fg=GRAY_TEXT).pack(side="right")

        tk.Frame(modal, bg=GRAY_BTN, height=1).pack(fill="x", padx=20, pady=5)

        # Totales en el comprobante
        frame_totales = tk.Frame(modal, bg=DARK_CARD)
        frame_totales.pack(fill="x", padx=25, pady=5)

        sub_str = f"{self.subtotal_actual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        iva_str = f"{self.iva_actual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        tot_str = f"{self.total_actual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        def add_linea(label, valor, color=WHITE):
            f = tk.Frame(frame_totales, bg=DARK_CARD)
            f.pack(fill="x", pady=2)
            tk.Label(f, text=label, font=FUENTE_BODY, bg=DARK_CARD, fg=GRAY_TEXT).pack(side="left")
            tk.Label(f, text=valor, font=FUENTE_BODY, bg=DARK_CARD, fg=color).pack(side="right")

        add_linea("Subtotal:", f"${sub_str}")
        add_linea("IVA (19%):", f"${iva_str}")
        add_linea("TOTAL PAGADO:", f"${tot_str}", color=GREEN)

        def confirmar():
            modal.destroy()
            if self.on_pagar:
                # Avisa al flujo general para que el ADMIN o Sockets reciban la venta
                self.on_pagar()

        tk.Button(
            modal, text="ACEPTAR", font=FUENTE_BOTON,
            bg=GREEN, fg=BLACK, activebackground=GREEN_HOVER,
            relief="flat", bd=0, cursor="hand2", command=confirmar
        ).pack(fill="x", padx=30, pady=20, ipady=8)

    def pagar(self):
        if not self.lista_actual:
            self._mostrar_mensaje("Tu carrito está vacío, agrega productos primero", tipo="error")
            return

        self._limpiar_mensaje()
        self._generar_comprobante()


# PRUEBA AISLADA: Ejecuta directamente con el caso textual de la pauta docente
if __name__ == "__main__":
    root = tk.Tk()
    root.title("RetroVault - Carrito")
    root.geometry("1000x650")
    root.configure(bg=BG_DARK)
    root.resizable(False, False)

    pantalla = carrito(
        root,
        usuario_actual="Cliente Demo",
        on_volver=lambda: print("Volver"),
        on_pagar=lambda: print("Venta notificada al ADMIN")
    )

    # Caso exacto del enunciado docente:
    demo = [
        {"producto": Producto(1, "Laptop Gamer", 999990, 10, "Laptops"), "cantidad": 1},
        {"producto": Producto(2, "Teclado Mecanico", 49990, 5, "Perifericos"), "cantidad": 2}
    ]

    pantalla.actualizar_carrito(demo)

    root.mainloop()