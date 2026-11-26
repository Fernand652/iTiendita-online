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
from tkinter import scrolledtext

try:
    from vistas.estilos import *
except ImportError:
    try:
        from estilos import *
    except ImportError:
        FUENTE_LOGO = ("Arial", 15, "bold")
        FUENTE_TITULO = ("Arial", 20, "bold")
        FUENTE_NAV = ("Arial", 10, "bold")
        FUENTE_BODY = ("Arial", 10)
        FUENTE_BOTON = ("Arial", 11, "bold")

# paleta sobria de esta pantalla: esmeralda apagado sobre gris carbon
FONDO_CARBON = "#141815"
FONDO_PANEL = "#1b211d"
GRIS_BOTON = "#2a322c"
VERDE_SOBRIO = "#205c3f"
VERDE_SUAVE = "#2b7a52"
VERDE_LOGO = "#4aa677"
TEXTO_CLARO = "#eef3ef"
TEXTO_SUAVE = "#b4beb6"


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


def _interpolar_color(inicio, fin, factor):
    """Mezcla dos colores hexadecimales sin usar librerias externas."""
    inicio = inicio.lstrip("#")
    fin = fin.lstrip("#")
    componentes = []
    for indice in (0, 2, 4):
        valor_inicio = int(inicio[indice:indice + 2], 16)
        valor_fin = int(fin[indice:indice + 2], 16)
        componentes.append(int(round(valor_inicio + (valor_fin - valor_inicio) * factor)))
    return "#{:02x}{:02x}{:02x}".format(*componentes)


def _crear_degradado(parent):
    """Difuminado suave con franjas de Canvas puro, sin borde."""
    lienzo = tk.Canvas(parent, bg=FONDO_CARBON, highlightthickness=0, bd=0)
    lienzo.place(x=0, y=0, relwidth=1, relheight=1)
    color_esmeralda_suave = _interpolar_color(FONDO_CARBON, VERDE_SOBRIO, 0.20)

    def _dibujar(evento=None):
        ancho = max(lienzo.winfo_width(), 1)
        alto = max(lienzo.winfo_height(), 1)
        lienzo.delete("franja")
        paso = 4
        for posicion in range(0, ancho, paso):
            centro = (posicion + paso / 2) / ancho
            intensidad = max(0.0, 1.0 - abs(centro - 0.5) * 2)
            color = _interpolar_color(FONDO_CARBON, color_esmeralda_suave, intensidad)
            lienzo.create_rectangle(
                posicion, 0, posicion + paso, alto,
                fill=color, outline="", tags="franja",
            )

    lienzo.bind("<Configure>", _dibujar)
    lienzo.after_idle(_dibujar)
    return lienzo


