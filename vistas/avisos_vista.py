"""Bandeja de avisos de la sesión, actualizada sin bloquear Tkinter."""
import tkinter as tk
from tkinter import scrolledtext


def abrir_avisos(parent, obtener):
    ventana = tk.Toplevel(parent)
    ventana.title("Mis avisos")
    ventana.geometry("700x450")
    ventana.configure(bg="#0b100c")
    tk.Label(ventana, text="MIS AVISOS", font=("Arial", 20, "bold"),
             bg="#0b100c", fg="#00ff66").pack(anchor="w", padx=20, pady=15)
    tk.Label(ventana, text="Reposiciones y rebajas de tus productos guardados",
             bg="#0b100c", fg="white").pack(anchor="w", padx=20)
    texto = scrolledtext.ScrolledText(ventana, wrap="word", font=("Arial", 12),
                                     bg="#181d18", fg="white", padx=15, pady=15)
    texto.pack(fill="both", expand=True, padx=20, pady=20)
    anterior = None
    def refrescar():
        nonlocal anterior
        if not ventana.winfo_exists():
            return
        avisos = obtener()
        contenido = "\n\n".join(f"{a.get('fecha', '').replace('T', ' ')}\n{a.get('mensaje', '')}"
                                  for a in reversed(avisos)) or "Todavía no tienes avisos."
        if contenido != anterior:
            texto.configure(state="normal")
            texto.delete("1.0", "end")
            texto.insert("end", contenido)
            texto.configure(state="disabled")
            anterior = contenido
        ventana.after(500, refrescar)
    refrescar()
    return ventana
