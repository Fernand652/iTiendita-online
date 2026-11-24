"""
chat_vista.py
panel de chat "consultar al asistente": el cliente escribe preguntas en
lenguaje natural sobre los productos de la tienda y el servidor del admin
(llamando a la api de gemini) responde usando el catalogo real.
el hilo que consulta la api nunca toca la ventana. deja la respuesta en una bandeja (queue) y
el hilo principal de tkinter la lee con after().
"""
import os
import queue
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import scrolledtext, ttk

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
                 on_cerrar_sesion=None, on_ir_login=None, conexion=None,
                 consultar_local=None, historial=None):
        super().__init__(parent, bg=BG_DARK)
        self.parent = parent
        self.on_volver = on_volver
        self.usuario_actual = usuario_actual
        self.on_cerrar_sesion = on_cerrar_sesion
        self.on_ir_login = on_ir_login
        self.conexion = conexion
        self._consultar_local = consultar_local

        self._inventario_objeto = inventario if hasattr(inventario, "productos") else None
        if inventario is None:
            self.inventario = []
        elif hasattr(inventario, "productos"):
            self.inventario = list(inventario.productos)
        else:
            self.inventario = list(inventario)

        # historial compartido por la app para mantener el contexto
        self.historial = historial if historial is not None else []

        self._cola_respuestas = queue.Queue()
        self._consultando = False
        self._marca_pendiente = None

        self.pack(fill="both", expand=True)
        self._crear_barra_superior()
        self._crear_interfaz()
        self.after(100, self._bombeo_respuestas)

    def _crear_barra_superior(self):
        barra = tk.Frame(self, bg=BG_DARK)
        barra.pack(fill="x", padx=24, pady=(14, 10))

        tk.Label(barra, text="RETRO VAULT", font=FUENTE_LOGO, bg=BG_DARK, fg=GREEN).pack(side="left", pady=6)

        bloque_derecho = tk.Frame(barra, bg=BG_DARK)
        bloque_derecho.pack(side="right", fill="y")

        nombre = self.usuario_actual or "Invitado"
        tk.Label(
            bloque_derecho, text=nombre, font=FUENTE_NAV,
            bg=BG_DARK, fg=GRAY_TEXT, padx=8, pady=8,
        ).pack(side="left", padx=(0, 18), pady=6)

        texto_sesion = "INICIAR SESIÓN" if self.usuario_actual is None else "SALIR"
        # jerarquia: iniciar sesion es accion principal
        if self.usuario_actual is None:
            color_fondo_sesion = GREEN
            color_texto_sesion = BLACK
        else:
            color_fondo_sesion = GRAY_BTN
            color_texto_sesion = WHITE
        btn_sesion = tk.Label(
            bloque_derecho, text=texto_sesion, font=FUENTE_NAV,
            bg=color_fondo_sesion, fg=color_texto_sesion,
            padx=14, pady=8, cursor="hand2", relief="flat", bd=0,
        )
        btn_sesion.pack(side="left", padx=(8, 0), pady=6)
        if self.usuario_actual is None:
            btn_sesion.bind("<Button-1>", lambda e: self._ir_login())
        else:
            btn_sesion.bind("<Button-1>", lambda e: self._cerrar_sesion())

        btn_volver = tk.Label(
            bloque_derecho, text="VOLVER", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, padx=14, pady=8, cursor="hand2",
            relief="flat", bd=0,
        )
        btn_volver.pack(side="left", padx=(8, 0), pady=6)
        btn_volver.bind("<Button-1>", lambda e: self.volver())

    def _crear_interfaz(self):
        cuerpo = tk.Frame(self, bg=BG_DARK)
        cuerpo.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # area inferior: entrada de texto y un solo boton (pack bottom para no recortarse)
        marco_entrada = tk.Frame(cuerpo, bg=BG_DARK)
        marco_entrada.pack(side="bottom", fill="x", pady=(12, 8))

        self.entrada = tk.Entry(
            marco_entrada, font=FUENTE_BODY, bg=DARK_CARD, fg=WHITE,
            insertbackground=WHITE, relief="flat"
        )
        self.entrada.pack(side="left", fill="x", expand=True, ipady=12, padx=(0, 12))
        self.entrada.bind("<Return>", lambda e: self._enviar_mensaje())

        self.btn_enviar = tk.Button(
            marco_entrada, text="ENVIAR", font=FUENTE_BOTON,
            bg=GREEN, fg=BLACK, activebackground=GREEN_HOVER,
            relief="flat", bd=0, cursor="hand2",
            padx=18, pady=10, command=self._enviar_mensaje
        )
        self.btn_enviar.pack(side="right", ipadx=6, ipady=4)

        # zona central: titulo, descripcion y pestañas
        zona_central = tk.Frame(cuerpo, bg=BG_DARK)
        zona_central.pack(side="top", fill="both", expand=True)

        tk.Label(zona_central, text="CONSULTA DE PRODUCTOS", font=FUENTE_TITULO, bg=BG_DARK, fg=WHITE).pack(anchor="w", pady=(0, 8))
        tk.Label(zona_central, text="Escribe preguntas en lenguaje natural sobre características, comparaciones, recomendaciones, disponibilidad o rangos de precio.",
                 font=FUENTE_BODY, bg=BG_DARK, fg=GRAY_TEXT, justify="left", wraplength=900).pack(anchor="w", pady=(0, 14))

        # pestañas: conversacion y historial (se adaptan al tamaño)
        cuaderno = ttk.Notebook(zona_central)
        cuaderno.pack(fill="both", expand=True)
        self._cuaderno = cuaderno

        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure("TNotebook", background=BG_DARK, borderwidth=0)
        estilo.configure("TNotebook.Tab", background=GRAY_BTN,
                         foreground=WHITE, font=FUENTE_NAV, padding=(16, 8))
        estilo.map("TNotebook.Tab",
                   background=[("selected", GREEN), ("active", "#1f3a28")],
                   foreground=[("selected", BLACK), ("active", WHITE)])
        try:
            cuaderno.select(0)
        except Exception:
            pass

        # area superior: historial de mensajes (bonita y limpia)
        tab_chat = tk.Frame(cuaderno, bg=DARK_CARD)
        cuaderno.add(tab_chat, text="CONVERSACIÓN")

        marco_chat = tk.Frame(tab_chat, bg=DARK_CARD)
        marco_chat.pack(fill="both", expand=True)

        self.chat_area = scrolledtext.ScrolledText(
            marco_chat, wrap=tk.WORD, font=FUENTE_BODY,
            bg=DARK_CARD, fg=WHITE, insertbackground=WHITE,
            relief="flat", bd=0, padx=28, pady=22
        )
        self.chat_area.pack(fill="both", expand=True)
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.tag_configure("etiqueta_usuario", foreground=GREEN, font=FUENTE_NAV)
        self.chat_area.tag_configure("etiqueta_asistente", foreground=WHITE, font=FUENTE_NAV)
        self.chat_area.tag_configure("cuerpo_usuario", foreground=WHITE, font=FUENTE_BODY, spacing1=6, spacing3=18, lmargin1=10, lmargin2=10)
        self.chat_area.tag_configure("cuerpo_asistente", foreground=WHITE, font=FUENTE_BODY, spacing1=6, spacing3=18, lmargin1=10, lmargin2=10)
        self.chat_area.tag_configure("cuerpo_error", foreground=GRAY_TEXT, font=FUENTE_BODY, spacing1=6, spacing3=18, lmargin1=10, lmargin2=10)

        # pestaña historial
        tab_historial = tk.Frame(cuaderno, bg=DARK_CARD)
        cuaderno.add(tab_historial, text="HISTORIAL")
        self._tab_historial = tab_historial

        tk.Label(
            tab_historial,
            text="Últimos mensajes de la sesión. El asistente los usa para entender seguidas.",
            font=FUENTE_BODY, bg=DARK_CARD, fg=GRAY_TEXT,
            anchor="w", justify="left",
        ).pack(fill="x", padx=20, pady=(16, 6))

        self.historial_area = scrolledtext.ScrolledText(
            tab_historial, wrap=tk.WORD, font=FUENTE_BODY,
            bg=DARK_CARD, fg=WHITE, insertbackground=WHITE,
            relief="flat", bd=0, padx=20, pady=10
        )
        self.historial_area.pack(fill="both", expand=True)
        self.historial_area.config(state=tk.DISABLED)

        self._agregar_mensaje(
            "Asistente",
            "Hola! Puedo ayudarte a consultar sobre nuestros productos. "
            "Que deseas saber?"
        )
        self._refrescar_historial()

    def _agregar_mensaje(self, remitente, mensaje):
        self.chat_area.config(state=tk.NORMAL)
        marca = self.chat_area.index("end-1c")
        if remitente == "Tú":
            self.chat_area.insert(tk.END, f"{remitente}\n", "etiqueta_usuario")
        else:
            self.chat_area.insert(tk.END, f"{remitente}\n", "etiqueta_asistente")
        es_error = isinstance(mensaje, str) and mensaje.lower().startswith("error:")
        etiqueta_cuerpo = "cuerpo_error" if es_error else ("cuerpo_usuario" if remitente == "Tú" else "cuerpo_asistente")
        self.chat_area.insert(tk.END, f"{mensaje}\n\n", etiqueta_cuerpo)
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)
        return marca

    def _reemplazar_desde(self, marca, remitente, mensaje):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.delete(marca, "end-1c")
        if remitente == "Tú":
            self.chat_area.insert(tk.END, f"{remitente}\n", "etiqueta_usuario")
        else:
            self.chat_area.insert(tk.END, f"{remitente}\n", "etiqueta_asistente")
        es_error = isinstance(mensaje, str) and mensaje.lower().startswith("error:")
        etiqueta_cuerpo = "cuerpo_error" if es_error else ("cuerpo_usuario" if remitente == "Tú" else "cuerpo_asistente")
        self.chat_area.insert(tk.END, f"{mensaje}\n\n", etiqueta_cuerpo)
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def _refrescar_historial(self):
        try:
            self.historial_area.config(state=tk.NORMAL)
            self.historial_area.delete("1.0", tk.END)
            if not self.historial:
                self.historial_area.insert(
                    tk.END,
                    "Todavía no hay mensajes. Lo que preguntes y te responda "
                    "aparecerá acá para dar contexto a la próxima consulta.\n"
                )
            else:
                nombres = {"user": "Tú", "model": "Asistente"}
                for numero, turno in enumerate(self.historial, 1):
                    texto = "".join(p.get("text", "") for p in turno.get("parts", []))
                    remitente = nombres.get(turno.get("role"), "Asistente")
                    self.historial_area.insert(tk.END, f"{numero:02d}. [{remitente}] {texto}\n\n")
            self.historial_area.config(state=tk.DISABLED)
            self.historial_area.see(tk.END)
        except tk.TclError:
            pass

    def _bloquear_entrada(self, bloqueado):
        estado = "disabled" if bloqueado else "normal"
        self.entrada.config(state=estado)
        self.btn_enviar.config(state=estado, text="..." if bloqueado else "ENVIAR")

    def _productos_actuales(self):
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

        self._agregar_mensaje("Tú", pregunta)
        self.entrada.delete(0, tk.END)
        self._consultando = True
        self._bloquear_entrada(True)
        self._marca_pendiente = self._agregar_mensaje("Asistente", "Consultando al asistente...")

        hilo = threading.Thread(target=self._consultar_en_hilo, args=(pregunta,), daemon=True)
        hilo.start()

    def _consultar_en_hilo(self, pregunta):
        try:
            if (self.conexion is not None and self.conexion.conectado
                    and self.conexion.preguntar(pregunta, self.historial)):
                return
            if self._consultar_local is not None:
                texto, error = self._consultar_local(pregunta, self._productos_actuales(), self.historial)
            else:
                texto, error = None, "El asistente requiere conexion con el ADMIN."
        except Exception as e:
            texto, error = None, f"Error inesperado del asistente: {e}"
        self._cola_respuestas.put((pregunta, texto, error))

    def recibir_respuesta(self, mensaje):
        self._cola_respuestas.put((mensaje.get("pregunta", ""), mensaje.get("texto"), mensaje.get("error")))

    def _bombeo_respuestas(self):
        try:
            while True:
                pregunta, texto, error = self._cola_respuestas.get_nowait()
                self._mostrar_respuesta(pregunta, texto, error)
        except queue.Empty:
            pass
        except tk.TclError:
            return
        try:
            self.after(100, self._bombeo_respuestas)
        except tk.TclError:
            pass

    def _mostrar_respuesta(self, pregunta, texto, error):
        self._consultando = False
        self._bloquear_entrada(False)
        marca = self._marca_pendiente
        self._marca_pendiente = None

        if error:
            if marca is not None:
                self._reemplazar_desde(marca, "Asistente", f"error: {error}")
            else:
                self._agregar_mensaje("Asistente", f"error: {error}")
            return

        if marca is not None:
            self._reemplazar_desde(marca, "Asistente", texto)
        else:
            self._agregar_mensaje("Asistente", texto)

        self.historial.append({"role": "user", "parts": [{"text": pregunta}]})
        self.historial.append({"role": "model", "parts": [{"text": texto}]})
        self.historial = self.historial[-12:]
        self._refrescar_historial()

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
