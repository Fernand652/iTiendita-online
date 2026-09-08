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
        on_volver:   función que se llama al hacer click en "VOLVER".
    """

    def __init__(self, parent, inventario=None, on_volver=None, usuario_actual=None, on_cerrar_sesion=None):
        super().__init__(parent, bg=BG_DARK)
        self.inventario = inventario or Inventario()
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

        self.label_valor_total = tk.Label(
            panel, text="", font=FUENTE_PRECIO, bg=BG_DARK, fg=GREEN
        )
        self.label_valor_total.pack(anchor="w", pady=(12, 0))

        self._crear_reportes(panel)

    def _crear_reportes(self, parent):
        """Sección Reportes por categoría: promedio y menor stock (Item 3)."""
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

        self._crear_reportes(panel)

    def _crear_formulario(self, parent):
        panel = tk.Frame(parent, bg=DARK_CARD, padx=25, pady=25)
        panel.pack(fill="both", expand=True)

        tk.Label(
            panel, text="Selecciona una fila para editar o eliminar",
            font=(FUENTE_BODY[0], 9, "italic"), bg=DARK_CARD, fg=GRAY_TEXT,
            wraplength=250, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        self.titulo_formulario = tk.Label(
            panel, text="Nuevo Producto", font=FUENTE_TITULO, bg=DARK_CARD, fg=WHITE
        )
        self.titulo_formulario.pack(pady=(0, 20), anchor="w")

        self.entry_id = self._campo_texto(panel, "ID (vacío = automático)")
        self.entry_nombre = self._campo_texto(panel, "Nombre")
        self.entry_precio = self._campo_texto(panel, "Precio (CLP)")
        self.entry_stock = self._campo_texto(panel, "Stock")
        self.entry_categoria = self._campo_categoria(panel)
        self._campo_imagen(panel)

        self.label_error = tk.Label(
            panel, text="", font=(FUENTE_BODY[0], 9),
            bg=DARK_CARD, fg="#ff6b6b", wraplength=220, justify="left"
        )
        self.label_error.pack(anchor="w", pady=(8, 8))

        self.btn_guardar = tk.Button(
            panel, text="Agregar Producto", font=FUENTE_BOTON,
            bg=GREEN, fg=BLACK, relief="flat", bd=0, cursor="hand2",
            command=self._guardar
        )
        self.btn_guardar.pack(fill="x", ipady=8, pady=4)

        tk.Button(
            panel, text="Eliminar seleccionado", font=FUENTE_BOTON,
            bg="#c0392b", fg=WHITE, relief="flat", bd=0, cursor="hand2",
            command=self._eliminar
        ).pack(fill="x", ipady=8, pady=4)

        tk.Button(
            panel, text="Limpiar formulario", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0, cursor="hand2",
            command=self._limpiar_formulario
        ).pack(fill="x", ipady=6, pady=(15, 0))

    def _campo_texto(self, parent, etiqueta):
        tk.Label(parent, text=etiqueta, font=FUENTE_NAV, bg=DARK_CARD, fg=GRAY_TEXT).pack(anchor="w", pady=(8, 2))
        entry = tk.Entry(parent, font=FUENTE_BODY, relief="flat", bd=4)
        entry.pack(fill="x", ipady=4)
        return entry

    def _campo_categoria(self, parent):
        """
        Combobox en vez de Entry normal: muestra las categorías que ya
        existen (para elegir con un click) pero también permite escribir
        una nueva. Esto evita que Item 3 (promedio/menor stock por
        categoría) falle por errores de tipeo como "Videojuegos" vs
        "videojuegos " con espacio de más.
        """
        tk.Label(parent, text="Categoría", font=FUENTE_NAV, bg=DARK_CARD, fg=GRAY_TEXT).pack(anchor="w", pady=(8, 2))
        combo = ttk.Combobox(parent, font=FUENTE_BODY, values=self.inventario.obtener_categorias())
        combo.pack(fill="x", ipady=2)
        return combo

    def _campo_imagen(self, parent):
        """Fila Imagen PNG: preview + Examinar/Quitar. Guarda en data/imagenes/."""
        tk.Label(parent, text="Imagen (PNG)", font=FUENTE_NAV, bg=DARK_CARD, fg=GRAY_TEXT).pack(anchor="w", pady=(8, 2))
        fila = tk.Frame(parent, bg=DARK_CARD)
        fila.pack(fill="x")

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
                # Reescala por enteros para encajar aprox. en 190x140
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
        # Fallback compacto: restaurar width/height de texto (28x4).
        # Sin esto el label vacío heredaba 190x140 px de la foto y
        # quedaba un bloque gris gigante tras Limpiar/Guardar/Quitar.
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
            return self._error("Solo se permiten imágenes PNG (nativo)")
        # Validar que tkinter la pueda leer
        try:
            tk.PhotoImage(file=origen)
        except Exception:
            return self._error("Ese PNG no se pudo leer")
        self._origen_imagen_tmp = origen
        # Si ya hay ruta guardada (editando), se mantiene hasta guardar;
        # si es nuevo, previsualizamos el origen y mostramos su nombre
        # con marca de pendiente: la copia real ocurre en Guardar.
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
        """
        Copia el PNG elegido a data/imagenes/id_<id>.png y VERIFICA
        que quedó en disco. Retorna (ruta_rel_o_None, error_o_None).
        Solo PNG nativo (sin Pillow).
        """
        # Sin origen nuevo: conservar la ruta que ya tenía (editar sin cambiar foto)
        if not self._origen_imagen_tmp:
            return self._ruta_imagen_tmp, None
        if not os.path.exists(self._origen_imagen_tmp):
            return self._ruta_imagen_tmp, f"Origen no existe: {self._origen_imagen_tmp}"
        destino = os.path.join(self._dir_imagenes(), f"id_{id_producto}.png")
        try:
            shutil.copyfile(self._origen_imagen_tmp, destino)
        except Exception as e:
            return self._ruta_imagen_tmp, f"No se pudo copiar el PNG: {e}"
        # Verificación real en disco (no solo "sin excepción")
        try:
            if not os.path.exists(destino) or os.path.getsize(destino) == 0:
                return self._ruta_imagen_tmp, f"La copia quedó vacía o no existe: {destino}"
            tk.PhotoImage(file=destino)  # verifica que la copia se puede leer
        except Exception as e:
            return self._ruta_imagen_tmp, f"La copia no se puede leer: {e}"
        rel = os.path.join("data", "imagenes", f"id_{id_producto}.png").replace(os.sep, "/")
        self._origen_imagen_tmp = None
        return rel, None

    # ------------------------------------------------------------------
    # LÓGICA
    # ------------------------------------------------------------------
    def _refrescar_tabla(self):
        """Vuelve a dibujar la tabla y el valor total con los datos actuales."""
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)

        for p in self.inventario.productos:
            precio_fmt = f"${p.precio:,.0f}".replace(",", ".")
            marca_foto = "✓" if getattr(p, "imagen", None) else "—"
            self.tabla.insert("", "end", iid=str(p.id), values=(p.id, p.nombre, precio_fmt, p.stock, p.categoria, marca_foto))

        valor_total = self.inventario.calcular_valor_inventario()
        valor_fmt = f"${valor_total:,.0f}".replace(",", ".")
        self.label_valor_total.config(text=f"Valor total del inventario: {valor_fmt}")

        self.entry_categoria["values"] = self.inventario.obtener_categorias()
        if hasattr(self, "combo_reporte"):
            actual = self.combo_reporte.get()
            self.combo_reporte["values"] = self.inventario.obtener_categorias()
            if actual not in list(self.combo_reporte["values"]) + ["Elige categoría"]:
                self.combo_reporte.set("Elige categoría")

    def _al_seleccionar_fila(self, event):
        seleccion = self.tabla.selection()
        if not seleccion:
            return

        producto = self.inventario.buscar_por_id(int(seleccion[0]))
        if producto is None:
            return

        self.id_seleccionado = producto.id
        self.titulo_formulario.config(text=f"Editando #{producto.id}")
        self.btn_guardar.config(text="Actualizar Producto")

        # ID inmutable al editar: se muestra readonly, no se valida de nuevo
        self.entry_id.config(state="normal")
        self.entry_id.delete(0, tk.END)
        self.entry_id.insert(0, str(producto.id))
        self.entry_id.config(state="readonly")
        self.entry_nombre.delete(0, tk.END)
        self.entry_nombre.insert(0, producto.nombre)
        self.entry_precio.delete(0, tk.END)
        self.entry_precio.insert(0, str(producto.precio))
        self.entry_stock.delete(0, tk.END)
        self.entry_stock.insert(0, str(producto.stock))
        self.entry_categoria.set(producto.categoria)
        # Si había un PNG pendiente de guardar, se conserva (no se pierde
        # en silencio al cambiar de fila): se aplicará al Guardar.
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

    def _limpiar_formulario(self):
        self.id_seleccionado = None
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
        self._set_entry_imagen("")
        self._mostrar_preview(None)

        if self.tabla.selection():
            self.tabla.selection_remove(self.tabla.selection())

    def _error(self, msg):
        """Error EN PANTALLA (label fijo + toast flotante 2s)."""
        self.label_error.config(text=msg)
        _toast(self, msg, tipo="error")
        return None

    def _leer_formulario(self):
        """
        Lee y valida el formulario. Retorna (id_or_None, nombre, precio,
        stock, categoria, imagen) o None si hay un error (label+toast).
        `id_or_None`: vacío → automático; con valor → entero >= 1 y único
        (solo se valida duplicado en modo crear; en editar el ID es
        inmutable y se ignora este campo).
        `imagen` es la ruta relativa actual (puede ser None); si hay un
        PNG nuevo por copiar, se resuelve en _guardar().
        """
        id_txt = self.entry_id.get().strip()
        if id_txt == "":
            id_manual = None
        else:
            # Acepta "7" (no "7.5" ni "1,000"): entero estricto
            try:
                if any(c in id_txt for c in ".,"):
                    raise ValueError
                id_manual = int(id_txt)
            except ValueError:
                return self._error("El ID debe ser un número entero")
            if id_manual < 1:
                return self._error("El ID debe ser mayor o igual a 1")
            if self.id_seleccionado is None and self.inventario.buscar_por_id(id_manual) is not None:
                return self._error(f"Ya existe un producto con ID {id_manual}")
        nombre = self.entry_nombre.get().strip()
        categoria = self.entry_categoria.get().strip()

        if nombre == "":
            return self._error("El nombre no puede estar vacío")
        if categoria == "":
            return self._error("La categoría no puede estar vacía")

        # Se aceptan precios con o sin puntos de miles ("149990" o
        # "149.990"), para que no choque con el formato en que se
        # MUESTRA el precio en el resto de la tienda.
        try:
            precio = float(self.entry_precio.get().replace(".", "").replace(",", ""))
        except ValueError:
            return self._error("El precio debe ser un número")

        try:
            stock = int(self.entry_stock.get())
        except ValueError:
            return self._error("El stock debe ser un número entero")

        if precio < 0:
            return self._error("El precio no puede ser negativo")
        if stock < 0:
            return self._error("El stock no puede ser negativo")

        self.label_error.config(text="")
        return id_manual, nombre, precio, stock, categoria, self._ruta_imagen_tmp

    def _guardar(self):
        datos = self._leer_formulario()
        if datos is None:
            # Validación fallida: la foto pendiente se conserva para reintentar
            if self._origen_imagen_tmp:
                _toast(self, "Corrige el formulario (foto PNG conservada)", tipo="info")
            return
        id_manual, nombre, precio, stock, categoria, _ = datos

        if self.id_seleccionado is None:
            habia_foto_nueva = bool(self._origen_imagen_tmp)
            try:
                nuevo = self.inventario.agregar_producto(nombre, precio, stock, categoria, imagen=None, id=id_manual)
            except ValueError as e:
                self._error(str(e))
                return
            # Copiar el PNG ahora que ya existe el ID real
            ruta_rel, err = self._copiar_imagen_al_guardar(nuevo.id)
            if err:
                # Producto guardado pero foto NO: quedar en modo edición
                # del nuevo producto para reintentar sin perder nada.
                self.id_seleccionado = nuevo.id
                self.titulo_formulario.config(text=f"Editando #{nuevo.id}")
                self.btn_guardar.config(text="Actualizar Producto")
                self.entry_id.config(state="normal")
                self.entry_id.delete(0, tk.END)
                self.entry_id.insert(0, str(nuevo.id))
                self.entry_id.config(state="readonly")
                self._ruta_imagen_tmp = ruta_rel
                self._error(err + " (producto guardado sin foto, reintenta)")
                self._refrescar_tabla()
                return
            if ruta_rel != nuevo.imagen:
                try:
                    self.inventario.actualizar_producto(nuevo.id, nombre, precio, stock, categoria, imagen=ruta_rel)
                except ValueError as e:
                    self._error(str(e))
                    return
            self._ruta_imagen_tmp = ruta_rel
            if habia_foto_nueva:
                _toast(self, f"Foto guardada: {ruta_rel}", tipo="exito")
            else:
                _toast(self, f"Producto '{nombre}' agregado", tipo="exito")
        else:
            habia_foto_nueva = bool(self._origen_imagen_tmp)
            ruta_rel, err = self._copiar_imagen_al_guardar(self.id_seleccionado)
            if err:
                self._error(err + " (no se guardó la foto, reintenta)")
                self._refrescar_tabla()
                return
            try:
                self.inventario.actualizar_producto(self.id_seleccionado, nombre, precio, stock, categoria, imagen=ruta_rel)
            except ValueError as e:
                self._error(str(e))
                return
            self._ruta_imagen_tmp = ruta_rel
            if habia_foto_nueva:
                _toast(self, f"Foto guardada: {ruta_rel}", tipo="exito")
            else:
                _toast(self, f"Producto '{nombre}' actualizado", tipo="exito")

        self._refrescar_tabla()
        self._limpiar_formulario()

    def _eliminar(self):
        if self.id_seleccionado is None:
            self._error("Selecciona un producto de la tabla primero")
            return

        producto = self.inventario.buscar_por_id(self.id_seleccionado)
        if not messagebox.askyesno("Confirmar eliminación", f"¿Seguro que quieres eliminar '{producto.nombre}'?"):
            return

        self.inventario.eliminar_producto(self.id_seleccionado)
        # Borrar su PNG (solo si vive en data/imagenes/) para no dejar huérfanos
        try:
            img = (producto.imagen or "").replace("\\", "/")
            if img.startswith("data/imagenes/"):
                abs_img = os.path.join(self._raiz_proyecto(), img)
                if os.path.exists(abs_img):
                    os.remove(abs_img)
        except Exception:
            pass
        _toast(self, f"Producto '{producto.nombre}' eliminado", tipo="exito")
        self._refrescar_tabla()
        self._limpiar_formulario()


# ==============================================================================
# PRUEBA INDEPENDIENTE
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("RetroVault - Administración")
    root.geometry("950x600")
    root.configure(bg=BG_DARK)

    pantalla = PantallaAdmin(root)
    pantalla.pack(fill="both", expand=True)

    root.mainloop()