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

        tk.Button(
            fila_vista, text="VER VENTAS", font=FUENTE_NAV,
            bg=GREEN, fg=BLACK, relief="flat", bd=0, cursor="hand2",
            command=self._abrir_todas_las_ventas,
        ).pack(side="right", padx=(0, 8), ipadx=8, ipady=4)

        self._crear_reportes(panel)

    def _alternar_vista_carritos(self):
        """Cambia la tabla central entre stock y carritos en curso."""
        self._vista_carritos = not self._vista_carritos
        self.id_seleccionado = None
        self._refrescar_tabla()

    def _abrir_todas_las_ventas(self):
        """Abre la pestaña de detalle conectada a data/ventas.json."""
        try:
            from vistas.pestaña_ventas import abrir_ventana_ventas
        except ImportError:
            try:
                from pestaña_ventas import abrir_ventana_ventas
            except ImportError:
                return
        try:
            abrir_ventana_ventas(self)
        except Exception:
            return

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

    # -- Métodos que el archivo usaba pero no definía (crash al abrir) --
    def _error(self, msg):
        try:
            self.label_error.config(text=msg)
        except Exception:
            pass
        try:
            from vistas.toast import mostrar_toast as _toast_fn
        except ImportError:
            try:
                from toast import mostrar_toast as _toast_fn
            except ImportError:
                _toast_fn = None
        if _toast_fn is not None:
            try:
                _toast_fn(self, msg, tipo="error")
            except Exception:
                pass
        return None

    def _al_seleccionar_fila(self, _event=None):
        if getattr(self, "_vista_carritos", False):
            return None
        try:
            sel = self.tabla.selection()
        except Exception:
            return None
        if not sel:
            return None
        try:
            pid = int(sel[0])
        except (TypeError, ValueError):
            return None
        producto = self.inventario.buscar_por_id(pid)
        if producto is None:
            return None
        self.id_seleccionado = producto.id
        try:
            self.titulo_formulario.config(text=f"Editando #{producto.id}")
            self.btn_guardar.config(text="Actualizar Producto")
            for e, v in ((self.entry_id, str(producto.id)), (self.entry_nombre, producto.nombre),
                         (self.entry_precio, str(producto.precio)), (self.entry_stock, str(producto.stock))):
                e.config(state="normal")
                e.delete(0, tk.END)
                e.insert(0, v)
            self.entry_id.config(state="readonly")
            self.entry_categoria.set(producto.categoria)
            self.label_error.config(text="")
            if self._origen_imagen_tmp:
                _toast(self, "Foto pendiente conservada: pulsa Guardar para aplicarla", tipo="info")
                return
            self._ruta_imagen_tmp = producto.imagen
            self._origen_imagen_tmp = None
            self._set_entry_imagen(producto.imagen or "")
            if producto.imagen:
                base = self._raiz_proyecto()
                ruta_abs = producto.imagen if os.path.isabs(producto.imagen) else os.path.join(base, producto.imagen)
                self._mostrar_preview(ruta_abs)
            else:
                self._mostrar_preview(None)
        except Exception:
            pass
        return None

    def _crear_reportes(self, parent):
        """Reportes por categoría: filtra el inventario y calcula promedio / menor stock."""
        marco = tk.Frame(parent, bg=DARK_CARD, padx=12, pady=12)
        marco.pack(fill="x", pady=(12, 0))

        tk.Label(
            marco, text="Reportes por categoría", font=FUENTE_NAV,
            bg=DARK_CARD, fg=GREEN,
        ).pack(anchor="w", pady=(0, 8))

        fila = tk.Frame(marco, bg=DARK_CARD)
        fila.pack(fill="x")

        self.combo_reporte = ttk.Combobox(
            fila, font=FUENTE_BODY, width=22, state="readonly",
            values=self.inventario.obtener_categorias(),
        )
        self.combo_reporte.pack(side="left", padx=(0, 8))
        self.combo_reporte.set("Elige categoría")

        tk.Button(
            fila, text="Promedio", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0, cursor="hand2",
            command=self._reporte_promedio
        ).pack(side="left", padx=4, ipadx=8, ipady=4)

        tk.Button(
            fila, text="Menor stock", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0, cursor="hand2",
            command=self._reporte_menor_stock
        ).pack(side="left", padx=4, ipadx=8, ipady=4)

        self.label_reporte = tk.Label(
            marco, text="", font=FUENTE_BODY,
            bg=DARK_CARD, fg=WHITE, wraplength=480, justify="left",
        )
        self.label_reporte.pack(anchor="w", pady=(8, 0))

    def _categoria_reporte(self):
        """Categoría elegida o None (con error en pantalla)."""
        cat = self.combo_reporte.get().strip()
        if not cat or cat == "Elige categoría":
            self._error("Elige una categoría para el reporte")
            return None
        return cat

    @staticmethod
    def _fmt_clp(valor):
        return f"${valor:,.0f}".replace(",", ".")

    def _reporte_promedio(self):
        cat = self._categoria_reporte()
        if cat is None:
            return
        prom = self.inventario.calcular_promedio_categoria(cat)
        if prom is None:
            msg = f"Sin productos en '{cat}'"
            self.label_reporte.config(text=msg)
            _toast(self, msg, tipo="error")
            return
        n = sum(1 for p in self.inventario.productos if p.categoria.lower() == cat.lower())
        msg = f"Promedio '{cat}': {self._fmt_clp(prom)} ({n} productos)"
        self.label_reporte.config(text=msg)
        _toast(self, msg, tipo="exito")

    def _reporte_menor_stock(self):
        cat = self._categoria_reporte()
        if cat is None:
            return
        prod = self.inventario.producto_menor_stock_categoria(cat)
        if prod is None:
            msg = f"Sin productos en '{cat}'"
            self.label_reporte.config(text=msg)
            _toast(self, msg, tipo="error")
            return
        msg = f"Menor stock '{cat}': {prod.nombre} ({prod.stock} uds.)"
        self.label_reporte.config(text=msg)
        _toast(self, msg, tipo="exito")

    def _crear_formulario(self, parent):
        """Formulario mínimo de productos: agregar / editar / eliminar."""
        panel = tk.Frame(parent, bg=DARK_CARD, padx=25, pady=25)
        panel.pack(fill="both", expand=True)
        self.titulo_formulario = tk.Label(panel, text="Nuevo Producto", font=FUENTE_TITULO, bg=DARK_CARD, fg=WHITE)
        self.titulo_formulario.pack(pady=(0, 20), anchor="w")
        self.entry_id = self._campo_texto(panel, "ID (vacío = automático)")
        self.entry_nombre = self._campo_texto(panel, "Nombre")
        self.entry_precio = self._campo_texto(panel, "Precio (CLP)")
        self.entry_stock = self._campo_texto(panel, "Stock")
        tk.Label(panel, text="Categoría", font=FUENTE_NAV, bg=DARK_CARD, fg=GRAY_TEXT).pack(anchor="w", pady=(8, 2))
        try:
            cats = self.inventario.obtener_categorias()
        except Exception:
            cats = []
        self.entry_categoria = ttk.Combobox(panel, font=FUENTE_BODY, values=cats)
        self.entry_categoria.pack(fill="x", ipady=2)
        self._campo_imagen(panel)
        self.label_error = tk.Label(panel, text="", font=(FUENTE_BODY[0], 9),
                                    bg=DARK_CARD, fg="#ff6b6b", wraplength=220, justify="left")
        self.label_error.pack(anchor="w", pady=(8, 8))
        self.btn_guardar = tk.Button(panel, text="Agregar Producto", font=FUENTE_BOTON,
                                     bg=GREEN, fg=BLACK, relief="flat", bd=0, cursor="hand2",
                                     command=self._guardar)
        self.btn_guardar.pack(fill="x", ipady=8, pady=4)
        tk.Button(panel, text="Eliminar seleccionado", font=FUENTE_BOTON,
                  bg="#c0392b", fg=WHITE, relief="flat", bd=0, cursor="hand2",
                  command=self._eliminar).pack(fill="x", ipady=8, pady=4)
        tk.Button(panel, text="Vaciar inventario", font=FUENTE_NAV,
                  bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0, cursor="hand2",
                  command=self._vaciar_inventario).pack(fill="x", ipady=6, pady=4)
        tk.Button(panel, text="Limpiar formulario", font=FUENTE_NAV,
                  bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0, cursor="hand2",
                  command=self._limpiar_formulario).pack(fill="x", ipady=6, pady=(15, 0))

    def _campo_texto(self, parent, etiqueta):
        tk.Label(parent, text=etiqueta, font=FUENTE_NAV, bg=DARK_CARD, fg=GRAY_TEXT).pack(anchor="w", pady=(8, 2))
        entry = tk.Entry(parent, font=FUENTE_BODY, relief="flat", bd=4)
        entry.pack(fill="x", ipady=4)
        return entry

    def _campo_imagen(self, parent):
        """Imagen PNG: Examinar/Quitar + preview. Se copia a data/imagenes/ al Guardar."""
        tk.Label(parent, text="Imagen (PNG)", font=FUENTE_NAV, bg=DARK_CARD, fg=GRAY_TEXT).pack(anchor="w", pady=(8, 2))
        self.entry_imagen = tk.Entry(parent, font=FUENTE_BODY, relief="flat", bd=4, state="readonly")
        self.entry_imagen.pack(fill="x", ipady=4)
        btns = tk.Frame(parent, bg=DARK_CARD)
        btns.pack(fill="x", pady=(4, 0))
        tk.Button(
            btns, text="Examinar PNG", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0, cursor="hand2",
            command=self._examinar_imagen
        ).pack(side="left", expand=True, fill="x", padx=(0, 4), ipady=4)
        tk.Button(
            btns, text="Quitar", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0, cursor="hand2",
            command=self._quitar_imagen
        ).pack(side="left", expand=True, fill="x", padx=(4, 0), ipady=4)
        self.lbl_preview = tk.Label(parent, text="Sin imagen", font=FUENTE_BODY, bg="#e4e4e4", fg=GRAY_TEXT, width=28, height=4)
        self.lbl_preview.pack(fill="x", pady=(8, 0))

    def _raiz_proyecto(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _dir_imagenes(self):
        d = os.path.join(self._raiz_proyecto(), "data", "imagenes")
        os.makedirs(d, exist_ok=True)
        return d

    def _set_entry_imagen(self, texto):
        self.entry_imagen.config(state="normal")
        self.entry_imagen.delete(0, tk.END)
        if texto:
            self.entry_imagen.insert(0, texto)
        self.entry_imagen.config(state="readonly")

    def _mostrar_preview(self, ruta):
        """Preview 190x140 con PNG nativo; fallback a texto si falla."""
        try:
            if ruta and os.path.exists(ruta):
                img = tk.PhotoImage(file=ruta)
                fx = max(1, img.width() // 190 + (1 if img.width() % 190 else 0))
                fy = max(1, img.height() // 140 + (1 if img.height() % 140 else 0))
                f = max(fx, fy)
                if f > 1:
                    img = img.subsample(f, f)
                self._preview_img = img
                self.lbl_preview.config(image=img, text="", width=190, height=140)
                return
        except Exception:
            pass
        self._preview_img = None
        self.lbl_preview.config(image="", text="Sin imagen", width=28, height=4)

    def _examinar_imagen(self):
        origen = filedialog.askopenfilename(
            title="Elegir imagen PNG del producto",
            filetypes=[("PNG", "*.png"), ("Todos", "*.*")],
        )
        if not origen:
            return
        if not origen.lower().endswith(".png"):
            self.label_error.config(text="Solo se permiten imágenes PNG (nativo)")
            return
        try:
            tk.PhotoImage(file=origen)
        except Exception:
            self.label_error.config(text="Ese PNG no se pudo leer")
            return
        self._origen_imagen_tmp = origen
        self._set_entry_imagen(os.path.basename(origen) + " (pendiente)")
        self._mostrar_preview(origen)
        self.label_error.config(text="")
        _toast(self, "PNG listo: pulsa Guardar para copiarlo a data/imagenes/", tipo="exito")

    def _quitar_imagen(self):
        self._origen_imagen_tmp = None
        self._ruta_imagen_tmp = None
        self._set_entry_imagen("")
        self._mostrar_preview(None)
        self.label_error.config(text="")

    def _copiar_imagen_al_guardar(self, id_producto):
        """Copia el PNG a data/imagenes/id_<id>.png. Retorna (ruta_rel, error)."""
        if not self._origen_imagen_tmp:
            return self._ruta_imagen_tmp, None
        if not os.path.exists(self._origen_imagen_tmp):
            return self._ruta_imagen_tmp, f"Origen no existe: {self._origen_imagen_tmp}"
        destino = os.path.join(self._dir_imagenes(), f"id_{id_producto}.png")
        try:
            shutil.copyfile(self._origen_imagen_tmp, destino)
        except Exception as e:
            return self._ruta_imagen_tmp, f"No se pudo copiar el PNG: {e}"
        try:
            if not os.path.exists(destino) or os.path.getsize(destino) == 0:
                return self._ruta_imagen_tmp, f"La copia quedó vacía o no existe: {destino}"
            tk.PhotoImage(file=destino)
        except Exception as e:
            return self._ruta_imagen_tmp, f"La copia no se puede leer: {e}"
        rel = os.path.join("data", "imagenes", f"id_{id_producto}.png").replace(os.sep, "/")
        self._origen_imagen_tmp = None
        return rel, None

    def _leer_formulario(self):
        id_txt = self.entry_id.get().strip()
        if id_txt == "":
            id_manual = None
        else:
            try:
                if any(c in id_txt for c in ".,"):
                    raise ValueError
                id_manual = int(id_txt)
            except ValueError:
                self.label_error.config(text="El ID debe ser un número entero")
                return None
            if id_manual < 1:
                self.label_error.config(text="El ID debe ser mayor o igual a 1")
                return None
            if self.id_seleccionado is None and self.inventario.buscar_por_id(id_manual) is not None:
                self.label_error.config(text=f"Ya existe un producto con ID {id_manual}")
                return None
        nombre = self.entry_nombre.get().strip()
        categoria = self.entry_categoria.get().strip()
        if not nombre:
            self.label_error.config(text="El nombre no puede estar vacío")
            return None
        if not categoria:
            self.label_error.config(text="La categoría no puede estar vacía")
            return None
        try:
            precio = float(self.entry_precio.get().replace(".", "").replace(",", ""))
        except ValueError:
            self.label_error.config(text="El precio debe ser un número")
            return None
        try:
            stock = int(self.entry_stock.get())
        except ValueError:
            self.label_error.config(text="El stock debe ser un número entero")
            return None
        if precio < 0:
            self.label_error.config(text="El precio no puede ser negativo")
            return None
        if stock < 0:
            self.label_error.config(text="El stock no puede ser negativo")
            return None
        self.label_error.config(text="")
        return id_manual, nombre, precio, stock, categoria

    def _guardar(self):
        datos = self._leer_formulario()
        if datos is None:
            if self._origen_imagen_tmp:
                _toast(self, "Corrige el formulario (foto PNG conservada)", tipo="info")
            return
        id_manual, nombre, precio, stock, categoria = datos
        try:
            if self.id_seleccionado is None:
                nuevo = self.inventario.agregar_producto(nombre, precio, stock, categoria, imagen=None, id=id_manual)
                ruta_rel, err = self._copiar_imagen_al_guardar(nuevo.id)
                if err:
                    self.id_seleccionado = nuevo.id
                    self.titulo_formulario.config(text=f"Editando #{nuevo.id}")
                    self.btn_guardar.config(text="Actualizar Producto")
                    self.label_error.config(text=err + " (producto guardado sin foto, reintenta)")
                    self._refrescar_tabla()
                    return
                if ruta_rel != nuevo.imagen:
                    self.inventario.actualizar_producto(nuevo.id, nombre, precio, stock, categoria, imagen=ruta_rel)
                self._ruta_imagen_tmp = ruta_rel
                _toast(self, f"Producto '{nombre}' agregado", tipo="exito")
            else:
                ruta_rel, err = self._copiar_imagen_al_guardar(self.id_seleccionado)
                if err:
                    self.label_error.config(text=err + " (no se guardó la foto, reintenta)")
                    self._refrescar_tabla()
                    return
                self.inventario.actualizar_producto(self.id_seleccionado, nombre, precio, stock, categoria, imagen=ruta_rel)
                self._ruta_imagen_tmp = ruta_rel
                _toast(self, f"Producto '{nombre}' actualizado", tipo="exito")
        except ValueError as e:
            self.label_error.config(text=str(e))
            return
        self._refrescar_tabla()
        self._limpiar_formulario()

    def _eliminar(self):
        if self.id_seleccionado is None:
            self.label_error.config(text="Selecciona un producto de la tabla primero")
            return
        producto = self.inventario.buscar_por_id(self.id_seleccionado)
        if producto is None:
            self.label_error.config(text="El producto seleccionado ya no existe")
            return
        if not messagebox.askyesno("Confirmar eliminación", f"¿Eliminar '{producto.nombre}'?"):
            return
        self.inventario.eliminar_producto(self.id_seleccionado)
        # Borra su PNG para no dejar huérfanos en data/imagenes/
        try:
            img = (producto.imagen or "").replace("\\", "/")
            if img.startswith("data/imagenes/"):
                abs_img = os.path.join(self._raiz_proyecto(), img)
                if os.path.exists(abs_img):
                    os.remove(abs_img)
        except Exception:
            pass
        self._refrescar_tabla()
        self._limpiar_formulario()

    def _vaciar_inventario(self):
        """Hito 2 ADMIN: elimina TODOS los productos (con confirmación)."""
        if not self.inventario.productos:
            self.label_error.config(text="El inventario ya está vacío")
            return
        n = len(self.inventario.productos)
        if not messagebox.askyesno(
            "Vaciar inventario",
            f"¿Eliminar los {n} productos del inventario? No se puede deshacer.",
        ):
            return
        imagenes = [(p.imagen or "").replace("\\", "/") for p in self.inventario.productos]
        self.inventario.vaciar_inventario()
        # Borra los PNG huérfanos de data/imagenes/
        for img in imagenes:
            try:
                if img.startswith("data/imagenes/"):
                    abs_img = os.path.join(self._raiz_proyecto(), img)
                    if os.path.exists(abs_img):
                        os.remove(abs_img)
            except Exception:
                pass
        _toast(self, f"Inventario vaciado ({n} productos)", tipo="exito")
        self._refrescar_tabla()
        self._limpiar_formulario()

    def _limpiar_formulario(self):
        self.id_seleccionado = None
        try:
            self.titulo_formulario.config(text="Nuevo Producto")
            self.btn_guardar.config(text="Agregar Producto")
            self.label_error.config(text="")
            self.entry_id.config(state="normal")
            self.entry_id.delete(0, tk.END)
            self.entry_nombre.delete(0, tk.END)
            self.entry_precio.delete(0, tk.END)
            self.entry_stock.delete(0, tk.END)
            self.entry_categoria.set("")
            self._ruta_imagen_tmp = None
            self._origen_imagen_tmp = None
            try:
                self._set_entry_imagen("")
                self._mostrar_preview(None)
            except Exception:
                pass
            if self.tabla.selection():
                self.tabla.selection_remove(self.tabla.selection())
        except Exception:
            pass

    def _refrescar_tabla(self):
        """Rellena la tabla según _vista_carritos (inventario o carritos)."""
        try:
            for fila in self.tabla.get_children():
                self.tabla.delete(fila)
        except Exception:
            return
        try:
            if self._vista_carritos:
                self._configurar_columnas_carritos()
                hay = False
                for usuario, items in (self.carritos or {}).items():
                    nombres = [f"{c} {n}" for n, c in self._items_carrito(items) if c]
                    if nombres:
                        hay = True
                        self.tabla.insert("", "end", iid=f"car-{usuario}",
                                          values=(usuario, " | ".join(nombres), "", "", "", ""))
                if not hay:
                    self.tabla.insert("", "end", iid="sin-carritos",
                                      values=("?", "Sin carritos activos", "", "", "", ""))
                self.label_valor_total.config(text="")
                self.btn_carritos.config(text="VER INVENTARIO")
            else:
                self._configurar_columnas_inventario()
                for p in self.inventario.productos:
                    precio_fmt = f"${p.precio:,.0f}".replace(",", ".")
                    marca = "✓" if getattr(p, "imagen", None) else "—"
                    self.tabla.insert("", "end", iid=str(p.id),
                                      values=(p.id, p.nombre, precio_fmt, p.stock, p.categoria, marca))
                try:
                    total = self.inventario.calcular_valor_inventario()
                    self.label_valor_total.config(
                        text=f"Valor total del inventario: ${total:,.0f}".replace(",", "."))
                except Exception:
                    pass
                self.btn_carritos.config(text="VER CARRITOS ACTIVOS")
                try:
                    self.entry_categoria["values"] = self.inventario.obtener_categorias()
                except Exception:
                    pass
                if hasattr(self, "combo_reporte"):
                    try:
                        actual = self.combo_reporte.get()
                        self.combo_reporte["values"] = self.inventario.obtener_categorias()
                        if actual not in list(self.combo_reporte["values"]) + ["Elige categoría"]:
                            self.combo_reporte.set("Elige categoría")
                    except Exception:
                        pass
        except Exception:
            pass