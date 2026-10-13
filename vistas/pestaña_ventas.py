import tkinter as tk 
from tkinter import ttk,messagebox
class TiendaTerminalApp:
  def init(self,root):
    self.root=root
    self.root.title("tiendita_ventas")
    self.root.geometry("600x500")
    style.configure("TNotebook", background="#000000", borderwidth=0)
        style.configure("TNotebook.Tab", background="#111111", foreground="#00FF00", padding=[12, 8], font=("Consolas", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#002200")], foreground=[("selected", "#00FF00")])

        # Creación del contenedor de pestañas (Notebook)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Pestaña 1: Caja / Ventas
        self.tab_venta = tk.Frame(self.notebook, bg="#000000")
        self.notebook.add(self.tab_venta)
        self.crear_pestana_venta(self.tab_venta)

        # Pestaña 2: Inventario / Info (Ejemplo de otra pestaña)
        self.tab_info = tk.Frame(self.notebook, bg="#000000")
        self.notebook.add(self.tab_info)
        self.crear_pestana_info(self.tab_info)

    def crear_pestana_venta(self, parent):
        # Título de la sección
        lbl_titulo = tk.Label(parent, text="TERMINAL DE VENTAS", fg="#00FF00", bg="#000000", font=("Consolas", 14, "bold"))
        lbl_titulo.pack(pady=10)
        # Marco para los campos de entrada (Cliente)
        frame_cliente = tk.LabelFrame(parent, text=" Datos del Cliente ", fg="#00FF00", bg="#000000", font=("Consolas", 10, "bold"), bd=2, relief="groove")
        # Correo
        lbl_correo = tk.Label(frame_cliente, text="Correo:", fg="#00FF00", bg="#000000", font=("Consolas", 10))
        lbl_correo.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.entry_correo = tk.Entry(frame_cliente, bg="#111111", fg="#00FF00", insertbackground="#00FF00", font=("Consolas", 10), relief="solid", bd=1)
        self.entry_correo.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        # RUT
        lbl_rut = tk.Label(frame_cliente, text="RUT:", fg="#00FF00", bg="#000000", font=("Consolas", 10))
        lbl_rut.grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.entry_rut = tk.Entry(frame_cliente, bg="#111111", fg="#00FF00", insertbackground="#00FF00", font=("Consolas", 10), relief="solid", bd=1)
        self.entry_rut.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        frame_cliente.columnconfigure(1, weight=1)
        # Marco para los cálculos y montos
        frame_totales = tk.LabelFrame(parent, text=" Resumen de Compra ", fg="#00FF00", bg="#000000", font=("Consolas", 10, "bold"), bd=2, relief="groove")
        frame_totales.pack(fill="x", padx=20, pady=10)

        # Subtotal (Base)
        lbl_sub = tk.Label(frame_totales, text="Subtotal neto ($):", fg="#00FF00", bg="#000000", font=("Consolas", 10))
        lbl_sub.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.entry_subtotal = tk.Entry(frame_totales, bg="#111111", fg="#00FF00", insertbackground="#00FF00", font=("Consolas", 10), relief="solid", bd=1)
        self.entry_subtotal.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        self.entry_subtotal.insert(0, "10000")
