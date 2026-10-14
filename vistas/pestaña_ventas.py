"""
pestaña_ventas.py
Pestaña de detalle de compras: lista TODAS las ventas de data/ventas.json
y muestra el detalle (ID, fecha, cliente, RUT, productos, subtotal, IVA, total).

Se conecta con las listas que ya existen:
- persistencia/gestor_ventas.cargar_ventas()
- persistencia/gestor_persistencia.RUTA_VENTAS_JSON + cargar_json
- reportes/reporte_carritos.buscar_ventas_por_clientes (filtro RUN/email)

Uso desde el admin:
    from vistas.pestaña_ventas import abrir_ventana_ventas
    abrir_ventana_ventas(self)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk

try:
    from vistas.estilos import (
        BG_DARK, DARK_CARD, GREEN, WHITE, BLACK,
        GRAY_TEXT, GRAY_BTN, FUENTE_TITULO, FUENTE_NAV, FUENTE_BODY,
        FUENTE_BOTON,
    )
except ImportError:
    try:
        from estilos import (
            BG_DARK, DARK_CARD, GREEN, WHITE, BLACK,
            GRAY_TEXT, GRAY_BTN, FUENTE_TITULO, FUENTE_NAV, FUENTE_BODY,
            FUENTE_BOTON,
        )
    except ImportError:
        BG_DARK, DARK_CARD = "#0b0f0b", "#171b17"
        GREEN = "#00ff66"
        WHITE, BLACK = "#ffffff", "#1a1a1a"
        GRAY_TEXT, GRAY_BTN = "#9a9a9a", "#2b2b2b"
        FUENTE_TITULO = ("Arial", 20, "bold")
        FUENTE_NAV = ("Arial", 10, "bold")
        FUENTE_BODY = ("Arial", 10)
        FUENTE_BOTON = ("Arial", 11, "bold")


def _cargar_todas_ventas():
    """Lee la lista completa desde las listas que ya hay en el proyecto."""
    try:
        from persistencia.gestor_ventas import cargar_ventas as _cargar
        ventas = _cargar() or []
        if isinstance(ventas, list):
            return ventas
    except Exception:
        pass
    try:
        from gestor_ventas import cargar_ventas as _cargar2
        ventas = _cargar2() or []
        if isinstance(ventas, list):
            return ventas
    except Exception:
        pass
    try:
        from persistencia.gestor_persistencia import RUTA_VENTAS_JSON, cargar_json
        return cargar_json(str(RUTA_VENTAS_JSON), default=[]) or []
    except Exception:
        pass
    try:
        from gestor_persistencia import RUTA_VENTAS_JSON as _R, cargar_json as _c
        return _c(str(_R), default=[]) or []
    except Exception:
        return []


def _cliente_de(v):
    """Solo el email/usuario (no mezcla el RUT)."""
    if not isinstance(v, dict):
        return "?"
    val = v.get("cliente", "")
    if isinstance(val, str) and val.strip():
        return val.strip()
    return "?"


def _run_de(v):
    """RUT de la venta: campo 'run' nuevo o 'run_cliente' legacy. '' = sin RUT."""
    if not isinstance(v, dict):
        return ""
    for k in ("run", "run_cliente"):
        val = v.get(k, "")
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _items_de(v):
    """Compat: ventas nuevas usan 'items', legacy 'productos'."""
    if not isinstance(v, dict):
        return []
    items = v.get("items", []) or v.get("productos", []) or []
    return items if isinstance(items, list) else []


def _fmt_clp(valor):
    try:
        return f"${float(valor):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


class PestanaVentas(tk.Frame):
    """Frame reutilizable: maestra (todas las ventas) + detalle."""

    def __init__(self, parent, ventas=None):
        super().__init__(parent, bg=BG_DARK)
        self._todas = list(ventas) if isinstance(ventas, list) else _cargar_todas_ventas()
        self._vista = list(self._todas)
        self._crear_ui()
        self.refrescar()

    def _crear_ui(self):
        tk.Label(
            self, text="DETALLE DE COMPRAS", font=FUENTE_TITULO,
            bg=BG_DARK, fg=GREEN,
        ).pack(anchor="w", padx=12, pady=(12, 4))

        barra = tk.Frame(self, bg=BG_DARK)
        barra.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(barra, text="RUN/email:", font=FUENTE_NAV, bg=BG_DARK, fg=GRAY_TEXT).pack(side="left")
        self.entry_filtro = tk.Entry(barra, font=FUENTE_BODY, width=24, relief="flat", bd=4)
        self.entry_filtro.pack(side="left", padx=(6, 6))
        self.entry_filtro.bind("<Return>", lambda e: self.buscar())
        tk.Button(
            barra, text="Buscar", font=FUENTE_NAV, bg=GRAY_BTN, fg=WHITE,
            relief="flat", bd=0, cursor="hand2", command=self.buscar,
        ).pack(side="left", ipadx=8, ipady=4)
        tk.Button(
            barra, text="Mostrar todas", font=FUENTE_NAV, bg=GRAY_BTN, fg=WHITE,
            relief="flat", bd=0, cursor="hand2", command=self.mostrar_todas,
        ).pack(side="left", padx=(6, 0), ipadx=8, ipady=4)
        tk.Button(
            barra, text="Actualizar", font=FUENTE_NAV, bg=GREEN, fg=BLACK,
            relief="flat", bd=0, cursor="hand2", command=self.actualizar,
        ).pack(side="right", ipadx=8, ipady=4)

        self.label_resumen = tk.Label(
            self, text="", font=FUENTE_NAV, bg=BG_DARK, fg=GRAY_TEXT,
        )
        self.label_resumen.pack(anchor="w", padx=12)

        medio = tk.Frame(self, bg=BG_DARK)
        medio.pack(fill="both", expand=True, padx=12, pady=8)

        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except Exception:
            pass
        estilo.configure("Treeview", background=DARK_CARD, foreground=WHITE,
                         fieldbackground=DARK_CARD, rowheight=26, font=FUENTE_BODY)
        estilo.configure("Treeview.Heading", background=GRAY_BTN, foreground=WHITE, font=FUENTE_NAV)

        cols = ("id", "fecha", "cliente", "run", "uds", "total")
        self.tabla = ttk.Treeview(medio, columns=cols, show="headings", height=10)
        self.tabla.heading("id", text="ID")
        self.tabla.heading("fecha", text="Fecha")
        self.tabla.heading("cliente", text="Cliente")
        self.tabla.heading("run", text="RUT")
        self.tabla.heading("uds", text="Uds.")
        self.tabla.heading("total", text="Total")
        self.tabla.column("id", width=50, anchor="center")
        self.tabla.column("fecha", width=140, anchor="center")
        self.tabla.column("cliente", width=150)
        self.tabla.column("run", width=110, anchor="center")
        self.tabla.column("uds", width=55, anchor="center")
        self.tabla.column("total", width=100, anchor="e")
        self.tabla.pack(side="left", fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self._al_seleccionar)

        self.txt_detalle = tk.Text(
            medio, width=38, height=12, font=FUENTE_BODY,
            bg=DARK_CARD, fg=WHITE, relief="flat", bd=6, wrap="word",
        )
        self.txt_detalle.pack(side="right", fill="y", padx=(10, 0))
        self.txt_detalle.config(state="disabled")

    def actualizar(self):
        """Recarga la lista desde data/ventas.json y repinta."""
        self._todas = _cargar_todas_ventas()
        self._vista = list(self._todas)
        self.entry_filtro.delete(0, tk.END)
        self.refrescar()

    def mostrar_todas(self):
        self._vista = list(self._todas)
        self.refrescar()

    def buscar(self):
        """Filtra por RUN/email."""
        texto = (self.entry_filtro.get() or "").strip().lower()
        if not texto:
            self.mostrar_todas()
            return
        try:
            from reportes.reporte_carritos import buscar_ventas_por_clientes
            self._vista = buscar_ventas_por_clientes(self._todas, texto)
        except Exception:
            self._vista = [
                v for v in self._todas
                if texto in str(v.get("cliente", "")).lower()
                or texto in str(v.get("run", "")).lower()
                or texto in str(v.get("run_cliente", "")).lower()
            ]
        self._vista = sorted(self._vista, key=lambda v: str(v.get("fecha", "")))
        self.refrescar()

    def refrescar(self):
        for iid in self.tabla.get_children():
            self.tabla.delete(iid)
        total_acum = 0.0
        for v in self._vista:
            try:
                vid = v.get("id_venta", "?")
                fecha = v.get("fecha", "Sin fecha")
                uds = sum(int(i.get("cantidad", 0) or 0) for i in _items_de(v))
                total = float(v.get("total", 0) or 0)
                run = _run_de(v) or "—"
            except (TypeError, ValueError, AttributeError):
                continue
            total_acum += total
            self.tabla.insert("", "end", iid=f"v-{vid}",
                              values=(vid, fecha, _cliente_de(v), run, uds, _fmt_clp(total)))
        n = len(self._vista)
        self.label_resumen.config(
            text=f"Ventas: {n} | Monto total: {_fmt_clp(total_acum)}" if n else "Sin ventas registradas"
        )
        self._mostrar_detalle(None)

    def _al_seleccionar(self, _event=None):
        sel = self.tabla.selection()
        if not sel:
            return
        iid = sel[0]
        venta = next((v for v in self._vista if f"v-{v.get('id_venta', '?')}" == iid), None)
        self._mostrar_detalle(venta)

    def _mostrar_detalle(self, v):
        self.txt_detalle.config(state="normal")
        self.txt_detalle.delete("1.0", tk.END)
        if not isinstance(v, dict):
            self.txt_detalle.insert(tk.END, "Selecciona una venta para ver cliente, RUT, productos, subtotal, IVA y total.")
        else:
            try:
                subtotal = float(v.get("subtotal", 0) or 0)
            except (TypeError, ValueError):
                subtotal = 0.0
            try:
                iva = float(v.get("iva", 0) or 0)
            except (TypeError, ValueError):
                iva = 0.0
            try:
                total = float(v.get("total", 0) or 0)
            except (TypeError, ValueError):
                total = 0.0
            if not subtotal and total:
                subtotal = total / 1.19
            if not iva and total:
                iva = total - subtotal
            lineas = [
                f"ID venta: {v.get('id_venta', '?')}",
                f"Fecha: {v.get('fecha', 'Sin fecha')}",
                f"Cliente: {_cliente_de(v)}",
                f"RUT: {_run_de(v) or '— (sin RUT)'}",
                "",
                "Productos:",
            ]
            items = _items_de(v)
            if not items:
                lineas.append("  (sin detalle)")
            for it in items:
                nom = it.get("nombre", "Producto")
                try:
                    cant = int(it.get("cantidad", 1) or 1)
                except (TypeError, ValueError):
                    cant = 1
                try:
                    sub = float(it.get("subtotal", float(it.get("precio", 0) or 0) * cant))
                except (TypeError, ValueError):
                    sub = 0.0
                lineas.append(f"  - {nom} x{cant}  {_fmt_clp(sub)}")
            lineas += ["", f"Subtotal: {_fmt_clp(subtotal)}",
                       f"IVA (19%): {_fmt_clp(iva)}",
                       f"TOTAL: {_fmt_clp(total)}"]
            self.txt_detalle.insert(tk.END, "\n".join(lineas))
        self.txt_detalle.config(state="disabled")


def abrir_ventana_ventas(parent):
    """Abre la lista completa en un Toplevel (la usa el ADMIN)."""
    try:
        root = parent.winfo_toplevel()
    except Exception:
        root = parent
    win = tk.Toplevel(root)
    win.title("Todas las ventas - Detalle de compras")
    win.geometry("900x560")
    try:
        win.configure(bg=BG_DARK)
    except Exception:
        pass
    PestanaVentas(win).pack(fill="both", expand=True)
    try:
        win.transient(root)
        win.grab_set()
    except Exception:
        pass
    return win


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Tiendita - Ventas")
    root.geometry("900x560")
    PestanaVentas(root).pack(fill="both", expand=True)
    root.mainloop()
