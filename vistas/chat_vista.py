"""
chat_vista.py
Panel de chat para que el cliente consulte sobre productos en lenguaje natural.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import scrolledtext

try:
    from vistas.estilos import *
except ImportError:
    try:
        from estilos import *
    except ImportError:
        BG_DARK = "#0b0f0b"
        DARK_CARD = "#171b17"
        GREEN = "#00ff66"
        GREEN_HOVER = "#17b84e"
        WHITE = "#ffffff"
        BLACK = "#1a1a1a"
        GRAY_TEXT = "#9a9a9a"
        GRAY_BTN = "#2b2b2b"
        FUENTE_LOGO = ("Arial", 15, "bold")
        FUENTE_TITULO = ("Arial", 20, "bold")
        FUENTE_NAV = ("Arial", 10, "bold")
        FUENTE_BODY = ("Arial", 10)
        FUENTE_BOTON = ("Arial", 11, "bold")


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


class PantallaChat(tk.Frame):
    def __init__(self, parent, inventario=None, on_volver=None, usuario_actual=None,
                 on_cerrar_sesion=None, on_ir_login=None):
        super().__init__(parent, bg=BG_DARK)
        self.parent = parent
        self.on_volver = on_volver
        self.usuario_actual = usuario_actual
        self.on_cerrar_sesion = on_cerrar_sesion
        self.on_ir_login = on_ir_login

        if inventario is None:
            self.inventario = []
        elif hasattr(inventario, "productos"):
            self.inventario = list(inventario.productos)
        else:
            self.inventario = list(inventario)

        self.pack(fill="both", expand=True)
        self._crear_barra_superior()
        self._crear_interfaz()

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
            barra, text="INICIAR SESIÓN" if self.usuario_actual is None else "SALIR", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, padx=15, pady=8, cursor="hand2"
        )
        btn_salir.pack(side="right", padx=(0, 10))
        if self.usuario_actual is None:
            btn_salir.bind("<Button-1>", lambda e: self._ir_login())
        else:
            btn_salir.bind("<Button-1>", lambda e: self._cerrar_sesion())

        nombre = self.usuario_actual or "Invitado"
        tk.Label(
            barra, text=f"👤 {nombre}", font=FUENTE_NAV,
            bg=BG_DARK, fg=GRAY_TEXT, padx=8, pady=8,
        ).pack(side="right", padx=(0, 10))

    def _crear_interfaz(self):
        cuerpo = tk.Frame(self, bg=BG_DARK)
        cuerpo.pack(fill="both", expand=True, padx=40, pady=(0, 25))

        tk.Label(cuerpo, text="CONSULTA DE PRODUCTOS", font=FUENTE_TITULO, bg=BG_DARK, fg=WHITE).pack(anchor="w", pady=(0, 10))
        tk.Label(cuerpo, text="Escribe preguntas en lenguaje natural sobre características, comparaciones, recomendaciones, disponibilidad o rangos de precio.",
                 font=FUENTE_BODY, bg=BG_DARK, fg=GRAY_TEXT).pack(anchor="w", pady=(0, 20))

        chat_frame = tk.Frame(cuerpo, bg=DARK_CARD)
        chat_frame.pack(fill="both", expand=True)

        self.chat_area = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, font=FUENTE_BODY,
            bg=DARK_CARD, fg=WHITE, insertbackground=WHITE,
            relief="flat", bd=0, padx=20, pady=20
        )
        self.chat_area.pack(fill="both", expand=True)
        self.chat_area.config(state=tk.DISABLED)

        self._agregar_mensaje("Asistente", "Hola! Puedo ayudarte a consultar sobre nuestros productos. ¿Qué deseas saber?")

        entrada_frame = tk.Frame(cuerpo, bg=BG_DARK)
        entrada_frame.pack(fill="x", pady=(15, 0))

        self.entrada = tk.Entry(
            entrada_frame, font=FUENTE_BODY, bg=DARK_CARD, fg=WHITE,
            insertbackground=WHITE, relief="flat"
        )
        self.entrada.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))
        self.entrada.bind("<Return>", lambda e: self._enviar_mensaje())

        btn_enviar = tk.Button(
            entrada_frame, text="ENVIAR", font=FUENTE_BOTON,
            bg=GREEN, fg=BLACK, activebackground=GREEN_HOVER,
            relief="flat", bd=0, cursor="hand2", command=self._enviar_mensaje
        )
        btn_enviar.pack(side="right", ipadx=20, ipady=10)

    def _agregar_mensaje(self, remitente, mensaje):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, f"[{remitente}]: {mensaje}\n\n")
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def _enviar_mensaje(self):
        pregunta = self.entrada.get().strip()
        if not pregunta:
            return
        self._agregar_mensaje("Tú", pregunta)
        self.entrada.delete(0, tk.END)
        self._agregar_mensaje("Asistente", "Procesando consulta...")

    def volver(self):
        if self.on_volver:
            self.on_volver()
        else:
            _toast(self, "Volver no disponible", tipo="info")

    def _cerrar_sesion(self):
        if self.on_cerrar_sesion:
            self.on_cerrar_sesion()
        else:
            _toast(self, "Cerrar sesión no disponible", tipo="info")

    def _ir_login(self):
        if self.on_ir_login:
            self.on_ir_login()
        else:
            _toast(self, "Iniciar sesión no disponible", tipo="info")