class PantallaChat(tk.Frame):
    def __init__(self, parent, inventario=None, on_volver=None, usuario_actual=None,
                 on_cerrar_sesion=None, on_ir_login=None, conexion=None,
                 consultar_local=None, historial=None, on_agregar_carro=None):
        super().__init__(parent, bg=FONDO_CARBON)
        self.parent = parent
        self.on_volver = on_volver
        self.usuario_actual = usuario_actual
        self.on_cerrar_sesion = on_cerrar_sesion
        self.on_ir_login = on_ir_login
        self.conexion = conexion
        self._consultar_local = consultar_local
        self.on_agregar_carro = on_agregar_carro

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
        barra = tk.Frame(self, bg=FONDO_CARBON)
        barra.pack(fill="x", padx=24, pady=(14, 10))
        _crear_degradado(barra)

        # los extremos crecen por igual para dejar el nombre de usuario centrado
        barra.columnconfigure(0, weight=1, uniform="lateral")
        barra.columnconfigure(2, weight=1, uniform="lateral")

        izquierda = tk.Frame(barra, bg=FONDO_CARBON)
        izquierda.grid(row=0, column=0, sticky="w")

        self.btn_conversacion = tk.Button(
            izquierda, text="CONVERSACIÓN", font=FUENTE_NAV,
            bg=VERDE_SOBRIO, fg=TEXTO_CLARO, activebackground=VERDE_SUAVE,
            activeforeground=TEXTO_CLARO, padx=14, pady=8,
            relief="flat", bd=0, highlightthickness=0,
            cursor="hand2", command=lambda: self._mostrar_vista("conversacion"),
        )
        self.btn_conversacion.pack(side="left", padx=(0, 8), pady=6)

        self.btn_historial = tk.Button(
            izquierda, text="HISTORIAL", font=FUENTE_NAV,
            bg=GRIS_BOTON, fg=TEXTO_CLARO, activebackground=VERDE_SUAVE,
            activeforeground=TEXTO_CLARO, padx=14, pady=8,
            relief="flat", bd=0, highlightthickness=0,
            cursor="hand2", command=lambda: self._mostrar_vista("historial"),
        )
        self.btn_historial.pack(side="left", pady=6)

        nombre = self.usuario_actual or "Invitado"
        centro = tk.Frame(barra, bg=FONDO_CARBON)
        centro.grid(row=0, column=1)
        tk.Label(
            centro, text=nombre, font=FUENTE_NAV,
            bg=FONDO_CARBON, fg=TEXTO_SUAVE, padx=14, pady=8,
            relief="flat", bd=0,
        ).pack(side="left", pady=6)

        derecha = tk.Frame(barra, bg=FONDO_CARBON)
        derecha.grid(row=0, column=2, sticky="e")

        texto_sesion = "INICIAR SESIÓN" if self.usuario_actual is None else "SALIR"
        # jerarquia: iniciar sesion es accion principal
        if self.usuario_actual is None:
            color_fondo_sesion = VERDE_SOBRIO
            accion_sesion = self._ir_login
        else:
            color_fondo_sesion = GRIS_BOTON
            accion_sesion = self._cerrar_sesion

        self.btn_sesion = tk.Button(
            derecha, text=texto_sesion, font=FUENTE_NAV,
            bg=color_fondo_sesion, fg=TEXTO_CLARO,
            activebackground=VERDE_SUAVE, activeforeground=TEXTO_CLARO,
            padx=14, pady=8, relief="flat", bd=0,
            highlightthickness=0, cursor="hand2", command=accion_sesion,
        )
        self.btn_sesion.pack(side="left", padx=(0, 8), pady=6)

        self.btn_volver = tk.Button(
            derecha, text="VOLVER", font=FUENTE_NAV,
            bg=GRIS_BOTON, fg=TEXTO_CLARO, activebackground=VERDE_SUAVE,
            activeforeground=TEXTO_CLARO, padx=14, pady=8,
            relief="flat", bd=0, highlightthickness=0,
            cursor="hand2", command=self.volver,
        )
        self.btn_volver.pack(side="left", pady=6)

        tk.Label(
            derecha, text="RETRO VAULT", font=FUENTE_LOGO,
            bg=FONDO_CARBON, fg=VERDE_LOGO,
        ).pack(side="right", padx=(24, 20), pady=6)

    def _crear_interfaz(self):
        cuerpo = tk.Frame(self, bg=FONDO_CARBON)
        cuerpo.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # area inferior: entrada de texto y un solo boton (pack bottom para no recortarse)
        marco_entrada = tk.Frame(cuerpo, bg=FONDO_CARBON)
        marco_entrada.pack(side="bottom", fill="x", pady=(12, 8))

        self.entrada = tk.Entry(
            marco_entrada, font=FUENTE_BODY, bg=FONDO_PANEL, fg=TEXTO_CLARO,
            insertbackground=TEXTO_CLARO, relief="flat"
        )
        self.entrada.pack(side="left", fill="x", expand=True, ipady=12, padx=(0, 12))
        self.entrada.bind("<Return>", lambda e: self._enviar_mensaje())

        self.btn_enviar = tk.Button(
            marco_entrada, text="ENVIAR", font=FUENTE_BOTON,
            bg=VERDE_SOBRIO, fg=TEXTO_CLARO, activebackground=VERDE_SUAVE,
            relief="flat", bd=0, cursor="hand2",
            padx=18, pady=10, command=self._enviar_mensaje
        )
        self.btn_enviar.pack(side="right", ipadx=6, ipady=4)

        # zona central: titulo, descripcion y vistas
        zona_central = tk.Frame(cuerpo, bg=FONDO_CARBON)
        zona_central.pack(side="top", fill="both", expand=True)

        tk.Label(zona_central, text="CONSULTA DE PRODUCTOS", font=FUENTE_TITULO, bg=FONDO_CARBON, fg=TEXTO_CLARO).pack(anchor="w", pady=(0, 8))
        tk.Label(zona_central, text="Escribe preguntas en lenguaje natural sobre características, comparaciones, recomendaciones, disponibilidad o rangos de precio.",
                 font=FUENTE_BODY, bg=FONDO_CARBON, fg=TEXTO_SUAVE, justify="left", wraplength=900).pack(anchor="w", pady=(0, 14))

        # vistas: conversacion e historial, controladas desde la barra superior
        marco_vistas = tk.Frame(zona_central, bg=FONDO_CARBON)
        marco_vistas.pack(fill="both", expand=True)

        # area de conversacion (bonita y limpia)
        tab_chat = tk.Frame(marco_vistas, bg=FONDO_PANEL)
        tab_chat.pack(fill="both", expand=True)
        self._tab_conversacion = tab_chat

        marco_chat = tk.Frame(tab_chat, bg=FONDO_PANEL)
        marco_chat.pack(fill="both", expand=True)

        self.chat_area = scrolledtext.ScrolledText(
            marco_chat, wrap=tk.WORD, font=FUENTE_BODY,
            bg=FONDO_PANEL, fg=TEXTO_CLARO, insertbackground=TEXTO_CLARO,
            relief="flat", bd=0, padx=32, pady=24,
            highlightthickness=1, highlightbackground=GRIS_BOTON,
            highlightcolor=VERDE_SOBRIO, selectbackground=VERDE_SUAVE,
            selectforeground=TEXTO_CLARO,
        )
        self.chat_area.pack(fill="both", expand=True, padx=(6, 6), pady=(6, 6))
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.tag_configure(
            "etiqueta_usuario", foreground=VERDE_SOBRIO, font=FUENTE_NAV,
            spacing1=10, spacing2=2, spacing3=2,
        )
        self.chat_area.tag_configure(
            "etiqueta_asistente", foreground=TEXTO_CLARO, font=FUENTE_NAV,
            spacing1=10, spacing2=2, spacing3=2,
        )
        self.chat_area.tag_configure(
            "cuerpo_usuario", foreground=TEXTO_CLARO, font=FUENTE_BODY,
            spacing1=2, spacing2=4, spacing3=18, lmargin1=16, lmargin2=16,
        )
        self.chat_area.tag_configure(
            "cuerpo_asistente", foreground=TEXTO_CLARO, font=FUENTE_BODY,
            spacing1=2, spacing2=4, spacing3=18, lmargin1=16, lmargin2=16,
        )
        self.chat_area.tag_configure(
            "cuerpo_error", foreground=TEXTO_SUAVE, font=FUENTE_BODY,
            spacing1=2, spacing2=4, spacing3=18, lmargin1=16, lmargin2=16,
        )

        # vista de historial (oculta hasta que se pida desde la barra superior)
        tab_historial = tk.Frame(marco_vistas, bg=FONDO_PANEL)
        self._tab_historial = tab_historial

        tk.Label(
            tab_historial,
            text="Últimos mensajes de la sesión. El asistente los usa para entender seguidas.",
            font=FUENTE_BODY, bg=FONDO_PANEL, fg=TEXTO_SUAVE,
            anchor="w", justify="left",
        ).pack(fill="x", padx=20, pady=(16, 6))

        self.historial_area = scrolledtext.ScrolledText(
            tab_historial, wrap=tk.WORD, font=FUENTE_BODY,
            bg=FONDO_PANEL, fg=TEXTO_CLARO, insertbackground=TEXTO_CLARO,
            relief="flat", bd=0, padx=20, pady=10
        )
        self.historial_area.pack(fill="both", expand=True)
        self.historial_area.config(state=tk.DISABLED)
        self.historial_area.tag_configure(
            "linea_historial", foreground=TEXTO_CLARO, font=FUENTE_BODY,
            spacing1=4, spacing2=2, spacing3=12, lmargin1=12, lmargin2=12,
        )

        self._agregar_mensaje(
            "Asistente",
            "Hola! Puedo ayudarte a consultar sobre nuestros productos. "
            "Que deseas saber?"
        )
        self._refrescar_historial()
        self._mostrar_vista("conversacion")

    def _mostrar_vista(self, vista):
        """Intercambia conversacion e historial sin perder su contenido."""
        if vista == "historial":
            if self._tab_conversacion.winfo_manager() == "pack":
                self._tab_conversacion.pack_forget()
            self._tab_historial.pack(fill="both", expand=True)
            self.btn_conversacion.config(bg=GRIS_BOTON, fg=TEXTO_CLARO)
            self.btn_historial.config(bg=VERDE_SOBRIO, fg=TEXTO_CLARO)
        else:
            if self._tab_historial.winfo_manager() == "pack":
                self._tab_historial.pack_forget()
            self._tab_conversacion.pack(fill="both", expand=True)
            self.btn_conversacion.config(bg=VERDE_SOBRIO, fg=TEXTO_CLARO)
            self.btn_historial.config(bg=GRIS_BOTON, fg=TEXTO_CLARO)
        self._vista_actual = vista

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
                    "aparecerá acá para dar contexto a la próxima consulta.\n",
                    "linea_historial",
                )
            else:
                nombres = {"user": "Tú", "model": "Asistente"}
                for numero, turno in enumerate(self.historial, 1):
                    texto = "".join(p.get("text", "") for p in turno.get("parts", []))
                    remitente = nombres.get(turno.get("role"), "Asistente")
                    self.historial_area.insert(
                        tk.END, f"{numero:02d}. [{remitente}] {texto}\n\n", "linea_historial"
                    )
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
                texto, error = None, "El asistente requiere conexion con el ADMIN. Verifica que este prendido."
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

    def _productos_en_respuesta(self, texto):
        encontrados = []
        contenido = str(texto or "").lower()
        for producto in self._productos_actuales():
            nombre = str(getattr(producto, "nombre", "") or "").strip()
            if nombre and nombre.lower() in contenido:
                encontrados.append(producto)
        return encontrados

    def _agregar_desde_respuesta(self, producto):
        if self.on_agregar_carro is None:
            return
        ok, mensaje = self.on_agregar_carro(producto)
        _toast(self, mensaje, tipo="exito" if ok else "error")

    def _agregar_botones(self, texto):
        if self.on_agregar_carro is None:
            return
        productos = self._productos_en_respuesta(texto)
        if not productos:
            return
        self.chat_area.config(state=tk.NORMAL)
        for producto in productos:
            boton = tk.Button(
                self.chat_area,
                text=f"+ AGREGAR: {producto.nombre}",
                font=FUENTE_NAV, bg=GRIS_BOTON, fg=TEXTO_CLARO,
                activebackground=VERDE_SOBRIO, activeforeground=TEXTO_CLARO,
                relief="flat", bd=0, cursor="hand2",
                command=lambda p=producto: self._agregar_desde_respuesta(p),
            )
            self.chat_area.window_create(tk.END, window=boton)
            self.chat_area.insert(tk.END, "\n")
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

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

        self._agregar_botones(texto)

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
