"""
interfaz_admin.py
Pantalla de gestión de productos (CRUD completo, Item 1) con tabla
+ formulario. Usa ttk.Treeview y ttk.Combobox -- ambos son parte de
tkinter (tkinter.ttk), no son librerías externas.

Para probar SOLO esta pantalla, ejecuta:
    python interfaz_admin.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
from estilos import *
from inventario import Inventario


class PantallaAdmin(tk.Frame):
    """
    Pantalla de gestión de productos: tabla con todo el catálogo +
    formulario para crear, editar y eliminar.

    Parámetros:
        inventario:  instancia de Inventario a administrar. Si no se
                     entrega, se crea una nueva.
        on_volver:   función que se llama al hacer click en "VOLVER".
    """

    def __init__(self, parent, inventario=None, on_volver=None):
        super().__init__(parent, bg=BG_DARK)
        self.inventario = inventario or Inventario()
        self.on_volver = on_volver
        self.id_seleccionado = None  # None = modo "crear" ; con valor = modo "editar"

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

    # ------------------------------------------------------------------
    # CONTENIDO: tabla (izquierda) + formulario (derecha)
    # ------------------------------------------------------------------
    def _crear_contenido(self):
        contenido = tk.Frame(self, bg=BG_DARK)
        contenido.pack(fill="both", expand=True, padx=40, pady=(0, 20))

        self._crear_tabla(contenido)
        self._crear_formulario(contenido)

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

        columnas = ("id", "nombre", "precio", "stock", "categoria")
        self.tabla = ttk.Treeview(panel, columns=columnas, show="headings", height=15)

        self.tabla.heading("id", text="ID")
        self.tabla.heading("nombre", text="Nombre")
        self.tabla.heading("precio", text="Precio")
        self.tabla.heading("stock", text="Stock")
        self.tabla.heading("categoria", text="Categoría")

        self.tabla.column("id", width=40, anchor="center")
        self.tabla.column("nombre", width=220)
        self.tabla.column("precio", width=90, anchor="e")
        self.tabla.column("stock", width=70, anchor="center")
        self.tabla.column("categoria", width=120)

        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self._al_seleccionar_fila)

        self.label_valor_total = tk.Label(
            panel, text="", font=FUENTE_PRECIO, bg=BG_DARK, fg=GREEN
        )
        self.label_valor_total.pack(anchor="w", pady=(12, 0))

    def _crear_formulario(self, parent):
        panel = tk.Frame(parent, bg=DARK_CARD, padx=25, pady=25)
        panel.pack(side="right", fill="y")

        self.titulo_formulario = tk.Label(
            panel, text="Nuevo Producto", font=FUENTE_TITULO, bg=DARK_CARD, fg=WHITE
        )
        self.titulo_formulario.pack(pady=(0, 20), anchor="w")

        self.entry_nombre = self._campo_texto(panel, "Nombre")
        self.entry_precio = self._campo_texto(panel, "Precio (CLP)")
        self.entry_stock = self._campo_texto(panel, "Stock")
        self.entry_categoria = self._campo_categoria(panel)

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

    # ------------------------------------------------------------------
    # LÓGICA
    # ------------------------------------------------------------------
    def _refrescar_tabla(self):
        """Vuelve a dibujar la tabla y el valor total con los datos actuales."""
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)

        for p in self.inventario.productos:
            precio_fmt = f"${p.precio:,.0f}".replace(",", ".")
            self.tabla.insert("", "end", iid=str(p.id), values=(p.id, p.nombre, precio_fmt, p.stock, p.categoria))

        valor_total = self.inventario.calcular_valor_inventario()
        valor_fmt = f"${valor_total:,.0f}".replace(",", ".")
        self.label_valor_total.config(text=f"Valor total del inventario: {valor_fmt}")

        self.entry_categoria["values"] = self.inventario.obtener_categorias()

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

        self.entry_nombre.delete(0, tk.END)
        self.entry_nombre.insert(0, producto.nombre)
        self.entry_precio.delete(0, tk.END)
        self.entry_precio.insert(0, str(producto.precio))
        self.entry_stock.delete(0, tk.END)
        self.entry_stock.insert(0, str(producto.stock))
        self.entry_categoria.set(producto.categoria)

    def _limpiar_formulario(self):
        self.id_seleccionado = None
        self.titulo_formulario.config(text="Nuevo Producto")
        self.btn_guardar.config(text="Agregar Producto")
        self.label_error.config(text="")

        self.entry_nombre.delete(0, tk.END)
        self.entry_precio.delete(0, tk.END)
        self.entry_stock.delete(0, tk.END)
        self.entry_categoria.set("")

        if self.tabla.selection():
            self.tabla.selection_remove(self.tabla.selection())

    def _leer_formulario(self):
        """
        Lee y valida el formulario. Retorna (nombre, precio, stock,
        categoria) o None si hay un error (y deja el mensaje en
        self.label_error, DENTRO de la ventana -- no en consola).
        """
        nombre = self.entry_nombre.get().strip()
        categoria = self.entry_categoria.get().strip()

        if nombre == "":
            self.label_error.config(text="El nombre no puede estar vacío")
            return None
        if categoria == "":
            self.label_error.config(text="La categoría no puede estar vacía")
            return None

        # Se aceptan precios con o sin puntos de miles ("149990" o
        # "149.990"), para que no choque con el formato en que se
        # MUESTRA el precio en el resto de la tienda.
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
        return nombre, precio, stock, categoria

    def _guardar(self):
        datos = self._leer_formulario()
        if datos is None:
            return
        nombre, precio, stock, categoria = datos

        if self.id_seleccionado is None:
            self.inventario.agregar_producto(nombre, precio, stock, categoria)
        else:
            self.inventario.actualizar_producto(self.id_seleccionado, nombre, precio, stock, categoria)

        self._refrescar_tabla()
        self._limpiar_formulario()

    def _eliminar(self):
        if self.id_seleccionado is None:
            self.label_error.config(text="Selecciona un producto de la tabla primero")
            return

        producto = self.inventario.buscar_por_id(self.id_seleccionado)
        if not messagebox.askyesno("Confirmar eliminación", f"¿Seguro que quieres eliminar '{producto.nombre}'?"):
            return

        self.inventario.eliminar_producto(self.id_seleccionado)
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
