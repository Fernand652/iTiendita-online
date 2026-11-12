"""
chat_vista.py
panel de chat "consultar al asistente": el cliente escribe preguntas en
lenguaje natural sobre los productos de la tienda y la
api de gemini (ver modelos/api_gemini.py) responde usando el catalogo real,
el hilo que consulta la api nunca toca la ventana. deja la respuesta en una bandeja (queue) y
el hilo principal de tkinter la lee con after().
"""
import os
import queue
import sys
import threading

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

try:
    from modelos.api_gemini import consultar_gemini
except ImportError:
    try:
        from api_gemini import consultar_gemini
    except ImportError:
        consultar_gemini = None


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

        # se guarda el objeto inventario (si llego uno) para leer el
        # catalogo vigente en cada pregunta, no una copia vieja
        self._inventario_objeto = inventario if hasattr(inventario, "productos") else None
        if inventario is None:
            self.inventario = []
        elif hasattr(inventario, "productos"):
            self.inventario = list(inventario.productos)
        else:
            self.inventario = list(inventario)

        # historial de la conversacion en el formato de gemini:
        # [{"role": "user"|"model", "parts": [{"text": ...}]}]
        self.historial = []

        # bandeja de respuestas: el hilo deja el resultado aca y el hilo
        # principal de tk lo lee con after() (patron de los sockets)
        self._cola_respuestas = queue.Queue()
        self._consultando = False
        self._marca_pendiente = None  # posicion del "consultando..."

        self.pack(fill="both", expand=True)
        self._crear_barra_superior()
        self._crear_interfaz()
        self.after(100, self._bombeo_respuestas)

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

        if consultar_gemini is None:
            self._agregar_mensaje(
                "Asistente",
                "El módulo del asistente no está disponible "
                "(falta modelos/api_gemini.py)."
            )
        else:
            self._agregar_mensaje(
                "Asistente",
                "Hola! Puedo ayudarte a consultar sobre nuestros productos. "
                "¿Qué deseas saber?"
            )

        entrada_frame = tk.Frame(cuerpo, bg=BG_DARK)
        entrada_frame.pack(fill="x", pady=(15, 0))

        self.entrada = tk.Entry(
            entrada_frame, font=FUENTE_BODY, bg=DARK_CARD, fg=WHITE,
            insertbackground=WHITE, relief="flat"
        )
        self.entrada.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))
        self.entrada.bind("<Return>", lambda e: self._enviar_mensaje())

        self.btn_enviar = tk.Button(
            entrada_frame, text="ENVIAR", font=FUENTE_BOTON,
            bg=GREEN, fg=BLACK, activebackground=GREEN_HOVER,
            relief="flat", bd=0, cursor="hand2", command=self._enviar_mensaje
        )
        self.btn_enviar.pack(side="right", ipadx=20, ipady=10)

    def _agregar_mensaje(self, remitente, mensaje):
        # retorna la marca (posicion) donde empieza, por si despues hay que
        # reemplazarlo (ver _reemplazar_desde)
        self.chat_area.config(state=tk.NORMAL)
        marca = self.chat_area.index("end-1c")
        self.chat_area.insert(tk.END, f"[{remitente}]: {mensaje}\n\n")
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)
        return marca

    def _reemplazar_desde(self, marca, remitente, mensaje):
        # borra lo que quedo desde la marca y escribe el mensaje real
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.delete(marca, "end-1c")
        self.chat_area.insert(tk.END, f"[{remitente}]: {mensaje}\n\n")
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def _bloquear_entrada(self, bloqueado):
        # bloquea el input mientras se espera la respuesta de gemini
        estado = "disabled" if bloqueado else "normal"
        self.entrada.config(state=estado)
        self.btn_enviar.config(
            state=estado, text="..." if bloqueado else "ENVIAR"
        )

    def _productos_actuales(self):
        # el catalogo vigente al momento de preguntar
        fuente = self._inventario_objeto
        if fuente is not None and hasattr(fuente, "productos"):
            try:
                return list(fuente.productos)
            except Exception:
                return []
        return list(self.inventario)

    def _enviar_mensaje(self):
        pregunta = self.entrada.get().strip()
        if not pregunta or self._consultando:
            return
        if consultar_gemini is None:
            self._agregar_mensaje(
                "Asistente",
                "El módulo del asistente no está disponible "
                "(falta modelos/api_gemini.py)."
            )
            return

        self._agregar_mensaje("Tú", pregunta)
        self.entrada.delete(0, tk.END)
        self._consultando = True
        self._bloquear_entrada(True)
        # el "consultando..." se escribe con marca para reemplazarlo por
        # la respuesta real cuando llegue
        self._marca_pendiente = self._agregar_mensaje(
            "Asistente", "Consultando al asistente..."
        )

        hilo = threading.Thread(
            target=self._consultar_en_hilo, args=(pregunta,), daemon=True
        )
        hilo.start()

    def _consultar_en_hilo(self, pregunta):
        # cuerpo del hilo: llama a gemini. nunca toca la ventana: deja el
        # resultado en la bandeja y el hilo principal de tk lo aplica
        try:
            texto, error = consultar_gemini(
                pregunta, self._productos_actuales(), self.historial
            )
        except Exception as e:  # paracaidas: consultar_gemini nunca lanza
            texto, error = None, f"Error inesperado del asistente: {e}"
        self._cola_respuestas.put((pregunta, texto, error))

    def _bombeo_respuestas(self):
        # vacia la bandeja de respuestas en el hilo principal de tkinter
        try:
            while True:
                pregunta, texto, error = self._cola_respuestas.get_nowait()
                self._mostrar_respuesta(pregunta, texto, error)
        except queue.Empty:
            pass
        except tk.TclError:
            return  # la pantalla ya no existe: se deja de bombear
        try:
            self.after(100, self._bombeo_respuestas)
        except tk.TclError:
            pass

    def _mostrar_respuesta(self, pregunta, texto, error):
        # aplica la respuesta que llego de la api a la ventana
        self._consultando = False
        self._bloquear_entrada(False)
        marca = self._marca_pendiente
        self._marca_pendiente = None

        if error:
            if marca is not None:
                self._reemplazar_desde(marca, "Asistente", f"⚠ {error}")
            else:
                self._agregar_mensaje("Asistente", f"⚠ {error}")
            return

        if marca is not None:
            self._reemplazar_desde(marca, "Asistente", texto)
        else:
            self._agregar_mensaje("Asistente", texto)

        # se guarda la conversacion para que la proxima pregunta tenga
        # contexto (p.ej. "y el mas barato de esos?")
        self.historial.append({"role": "user", "parts": [{"text": pregunta}]})
        self.historial.append({"role": "model", "parts": [{"text": texto}]})
        # solo las ultimas 6 idas y vueltas: el resto se descarta para no
        # hacer crecer el pedido a la api infinitamente
        self.historial = self.historial[-12:]

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
