"""
interfaz_admin.py
Pantalla de gestión de productos (CRUD completo, Item 1) con tabla
+ formulario. Usa ttk.Treeview y ttk.Combobox -- ambos son parte de
tkinter (tkinter.ttk), no son librerías externas.

Para probar SOLO esta pantalla, ejecuta:
    python interfaz_admin.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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


class PantallaAdmin(tk.Frame):
    """
    Pantalla de gestión de productos: tabla con todo el catálogo +
    formulario para crear, editar y eliminar.

    Parámetros:
        inventario:  instancia de Inventario a administrar. Si no se
                     entrega, se crea una nueva.
        carritos:    dict {usuario: [items]} con los carritos por cliente
                     para consumo del ADMIN (opción B, síncrono en memoria).
        on_volver:   función que se llama al hacer click en "VOLVER".
    """

    def __init__(self, parent, inventario=None, carritos=None, on_volver=None, usuario_actual=None, on_cerrar_sesion=None):
        super().__init__(parent, bg=BG_DARK)
        self.inventario = inventario or Inventario()
        self.carritos = carritos if carritos is not None else {}
        self.on_volver = on_volver
        self.usuario_actual = usuario_actual
        self.on_cerrar_sesion = on_cerrar_sesion
        self.id_seleccionado = None  # None = modo "crear" ; con valor = modo "editar"
        self._ruta_imagen_tmp = None  # ruta a guardar (relativa data/imagenes/xxx.png) o None
        self._origen_imagen_tmp = None  # archivo PNG origen elegido con Examinar (aún no copiado)
        self._preview_img = None  # referencia PhotoImage (evita GC)

        self._crear_barra_superior()
        self._crear_contenido()
        self._refrescar_tabla()

    # ------------------------------------------------------------------
    # BARRA SUPERIOR
    # ------------------------------------------------------------------
    def _crear_barra_superior(self):
        barra = tk.Frame(self, bg=BG_DARK)
        barra.pack(fill="x", padx=40, pady=20)

        tk.Label(
            barra, text="RETRO VAULT — Gestión de Productos", font=FUENTE_LOGO,
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

        nombre = self.usuario_actual or "admin"
        tk.Label(
            barra, text=f"👤 {nombre} (admin)", font=FUENTE_NAV,
            bg=BG_DARK, fg=GREEN, padx=8, pady=8,
        ).pack(side="right", padx=(0, 10))

    def _cerrar_sesion(self):
        if self.on_cerrar_sesion:
            self.on_cerrar_sesion()
        else:
            self._error("Cerrar sesión no disponible en vista aislada")

    # ------------------------------------------------------------------
    # CONTENIDO: tabla (izquierda) + formulario (derecha)
    # ------------------------------------------------------------------
    def _crear_contenido(self):
        contenido = tk.Frame(self, bg=BG_DARK)
        contenido.pack(fill="both", expand=True, padx=40, pady=(0, 20))

        self._crear_tabla(contenido)
        self._crear_formulario_scroll(contenido)

    def _crear_formulario_scroll(self, parent):
        """Columna derecha con scroll para que Guardar/Eliminar/Limpiar
        siempre estén visibles aunque la ventana sea baja (950x600)."""
        wrap = tk.Frame(parent, bg=DARK_CARD, width=320)
        wrap.pack(side="right", fill="y")
        wrap.pack_propagate(False)

        canvas = tk.Canvas(wrap, bg=DARK_CARD, highlightthickness=0, width=300)
        scrollbar = tk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=DARK_CARD)

        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _rueda(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _rueda))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        self.bind("<Destroy>", lambda e: self._desatar_rueda(e, canvas) if e.widget == self else None)

        self._crear_formulario(inner)

    def _desatar_rueda(self, event, canvas):
        try:
            canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass

    def _crear_tabla(self, parent):
        panel = tk.Frame(parent, bg=BG_DARK)
        panel.pack(side="left", fill="both", expand=True, padx=(0, 20))

        # ttk usa "estilos" en vez de bg=/fg= directo -- así se
        # tematiza un Treeview para que combine con el resto de la app.
        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure(
            "Treeview", background=DARK_CARD, foreground=WHITE,
            fieldbackground=DARK_CARD, rowheight=28, font=FUENTE_BODY
        )
        estilo.configure("Treeview.Heading", background=GRAY_BTN, foreground=WHITE, font=FUENTE_NAV)
        estilo.map("Treeview", background=[("selected", GREEN)], foreground=[("selected", BLACK)])

        # La misma tabla alterna entre el inventario y los carritos activos.
        # Así el administrador no pierde espacio en otra ventana ni necesita
        # abrir un reporte para ver lo que ocurre en las cajas.
        self._vista_carritos = False
        columnas = ("id", "nombre", "precio", "stock", "categoria", "foto")
        self.tabla = ttk.Treeview(panel, columns=columnas, show="headings", height=15)

        self.tabla.heading("id", text="ID")
        self.tabla.heading("nombre", text="Nombre")
        self.tabla.heading("precio", text="Precio")
        self.tabla.heading("stock", text="Stock")
        self.tabla.heading("categoria", text="Categoría")
        self.tabla.heading("foto", text="📷")

        self.tabla.column("id", width=40, anchor="center")
        self.tabla.column("nombre", width=200)
        self.tabla.column("precio", width=90, anchor="e")
        self.tabla.column("stock", width=70, anchor="center")
        self.tabla.column("categoria", width=110)
        self.tabla.column("foto", width=40, anchor="center")

        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self._al_seleccionar_fila)

        fila_vista = tk.Frame(panel, bg=BG_DARK)
        fila_vista.pack(fill="x", pady=(12, 0))

        self.label_valor_total = tk.Label(
            fila_vista, text="", font=FUENTE_PRECIO, bg=BG_DARK, fg=GREEN
        )
        self.label_valor_total.pack(side="left")

        self.btn_carritos = tk.Button(
            fila_vista, text="VER CARRITOS ACTIVOS", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0, cursor="hand2",
            command=self._alternar_vista_carritos,
        )
        self.btn_carritos.pack(side="right", ipadx=8, ipady=4)

        self._crear_reportes(panel)

    def _alternar_vista_carritos(self):
        """Cambia la tabla central entre stock y carritos en curso."""
        self._vista_carritos = not self._vista_carritos
        self.id_seleccionado = None
        self._refrescar_tabla()

    def _configurar_columnas_inventario(self):
        encabezados = {
            "id": ("ID", 40, "center"), "nombre": ("Nombre", 200, "w"),
            "precio": ("Precio", 90, "e"), "stock": ("Stock", 70, "center"),
            "categoria": ("Categoría", 110, "w"), "foto": ("📷", 40, "center"),
        }
        for columna, (texto, ancho, ancla) in encabezados.items():
            self.tabla.heading(columna, text=texto)
            self.tabla.column(columna, width=ancho, anchor=ancla, stretch=columna == "nombre")

    def _configurar_columnas_carritos(self):
        encabezados = {
            "id": ("Cliente", 130, "w"), "nombre": ("Producto", 210, "w"),
            "precio": ("Cantidad", 80, "center"), "stock": ("Estado", 110, "center"),
            "categoria": ("", 0, "w"), "foto": ("", 0, "w"),
        }
        for columna, (texto, ancho, ancla) in encabezados.items():
            self.tabla.heading(columna, text=texto)
            self.tabla.column(columna, width=ancho, anchor=ancla, stretch=columna in ("id", "nombre"))

    def _items_carrito(self, items):
        """Acepta tanto carritos locales como la foto simple que llega por red."""
        for item in items or []:
            if not isinstance(item, dict):
                continue
            cantidad = int(item.get("cantidad", 0) or 0)
            producto = item.get("producto")
            if producto is not None:
                yield producto.nombre, cantidad
                continue
            producto = self.inventario.buscar_por_id(item.get("id"))
            yield (producto.nombre if producto is not None else f"Producto #{item.get('id', '?')}"), cantidad

        filas = []
        try:
            for usuario, items in (self.carritos or {}).items():
                if not items: continue
                detalle = []
                for e in items:
                    if isinstance(e, dict):
                        if "producto" in e:
                            p = e["producto"]; nom = getattr(p, "nombre", "Prod")
                        else:
                            pid = e.get("id"); nom = str(pid) if pid is not None else "Prod"
                        c = int(e.get("cantidad", 0))
                    else:
                        c = 0; nom = "Prod"
                    if c: detalle.append(f"{c} {nom}")
                if detalle:
                    filas.append((usuario, " | ".join(detalle)))
        except Exception:
            filas = []
        if filas:
            for usuario, detalle in filas:
                self.tabla.insert("", "end", iid=f"car-{usuario}", values=(usuario, detalle))
        else:
            self.tabla.insert("", "end", iid="sin-carritos", values=("?", "Sin carritos activos"))