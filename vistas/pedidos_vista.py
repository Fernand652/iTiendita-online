"""Panel de pedidos agrupado por estado para ADMIN y lista para CLIENTE."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, messagebox
try:
    from vistas.estilos import (
        BG_DARK, DARK_CARD, GREEN, WHITE, BLACK, GRAY_TEXT, GRAY_BTN,
        FUENTE_TITULO, FUENTE_NAV, FUENTE_BODY, FUENTE_BOTON,
    )
except ImportError:
    from estilos import (
        BG_DARK, DARK_CARD, GREEN, WHITE, BLACK, GRAY_TEXT, GRAY_BTN,
        FUENTE_TITULO, FUENTE_NAV, FUENTE_BODY, FUENTE_BOTON,
    )

from modelos.pedido import EstadoPedido
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


def _fmt_clp(valor):
    try:
        return "$" + f"{float(valor):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def _clave_orden(pedido):
    if not isinstance(pedido, dict):
        return ("", 0)
    fecha = str(pedido.get("fecha") or "")
    codigo = str(pedido.get("id_pedido") or "")
    numero = 0
    if codigo.startswith("P-"):
        try:
            numero = int(codigo[2:])
        except ValueError:
            numero = 0
    return (fecha, numero)


def _items_de(pedido):
    items = pedido.get("items") if isinstance(pedido, dict) else None
    return items if isinstance(items, list) else []


def _cantidad_items(pedido):
    total = 0
    for item in _items_de(pedido):
        if not isinstance(item, dict):
            continue
        try:
            total += int(item.get("cantidad") or 0)
        except (TypeError, ValueError):
            continue
    return total


class PantallaPedidos(tk.Frame):
    _es_pantalla_pedidos = True

    def __init__(self, parent, obtener_pedidos, modo="cliente", on_avanzar=None,
                 on_volver=None, on_cancelar=None):
        super().__init__(parent, bg=BG_DARK)
        self.obtener_pedidos = obtener_pedidos
        self.modo = "admin" if modo == "admin" else "cliente"
        self.on_avanzar = on_avanzar
        self.on_cancelar = on_cancelar
        self.on_volver = on_volver
        self._pedidos = []
        self._por_id = {}
        self._crear_ui()
        self.refrescar()

    def _crear_ui(self):
        barra = tk.Frame(self, bg=BG_DARK)
        barra.pack(fill="x", padx=24, pady=(18, 10))

        titulo = "PEDIDOS" if self.modo == "admin" else "MIS PEDIDOS"
        tk.Label(barra, text=titulo, font=FUENTE_TITULO,
                 bg=BG_DARK, fg=GREEN).pack(side="left")

        if self.on_volver:
            volver = tk.Label(barra, text="← VOLVER", font=FUENTE_NAV,
                              bg=GRAY_BTN, fg=WHITE, padx=14, pady=7,
                              cursor="hand2")
            volver.pack(side="right")
            volver.bind("<Button-1>", lambda _e: self.on_volver())
        else:
            cerrar = tk.Label(barra, text="CERRAR", font=FUENTE_NAV,
                              bg=GRAY_BTN, fg=WHITE, padx=14, pady=7,
                              cursor="hand2")
            cerrar.pack(side="right")
            cerrar.bind(
                "<Button-1>",
                lambda _e: self.winfo_toplevel().destroy(),
            )

        self.label_resumen = tk.Label(barra, text="", font=FUENTE_NAV,
                                      bg=BG_DARK, fg=GRAY_TEXT)
        self.label_resumen.pack(anchor="w", padx=24)

        acciones = tk.Frame(self, bg=BG_DARK)
        acciones.pack(fill="x", padx=24, pady=(8, 8))
        tk.Button(acciones, text="ACTUALIZAR", font=FUENTE_NAV,
                  bg=GRAY_BTN, fg=WHITE, relief="flat", bd=0,
                  cursor="hand2", command=self.refrescar).pack(
                      side="left", ipadx=8, ipady=4)
        self.label_mensaje = tk.Label(acciones, text="", font=FUENTE_BODY,
                                      bg=BG_DARK, fg=GRAY_TEXT)
        self.label_mensaje.pack(side="left", padx=12)

        if self.modo == "admin" and self.on_avanzar:
            self.btn_avanzar = tk.Button(
                acciones, text="AVANZAR ESTADO", font=FUENTE_NAV,
                bg=GREEN, fg=BLACK, relief="flat", bd=0, cursor="hand2",
                command=self._avanzar,
            )
            self.btn_avanzar.pack(side="right", padx=10, ipady=5)

        if self.modo == "admin" and self.on_cancelar:
            self.btn_cancelar = tk.Button(
                acciones, text="CANCELAR PEDIDO", font=FUENTE_NAV,
                bg="#c0392b", fg=WHITE, relief="flat", bd=0, cursor="hand2",
                command=self._cancelar,
            )
            self.btn_cancelar.pack(side="right", padx=10, ipady=5)

        cuerpo = tk.Frame(self, bg=BG_DARK)
        cuerpo.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except Exception:
            pass
        estilo.configure("Pedidos.Treeview", background=DARK_CARD,
                         foreground=WHITE, fieldbackground=DARK_CARD,
                         rowheight=26, font=FUENTE_BODY)
        estilo.configure("Pedidos.Treeview.Heading", background=GRAY_BTN,
                         foreground=WHITE, font=FUENTE_NAV)
        estilo.map("Pedidos.Treeview",
                   [("selected", [(GREEN, BLACK)])])

        columnas = ("id", "fecha", "cliente", "uds", "total", "estado")
        mostrar = "tree headings" if self.modo == "admin" else "headings"
        self.tabla = ttk.Treeview(cuerpo, columns=columnas,
                                  show=mostrar, height=12,
                                  style="Pedidos.Treeview")
        self.tabla.heading("#0", text="Estado")
        self.tabla.column("#0", width=190, anchor="w", stretch=False)
        encabezados = {
            "id": ("Pedido", 100, "center"),
            "fecha": ("Fecha", 150, "center"),
            "cliente": ("Cliente", 180, "w"),
            "uds": ("Uds.", 55, "center"),
            "total": ("Total", 100, "e"),
            "estado": ("Estado", 130, "center"),
        }
        for columna, (texto, ancho, ancla) in encabezados.items():
            self.tabla.heading(columna, text=texto)
            self.tabla.column(columna, width=ancho, anchor=ancla,
                              stretch=columna in ("cliente", "estado"))
        if self.modo == "cliente":
            self.tabla.heading("cliente", text="")
            self.tabla.column("cliente", width=0, minwidth=0, stretch=False)
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self._al_seleccionar)

        self.txt_detalle = tk.Text(cuerpo, height=7, font=FUENTE_BODY,
                                   bg=DARK_CARD, fg=WHITE, relief="flat",
                                   bd=6, wrap="word")
        self.txt_detalle.pack(fill="x", pady=(10, 0))
        self.txt_detalle.config(state="disabled")

    def refrescar(self):
        try:
            datos = self.obtener_pedidos() or []
        except Exception:
            datos = []
        self._pedidos = [p for p in datos if isinstance(p, dict)]
        self._pedidos.sort(key=_clave_orden, reverse=True)
        self._por_id = {
            str(p.get("id_pedido")): p
            for p in self._pedidos
            if p.get("id_pedido") is not None
        }

        seleccionado = self.tabla.selection()
        id_seleccionado = str(seleccionado[0]) if seleccionado else None

        for iid in self.tabla.get_children():
            self.tabla.delete(iid)

        if self.modo == "admin":
            grupos = {}
            for pedido in self._pedidos:
                estado = pedido.get("estado") or EstadoPedido.PENDIENTE
                if estado not in EstadoPedido.TODOS:
                    estado = EstadoPedido.PENDIENTE
                grupos.setdefault(estado, []).append(pedido)
            for estado in EstadoPedido.TODOS:
                pedidos = grupos.get(estado) or []
                if not pedidos:
                    continue
                padre = self.tabla.insert(
                    "", "end", iid=f"grupo::{estado}",
                    text=f"{estado} ({len(pedidos)})", open=True,
                )
                for pedido in pedidos:
                    self._insertar_fila(pedido, padre)
        else:
            for pedido in self._pedidos:
                self._insertar_fila(pedido)

        if id_seleccionado and self.tabla.exists(id_seleccionado):
            self.tabla.selection_set(id_seleccionado)
            pedido = self._por_id.get(id_seleccionado)
            self._mostrar_detalle(pedido)
            self._actualizar_boton(pedido)
        else:
            self._mostrar_detalle(None)
            self._actualizar_boton(None)

        pendientes = sum(1 for p in self._pedidos
                         if p.get("estado") == EstadoPedido.PENDIENTE)
        if self._pedidos:
            self.label_resumen.config(
                text=f"Pedidos: {len(self._pedidos)} | Pendientes: {pendientes}"
            )
        else:
            self.label_resumen.config(text="Sin pedidos registrados")

    def _insertar_fila(self, pedido, padre=""):
        id_pedido = str(pedido.get("id_pedido") or "")
        if not id_pedido:
            return
        fecha = str(pedido.get("fecha") or "").replace("T", " ")[:16]
        valores = (
            id_pedido,
            fecha,
            pedido.get("cliente") or "",
            _cantidad_items(pedido),
            _fmt_clp(pedido.get("total", 0)),
            pedido.get("estado") or EstadoPedido.PENDIENTE,
        )
        try:
            self.tabla.insert(padre, "end", iid=id_pedido, values=valores)
        except tk.TclError:
            pass

    def _al_seleccionar(self, _event):
        seleccion = self.tabla.selection()
        if not seleccion:
            self._mostrar_detalle(None)
            self._actualizar_boton(None)
            return
        id_pedido = str(seleccion[0])
        pedido = self._por_id.get(id_pedido)
        self._mostrar_detalle(pedido)
        self._actualizar_boton(pedido)

    def _siguiente_estado(self, pedido):
        if not isinstance(pedido, dict):
            return None
        estado = pedido.get("estado")
        if estado not in EstadoPedido.FLUJO:
            return None
        indice = EstadoPedido.FLUJO.index(estado)
        if indice == len(EstadoPedido.FLUJO) - 1:
            return None
        return EstadoPedido.FLUJO[indice + 1]

    def _actualizar_boton(self, pedido):
        if hasattr(self, "btn_avanzar"):
            siguiente = self._siguiente_estado(pedido)
            if siguiente is None:
                self.btn_avanzar.config(text="AVANZAR ESTADO", state="disabled")
            else:
                self.btn_avanzar.config(text=f"AVANZAR A {siguiente.upper()}",
                                        state="normal")
        if hasattr(self, "btn_cancelar"):
            estado = pedido.get("estado") if isinstance(pedido, dict) else None
            self.btn_cancelar.config(
                state="normal" if estado in EstadoPedido.CANCELABLES
                else "disabled"
            )

    def _avanzar(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            self._avisar("Selecciona un pedido", "error")
            return
        id_pedido = str(seleccion[0])
        pedido = self._por_id.get(id_pedido)
        if pedido is None:
            self._avisar("Selecciona un pedido", "error")
            return
        if self._siguiente_estado(pedido) is None:
            self._avisar("El pedido ya está entregado", "info")
            return
        resultado = self.on_avanzar(id_pedido)
        if isinstance(resultado, tuple):
            ok = bool(resultado[0])
            mensaje = resultado[1] if len(resultado) > 1 else ""
        else:
            ok, mensaje = bool(resultado), ""
        self._avisar(mensaje or ("Pedido actualizado" if ok
                                 else "No se pudo actualizar"),
                     "exito" if ok else "error")
        self.refrescar()
        if self.tabla.exists(id_pedido):
            self.tabla.selection_set(id_pedido)

    def _cancelar(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            self._avisar("Selecciona un pedido", "error")
            return
        id_pedido = str(seleccion[0])
        pedido = self._por_id.get(id_pedido)
        if pedido is None:
            self._avisar("Selecciona un pedido", "error")
            return
        if pedido.get("estado") not in EstadoPedido.CANCELABLES:
            self._avisar("Solo se puede cancelar antes de despachar", "error")
            return
        confirmado = messagebox.askyesno(
            "Cancelar pedido",
            f"¿Cancelar el pedido {id_pedido}?\n"
            "Se devolverá el stock de sus productos al inventario.",
            parent=self.winfo_toplevel(),
        )
        if not confirmado:
            return
        resultado = self.on_cancelar(id_pedido)
        if isinstance(resultado, tuple):
            ok = bool(resultado[0])
            mensaje = resultado[1] if len(resultado) > 1 else ""
        else:
            ok, mensaje = bool(resultado), ""
        self._avisar(mensaje or ("Pedido cancelado" if ok
                                 else "No se pudo cancelar"),
                     "exito" if ok else "error")
        self.refrescar()
        if self.tabla.exists(id_pedido):
            self.tabla.selection_set(id_pedido)

    def _avisar(self, mensaje, tipo):
        color = GREEN if tipo == "exito" else "#ff6b6b"
        if tipo == "info":
            color = GRAY_TEXT
        self.label_mensaje.config(text=mensaje, fg=color)
        _toast(self, mensaje, tipo=tipo)

    def _mostrar_detalle(self, pedido):
        self.txt_detalle.config(state="normal")
        self.txt_detalle.delete("1.0", tk.END)
        if not isinstance(pedido, dict):
            self.txt_detalle.insert(
                tk.END, "Selecciona un pedido para ver su detalle y estado.")
            self.txt_detalle.config(state="disabled")
            return
        lineas = [
            f"Pedido: {pedido.get('id_pedido', '?')}",
            f"Venta: {pedido.get('id_venta', '?')}",
            f"Cliente: {pedido.get('cliente') or 'Invitado'}",
            f"Fecha: {str(pedido.get('fecha') or '').replace('T', ' ')}",
            f"Estado: {pedido.get('estado') or EstadoPedido.PENDIENTE}",
            f"Total: {_fmt_clp(pedido.get('total', 0))}",
            "",
            "Productos:",
        ]
        items = _items_de(pedido)
        if not items:
            lineas.append("  (sin detalle)")
        for item in items:
            if not isinstance(item, dict):
                continue
            nombre = item.get("nombre") or f"Producto #{item.get('id', '?')}"
            try:
                cantidad = int(item.get("cantidad") or 0)
            except (TypeError, ValueError):
                cantidad = 0
            lineas.append(f"  - {nombre} x{cantidad}")
        self.txt_detalle.insert(tk.END, "\n".join(lineas))
        self.txt_detalle.config(state="disabled")


def abrir_ventana_pedidos(parent, obtener_pedidos, on_avanzar,
                          on_cancelar=None):
    try:
        root = parent.winfo_toplevel()
    except Exception:
        root = parent
    ventana = tk.Toplevel(root)
    ventana.title("Pedidos")
    ventana.geometry("980x620")
    ventana.configure(bg=BG_DARK)
    pantalla = PantallaPedidos(ventana, obtener_pedidos, modo="admin",
                               on_avanzar=on_avanzar,
                               on_cancelar=on_cancelar)
    pantalla.pack(fill="both", expand=True)
    ventana.pantalla = pantalla
    try:
        ventana.transient(root)
        ventana.grab_set()
    except Exception:
        pass
    return ventana
