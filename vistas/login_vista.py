"""
interfaz_login.py
Pantalla de inicio de sesión de RetroVault.
"""

import tkinter as tk
from estilos import *


class PantallaLogin(tk.Frame):
    """
    Pantalla de inicio de sesión.

    Parámetros:
        parent:            el widget contenedor (root u otro Frame)
        on_login_exitoso:  función que se llama al hacer click en
                            CONTINUAR. Recibe el usuario ingresado.
        on_crear_cuenta:   función que se llama al hacer click en
                            "CREAR CUENTA".
    """

    def __init__(self, parent, on_login_exitoso=None, on_crear_cuenta=None):
        super().__init__(parent, bg=BG_DARK)
        self.on_login_exitoso = on_login_exitoso
        self.on_crear_cuenta = on_crear_cuenta

        self._crear_barra_superior()
        self._crear_tarjeta_login()

    # BARRA SUPERIOR (logo + botones EXPLORAR / CARRITO)
    def _crear_barra_superior(self):
        barra = tk.Frame(self, bg=BG_DARK)
        barra.pack(fill="x", padx=40, pady=25)

        tk.Label(
            barra, text="RETRO VAULT", font=FUENTE_LOGO,
            bg=BG_DARK, fg=GREEN
        ).pack(side="left")

        botones = tk.Frame(barra, bg=BG_DARK)
        botones.pack(side="right")

        self._boton_secundario(
            botones, "EXPLORAR",
            on_click=lambda: print("Ir a explorar catálogo")
        ).pack(side="left", padx=5)

        self._boton_carrito(botones).pack(side="left", padx=5)

    def _boton_secundario(self, parent, texto, on_click=None):
        btn = tk.Label(
            parent, text=texto, font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, padx=15, pady=8, cursor="hand2"
        )
        if on_click:
            btn.bind("<Button-1>", lambda e: on_click())
        return btn

    def _boton_carrito(self, parent):

        contenedor = tk.Frame(parent, bg=GRAY_BTN, cursor="hand2")

        lbl = tk.Label(
            contenedor, text="CARRITO", font=FUENTE_NAV,
            bg=GRAY_BTN, fg=WHITE, padx=15, pady=8
        )
        lbl.pack(side="left")

        badge = tk.Label(contenedor, bg=RED_BADGE, width=2)
        badge.pack(side="left", padx=(0, 10))

        accion = lambda e: print("Ir al carrito")
        lbl.bind("<Button-1>", accion)
        badge.bind("<Button-1>", accion)
        return contenedor

    # TARJETA DE LOGIN 

    def _crear_tarjeta_login(self):
        contenedor = tk.Frame(self, bg=BG_DARK)
        contenedor.pack(expand=True)

        tarjeta = tk.Frame(contenedor, bg=WHITE, padx=60, pady=45)
        tarjeta.pack()

        tk.Label(
            tarjeta, text="Iniciar Sesión", font=FUENTE_TITULO,
            bg=WHITE, fg=BLACK
        ).pack(pady=(0, 35))

        # Campo usuario / correo (simulado)
        self.entry_usuario = self._campo_con_placeholder(
            tarjeta, "Usuario / Correo electronico", bg_campo=GRAY_INPUT
        )
        self.entry_usuario.pack(fill="x", ipady=10, pady=6)

        # Campo contraseña (oculta)
        self.entry_password = tk.Entry(
            tarjeta, show="•", font=FUENTE_BODY,
            bg=WHITE, fg=BLACK, relief="solid", bd=1, justify="center"
        )
        self.entry_password.pack(fill="x", ipady=10, pady=6)

        tk.Button(
            tarjeta, text="CONTINUAR", font=FUENTE_BOTON,
            bg=GREEN, fg=BLACK, activebackground=GREEN_HOVER,
            relief="flat", bd=0, cursor="hand2",
            command=self._manejar_login
        ).pack(fill="x", ipady=10, pady=(25, 15))

        self._separador_or(tarjeta)

        crear_cuenta = tk.Label(
            tarjeta, text="CREAR CUENTA",
            font=(FUENTE_BODY[0], 10, "underline"),
            bg=WHITE, fg=BLACK, cursor="hand2"
        )
        crear_cuenta.pack(pady=(15, 0))
        crear_cuenta.bind("<Button-1>", lambda e: self._manejar_crear_cuenta())

    def _separador_or(self, parent):
        fila = tk.Frame(parent, bg=WHITE)
        fila.pack(fill="x", pady=10)

        tk.Frame(fila, bg="#dddddd", height=1).pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )
        tk.Label(fila, text="or", bg=WHITE, fg=GRAY_TEXT, font=FUENTE_BODY).pack(side="left")
        tk.Frame(fila, bg="#dddddd", height=1).pack(
            side="left", fill="x", expand=True, padx=(10, 0)
        )

    def _campo_con_placeholder(self, parent, texto_placeholder, bg_campo):
        """
        Tkinter no tiene "placeholder" nativo en el Entry, así que lo
        simulamos: mostramos un texto gris que desaparece cuando el
        usuario hace click (focus) y vuelve a aparecer si el campo
        queda vacío al salir de él.
        """
        entry = tk.Entry(
            parent, font=FUENTE_BODY, bg=bg_campo, fg="#5a5a5a",
            relief="flat", justify="center"
        )
        entry.insert(0, texto_placeholder)

        def al_enfocar(event):
            if entry.get() == texto_placeholder:
                entry.delete(0, tk.END)
                entry.config(fg=BLACK)

        def al_desenfocar(event):
            if entry.get().strip() == "":
                entry.insert(0, texto_placeholder)
                entry.config(fg="#5a5a5a")

        entry.bind("<FocusIn>", al_enfocar)
        entry.bind("<FocusOut>", al_desenfocar)
        entry.placeholder = texto_placeholder  # para validar después
        return entry

    # ACCIONES

    def _manejar_login(self):
        usuario = self.entry_usuario.get()
        password = self.entry_password.get()

        if usuario == self.entry_usuario.placeholder or usuario.strip() == "":
            print("⚠️ Debes ingresar un usuario o correo")
            return
        if password.strip() == "":
            print("⚠️ Debes ingresar una contraseña")
            return

        print(f"✅ Intentando iniciar sesión con: {usuario}")
        if self.on_login_exitoso:
            self.on_login_exitoso(usuario)

    def _manejar_crear_cuenta(self):
        print("Ir a pantalla de crear cuenta")
        if self.on_crear_cuenta:
            self.on_crear_cuenta()


# PRUEBA INDEPENDIENTE (para que probemos solo esta pantalla)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("RetroVault - Iniciar Sesión")
    root.geometry("1000x650")
    root.configure(bg=BG_DARK)
    root.resizable(False, False)

    pantalla = PantallaLogin(
        root,
        on_login_exitoso=lambda usuario: print(f"Login OK -> {usuario}")
    )
    pantalla.pack(fill="both", expand=True)

    root.mainloop()
