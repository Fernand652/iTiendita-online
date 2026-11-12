"""Vista cliente para consultar favoritos y suscripciones a reposición."""
import tkinter as tk

try:
    from vistas.estilos import *
except ImportError:
    from estilos import *


class PantallaListaDeseos(tk.Frame):
    def __init__(self, parent, inventario, lista_deseos, usuario, on_volver=None,
                 on_agregar_carro=None):
        super().__init__(parent, bg=BG_DARK)
        self.inventario = inventario
        self.lista_deseos = lista_deseos
        self.usuario = usuario
        self.on_volver = on_volver
        self.on_agregar_carro = on_agregar_carro
        self._crear()

    def _crear(self):
        barra = tk.Frame(self, bg=BG_DARK)
        barra.pack(fill="x", padx=40, pady=20)
        tk.Label(barra, text="RETRO VAULT — Mi lista de deseos", font=FUENTE_LOGO,
                 bg=BG_DARK, fg=GREEN).pack(side="left")
        tk.Button(barra, text="← VOLVER", font=FUENTE_NAV, bg=GRAY_BTN, fg=WHITE,
                  relief="flat", command=lambda: self.on_volver() if self.on_volver else None).pack(side="right")

        cuerpo = tk.Frame(self, bg=BG_DARK)
        cuerpo.pack(fill="both", expand=True, padx=55, pady=(10, 35))
        ids = self.lista_deseos.productos_de(self.usuario)
        productos = [p for p in self.inventario.productos if p.id in ids]
        if not productos:
            tk.Label(cuerpo, text="Aún no tienes productos guardados.", font=FUENTE_TITULO,
                     bg=BG_DARK, fg=GRAY_TEXT).pack(pady=50)
            return
        for producto in productos:
            tarjeta = tk.Frame(cuerpo, bg=DARK_CARD, padx=18, pady=14)
            tarjeta.pack(fill="x", pady=6)
            estado = "Sin stock" if producto.stock <= 0 else f"Stock disponible: {producto.stock}"
            if self.lista_deseos.es_suscriptor(self.usuario, producto.id):
                estado += " · Suscrito a reposición"
            tk.Label(tarjeta, text=producto.nombre, font=FUENTE_NOMBRE, bg=DARK_CARD, fg=WHITE).pack(anchor="w")
            tk.Label(tarjeta, text=f"${producto.precio:,.0f} · {estado}".replace(",", "."),
                     font=FUENTE_BODY, bg=DARK_CARD, fg=GRAY_TEXT).pack(anchor="w", pady=(4, 0))
            if producto.stock > 0 and self.on_agregar_carro:
                tk.Button(tarjeta, text="MOVER AL CARRITO", font=FUENTE_BOTON,
                          bg=GREEN, fg=BLACK, relief="flat",
                          command=lambda p=producto: self._agregar(p)).pack(side="right", padx=4)

    def _agregar(self, producto):
        resultado = self.on_agregar_carro(producto)
        if isinstance(resultado, tuple) and not resultado[0]:
            return
