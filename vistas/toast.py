"""
toast.py
Toast flotante reutilizable para mensajes de error/éxito/info.

- Aparece arriba a la derecha de la ventana, se queda 2s (error)
  o 1.5s (éxito/info) y sale con fade + deslizamiento.
- Reemplaza los messagebox de flujo (menos clics); los labels
  inline se mantienen como respaldo persistente.
- Uso:
    from vistas.toast import mostrar_toast
    mostrar_toast(self, "Stock máximo: 4", tipo="error")
    mostrar_toast(self, "Añadido: Mario", tipo="exito")
"""

import tkinter as tk

try:
    from vistas.estilos import (
        GREEN, RED_BADGE, GRAY_BTN, WHITE, BLACK,
        FUENTE_BOTON, DARK_CARD,
    )
except ImportError:
    try:
        from estilos import (
            GREEN, RED_BADGE, GRAY_BTN, WHITE, BLACK,
            FUENTE_BOTON, DARK_CARD,
        )
    except ImportError:  # valores de respaldo
        GREEN = "#00ff66"
        RED_BADGE = "#e63946"
        GRAY_BTN = "#2b2b2b"
        WHITE = "#ffffff"
        BLACK = "#1a1a1a"
        DARK_CARD = "#171b17"
        FUENTE_BOTON = ("Arial", 11, "bold")

DURACION = {
    "error": 2000,
    "exito": 1500,
    "info": 1500,
}

COLORES = {
    "error": (RED_BADGE, WHITE),
    "exito": (GREEN, BLACK),
    "info": (GRAY_BTN, WHITE),
}

_MARGEN_X = 20
_MARGEN_Y = 20


def _raiz_de(widget):
    """Devuelve la ventana Tk raíz dueña de `widget` (o el propio widget)."""
    try:
        top = widget.winfo_toplevel()
        return top
    except Exception:
        return widget


def _cerrar_anterior(root):
    anterior = getattr(root, "_toast_actual", None)
    if anterior is not None:
        try:
            if anterior.winfo_exists():
                anterior.destroy()
        except Exception:
            pass
    root._toast_actual = None


def mostrar_toast(parent, mensaje, tipo="error", duracion_ms=None):
    """
    Muestra un texto flotante arriba a la derecha.

    parent:      cualquier widget de la pantalla actual (Frame/Pantalla).
    mensaje:     texto a mostrar.
    tipo:        "error" | "exito" | "info".
    duracion_ms: override manual; por defecto error=2000, exito/info=1500.
    """
    if tipo not in COLORES:
        tipo = "info"
    if duracion_ms is None:
        duracion_ms = DURACION[tipo]

    try:
        root = _raiz_de(parent)
    except Exception:
        return None

    try:
        _cerrar_anterior(root)
    except Exception:
        pass

    bg, fg = COLORES[tipo]

    try:
        toast = tk.Toplevel(root)
    except Exception:
        return None

    toast.overrideredirect(True)
    try:
        toast.attributes("-topmost", True)
    except Exception:
        pass
    try:
        toast.transient(root)
    except Exception:
        pass

    # Contenido con look "bonito": tarjeta de color + borde sutil
    borde = tk.Frame(toast, bg=DARK_CARD, padx=1, pady=1)
    borde.pack()
    lbl = tk.Label(
        borde, text=mensaje, font=FUENTE_BOTON,
        bg=bg, fg=fg, padx=18, pady=12, wraplength=320, justify="left",
    )
    lbl.pack()

    # Posición arriba-derecha de la ventana raíz
    try:
        toast.update_idletasks()
        root.update_idletasks()
        rx = root.winfo_x()
        ry = root.winfo_y()
        rw = root.winfo_width()
        # Si la raíz aún no está mapeada (w=1), estimar 1100 de ancho
        if rw <= 1:
            rw = 1100
        tw = toast.winfo_reqwidth()
        x = rx + rw - tw - _MARGEN_X
        y_base = ry + _MARGEN_Y
        toast.geometry(f"+{max(x, rx)}+{y_base}")
    except Exception:
        y_base = None

    try:
        root._toast_actual = toast
    except Exception:
        pass

    # ---- animación: fade-in + desliz, hold, fade-out + desliz ----
    alpha_ok = True
    try:
        toast.attributes("-alpha", 0.0)
    except Exception:
        alpha_ok = False

    pasos_in = 10
    pasos_out = 10

    def _mover(y):
        try:
            if toast.winfo_exists():
                g = toast.geometry().split("+")
                # geometry() -> "WxH+X+Y"
                if len(g) == 3:
                    toast.geometry(f"+{g[1]}+{y}")
        except Exception:
            pass

    def _fade_in(paso=0):
        try:
            if not toast.winfo_exists():
                return
            if alpha_ok:
                toast.attributes("-alpha", (paso + 1) / pasos_in)
            if y_base is not None:
                _mover(y_base - 10 + int(10 * (paso + 1) / pasos_in))
            if paso + 1 < pasos_in:
                toast.after(15, lambda: _fade_in(paso + 1))
            else:
                toast.after(duracion_ms, _fade_out)
        except Exception:
            pass

    def _fade_out(paso=0):
        try:
            if not toast.winfo_exists():
                return
            if alpha_ok:
                toast.attributes("-alpha", 1.0 - (paso + 1) / pasos_out)
            if y_base is not None:
                _mover(y_base - int(6 * (paso + 1) / pasos_out))
            if paso + 1 < pasos_out:
                toast.after(25, lambda: _fade_out(paso + 1))
            else:
                try:
                    toast.destroy()
                except Exception:
                    pass
                try:
                    if getattr(root, "_toast_actual", None) == toast:
                        root._toast_actual = None
                except Exception:
                    pass
        except Exception:
            pass

    try:
        _fade_in()
    except Exception:
        # Sin animación: mostrar fijo y destruir tras la duración
        try:
            toast.after(duracion_ms, toast.destroy)
        except Exception:
            pass

    return toast


def toast_error(parent, mensaje, duracion_ms=2000):
    return mostrar_toast(parent, mensaje, tipo="error", duracion_ms=duracion_ms)


def toast_exito(parent, mensaje, duracion_ms=1500):
    return mostrar_toast(parent, mensaje, tipo="exito", duracion_ms=duracion_ms)


def toast_info(parent, mensaje, duracion_ms=1500):
    return mostrar_toast(parent, mensaje, tipo="info", duracion_ms=duracion_ms)


# Prueba independiente: abre una ventana y dispara 3 toasts seguidos.
if __name__ == "__main__":
    _root = tk.Tk()
    _root.title("Toast demo")
    _root.geometry("600x400")

    def _demo():
        mostrar_toast(_root, "Error de ejemplo (2s)", tipo="error")
        _root.after(2600, lambda: mostrar_toast(_root, "Éxito de ejemplo (1.5s)", tipo="exito"))
        _root.after(4800, lambda: mostrar_toast(_root, "Info de ejemplo (1.5s)", tipo="info"))

    tk.Button(_root, text="Probar toasts", command=_demo).pack(pady=40)
    _root.after(500, _demo)
    _root.mainloop()
