"""
interfaz_crear_cuenta.py
Pantalla de registro de nuevos usuarios en RetroVault.
"""

import tkinter as tk
try:
    from vistas.estilos import *
except ImportError:  # permite ejecutar este archivo directamente
    from estilos import *


class PantallaCrearCuenta(tk.Frame):
    """
    Pantalla de registro de cuenta.

    Parámetros:
        parent:             Widget contenedor (root u otro Frame).
        on_registro_exitoso: Función llamada al completar el registro. Recibe un dict con los datos.
        on_ir_a_login:      Función llamada al pulsar en 'INICIAR SESIÓN'.
    """

    def __init__(self, parent, on_registro_exitoso=None, on_ir_a_login=None):
        super().__init__(parent, bg=BG_DARK)
        self.on_registro_exitoso = on_registro_exitoso
        self.on_ir_a_login = on_ir_a_login

        self._crear_barra_superior()
        self._crear_tarjeta_registro()

    # ============================================================
    # BARRA SUPERIOR
    # ============================================================
    def _crear_barra_superior(self):
        barra = tk.Frame(self, bg=BG_DARK)
        barra.pack(fill="x", padx=40, pady=20)

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

    # ============================================================
    # TARJETA DE REGISTRO
    # ============================================================
    def _crear_tarjeta_registro(self):
        contenedor = tk.Frame(self, bg=BG_DARK)
        contenedor.pack(expand=True, pady=10)

        tarjeta = tk.Frame(contenedor, bg=WHITE, padx=50, pady=30)
        tarjeta.pack()

        tk.Label(
            tarjeta, text="Crear Cuenta", font=FUENTE_TITULO,
            bg=WHITE, fg=BLACK
        ).pack(pady=(0, 20))

        # Campos de texto con placeholder
        self.entry_nombres = self._campo_con_placeholder(tarjeta, "Nombres", bg_campo=GRAY_INPUT)
        self.entry_nombres.pack(fill="x", ipady=8, pady=4)

        self.entry_apellidos = self._campo_con_placeholder(tarjeta, "Apellidos", bg_campo=GRAY_INPUT)
        self.entry_apellidos.pack(fill="x", ipady=8, pady=4)

        self.entry_pais = self._campo_con_placeholder(tarjeta, "País", bg_campo=GRAY_INPUT)
        self.entry_pais.pack(fill="x", ipady=8, pady=4)

        self.entry_correo = self._campo_con_placeholder(tarjeta, "Correo electrónico", bg_campo=GRAY_INPUT)
        self.entry_correo.pack(fill="x", ipady=8, pady=4)

        # Campos de contraseña
        self.entry_password = tk.Entry(
            tarjeta, show="•", font=FUENTE_BODY,
            bg=WHITE, fg=BLACK, relief="solid", bd=1, justify="center"
        )
        self.entry_password.pack(fill="x", ipady=8, pady=4)
        self._asignar_ayuda_password(self.entry_password, "Crear contraseña")

        self.entry_confirmar_password = tk.Entry(
            tarjeta, show="•", font=FUENTE_BODY,
            bg=WHITE, fg=BLACK, relief="solid", bd=1, justify="center"
        )
        self.entry_confirmar_password.pack(fill="x", ipady=8, pady=4)
        self._asignar_ayuda_password(self.entry_confirmar_password, "Confirmar contraseña")

        # Botón Registrar
        tk.Button(
            tarjeta, text="REGISTRARME", font=FUENTE_BOTON,
            bg=GREEN, fg=BLACK, activebackground=GREEN_HOVER,
            relief="flat", bd=0, cursor="hand2",
            command=self._manejar_registro
        ).pack(fill="x", ipady=9, pady=(20, 10))

        self._separador_or(tarjeta)

        # Enlace a Iniciar Sesión
        iniciar_sesion = tk.Label(
            tarjeta, text="¿YA TIENES CUENTA? INICIAR SESIÓN",
            font=(FUENTE_BODY[0], 9, "underline"),
            bg=WHITE, fg=BLACK, cursor="hand2"
        )
        iniciar_sesion.pack(pady=(10, 0))
        iniciar_sesion.bind("<Button-1>", lambda e: self._manejar_ir_a_login())

    def _separador_or(self, parent):
        fila = tk.Frame(parent, bg=WHITE)
        fila.pack(fill="x", pady=8)

        tk.Frame(fila, bg="#dddddd", height=1).pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )
        tk.Label(fila, text="or", bg=WHITE, fg=GRAY_TEXT, font=FUENTE_BODY).pack(side="left")
        tk.Frame(fila, bg="#dddddd", height=1).pack(
            side="left", fill="x", expand=True, padx=(10, 0)
        )

    def _campo_con_placeholder(self, parent, texto_placeholder, bg_campo):
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
        entry.placeholder = texto_placeholder
        return entry

    def _asignar_ayuda_password(self, entry, texto_placeholder):
        """Muestra texto en claro si está vacío y enmascara con '•' al escribir."""
        entry.config(show="", fg="#5a5a5a")
        entry.insert(0, texto_placeholder)

        def al_enfocar(event):
            if entry.get() == texto_placeholder:
                entry.delete(0, tk.END)
                entry.config(show="•", fg=BLACK)

        def al_desenfocar(event):
            if entry.get().strip() == "":
                entry.config(show="", fg="#5a5a5a")
                entry.insert(0, texto_placeholder)

        entry.bind("<FocusIn>", al_enfocar)
        entry.bind("<FocusOut>", al_desenfocar)
        entry.placeholder = texto_placeholder

    # ============================================================
    # VALIDACIONES Y EVENTOS
    # ============================================================
    def _manejar_registro(self):
        nombres = self.entry_nombres.get().strip()
        apellidos = self.entry_apellidos.get().strip()
        pais = self.entry_pais.get().strip()
        correo = self.entry_correo.get().strip()
        password = self.entry_password.get().strip()
        confirmar = self.entry_confirmar_password.get().strip()

        # Validación de campos obligatorios
        if nombres == self.entry_nombres.placeholder or not nombres:
            print("⚠️ Debes ingresar tus nombres")
            return
        if apellidos == self.entry_apellidos.placeholder or not apellidos:
            print("⚠️ Debes ingresar tus apellidos")
            return
        if pais == self.entry_pais.placeholder or not pais:
            print("⚠️ Debes ingresar tu país")
            return
        if correo == self.entry_correo.placeholder or not correo:
            print("⚠️ Debes ingresar un correo electrónico")
            return
        if password == self.entry_password.placeholder or not password:
            print("⚠️ Debes ingresar una contraseña")
            return
        if confirmar == self.entry_confirmar_password.placeholder or not confirmar:
            print("⚠️ Debes confirmar tu contraseña")
            return

        # Validación de coincidencia de contraseñas
        if password != confirmar:
            print("⚠️ Las contraseñas no coinciden")
            return

        datos_usuario = {
            "nombres": nombres,
            "apellidos": apellidos,
            "pais": pais,
            "correo": correo,
            "password": password
        }

        print(f"✅ Cuenta creada exitosamente para: {nombres} {apellidos} ({correo})")
        if self.on_registro_exitoso:
            self.on_registro_exitoso(datos_usuario)

    def _manejar_ir_a_login(self):
        print("Volver a pantalla de inicio de sesión")
        if self.on_ir_a_login:
            self.on_ir_a_login()


# ============================================================
# PRUEBA INDEPENDIENTE
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("RetroVault - Crear Cuenta")
    root.geometry("1000x680")
    root.configure(bg=BG_DARK)
    root.resizable(False, False)

    pantalla = PantallaCrearCuenta(
        root,
        on_registro_exitoso=lambda datos: print(f"Usuario registrado -> {datos}"),
        on_ir_a_login=lambda: print("Navegar a pantalla de Login")
    )
    pantalla.pack(fill="both", expand=True)

    root.mainloop()