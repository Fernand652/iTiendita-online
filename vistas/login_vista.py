"""
login_vista.py
Pantalla de inicio de sesión de RetroVault conectada a usuarios.json.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk

# Importación adaptativa de estilos segun la estructura del proyecto
try:
    from vistas.estilos import *
except ImportError:
    try:
        from estilos import *
    except ImportError:
        # Colores y fuentes de respaldo si no se encuentra estilos.py
        BG_DARK = "#0d1117"
        WHITE = "#ffffff"
        BLACK = "#000000"
        GRAY_BTN = "#21262d"
        GRAY_INPUT = "#f0f0f0"
        GRAY_TEXT = "#8b949e"
        GREEN = "#2ea44f"
        GREEN_HOVER = "#2c974b"
        RED_BADGE = "#da3633"
        FUENTE_LOGO = ("Arial", 16, "bold")
        FUENTE_TITULO = ("Arial", 18, "bold")
        FUENTE_NAV = ("Arial", 10, "bold")
        FUENTE_BODY = ("Arial", 10)
        FUENTE_BOTON = ("Arial", 10, "bold")

try:
    from modelos.usuario import GestorUsuarios
except ImportError:
    try:
        from usuario import GestorUsuarios
    except ImportError:
        GestorUsuarios = None

try:
    from vistas.toast import mostrar_toast
except ImportError:
    try:
        from toast import mostrar_toast
    except ImportError:
        mostrar_toast = None


def _toast(parent, mensaje, tipo="error"):
    """Toast flotante arriba-derecha; silencioso si toast no disponible."""
    if mostrar_toast is None:
        return
    try:
        mostrar_toast(parent, mensaje, tipo=tipo)
    except Exception:
        pass


class PantallaLogin(tk.Frame):
    def __init__(self, parent, on_login_exitoso=None, on_crear_cuenta=None, gestor_usuarios=None, on_ir_explorar=None, on_ver_carrito=None):
        super().__init__(parent, bg=BG_DARK)
        self.on_login_exitoso = on_login_exitoso
        self.on_crear_cuenta = on_crear_cuenta
        self.on_ir_explorar = on_ir_explorar
        self.on_ver_carrito = on_ver_carrito
        if gestor_usuarios is not None:
            self.gestor_usuarios = gestor_usuarios
        elif GestorUsuarios is not None:
            self.gestor_usuarios = GestorUsuarios()
        else:
            raise ImportError("No se pudo importar GestorUsuarios desde modelos.usuario")

        self._crear_barra_superior()
        self._crear_tarjeta_login()

    def _crear_barra_superior(self):
        # Sin acceso invitado: solo logo. Para ver el catálogo o el
        # carrito hay que iniciar sesión primero.
        barra = tk.Frame(self, bg=BG_DARK)
        barra.pack(fill="x", padx=40, pady=25)

        tk.Label(
            barra, text="RETRO VAULT", font=FUENTE_LOGO,
            bg=BG_DARK, fg=GREEN
        ).pack(side="left")

    def _ir_explorar(self):
        # Botón eliminado de la barra; se mantiene por compatibilidad:
        # sin sesión siempre pide iniciar sesión.
        self.label_info.config(text="Inicia sesión para continuar")
        _toast(self, "Inicia sesión para continuar", tipo="info")

    def _ir_carrito(self):
        self.label_info.config(text="Inicia sesión para continuar")
        _toast(self, "Inicia sesión para continuar", tipo="info")

    def _crear_tarjeta_login(self):
        contenedor = tk.Frame(self, bg=BG_DARK)
        contenedor.pack(expand=True)

        tarjeta = tk.Frame(contenedor, bg=WHITE, padx=60, pady=45)
        tarjeta.pack()

        tk.Label(
            tarjeta, text="Iniciar Sesion", font=FUENTE_TITULO,
            bg=WHITE, fg=BLACK
        ).pack(pady=(0, 35))

        self.entry_usuario = self._campo_con_placeholder(
            tarjeta, "Usuario / Correo electronico"
        )
        self.entry_usuario.pack(fill="x", ipady=10, pady=6)

        self.entry_password = self._campo_password_con_placeholder(
            tarjeta, "Contrasena"
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

        self.label_info = tk.Label(
            tarjeta, text="", font=FUENTE_BODY,
            bg=WHITE, fg="#c0392b", wraplength=260
        )
        self.label_info.pack(pady=(8, 0))

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

    def _campo_con_placeholder(self, parent, texto_placeholder):
        entry = tk.Entry(
            parent, font=FUENTE_BODY, bg=GRAY_INPUT, fg="#5a5a5a",
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

    def _campo_password_con_placeholder(self, parent, texto_placeholder):
        entry = tk.Entry(
            parent, font=FUENTE_BODY, bg=GRAY_INPUT, fg="#5a5a5a",
            relief="flat", justify="center"
        )
        entry.insert(0, texto_placeholder)

        def al_enfocar(event):
            if entry.get() == texto_placeholder:
                entry.delete(0, tk.END)
                entry.config(fg=BLACK, show="•")

        def al_desenfocar(event):
            if entry.get().strip() == "":
                entry.config(show="")
                entry.insert(0, texto_placeholder)
                entry.config(fg="#5a5a5a")

        entry.bind("<FocusIn>", al_enfocar)
        entry.bind("<FocusOut>", al_desenfocar)
        entry.placeholder = texto_placeholder
        return entry

    def _obtener_credenciales_limpias(self):
        usuario = self.entry_usuario.get().strip()
        password = self.entry_password.get().strip()

        if usuario == self.entry_usuario.placeholder:
            usuario = ""
        if password == self.entry_password.placeholder:
            password = ""

        return usuario, password

    def _manejar_login(self):
        usuario, password = self._obtener_credenciales_limpias()

        if not usuario:
            self.label_info.config(text="Debes ingresar un usuario")
            _toast(self, "Debes ingresar un usuario", tipo="error")
            return
        if not password:
            self.label_info.config(text="Debes ingresar una contrasena")
            _toast(self, "Debes ingresar una contrasena", tipo="error")
            return

        # Verificacion contra data/usuarios.json (errores en label_info + toast)
        if self.gestor_usuarios.verificar_usuario(usuario, password):
            self.label_info.config(text="")
            _toast(self, f"Sesión iniciada: {usuario}", tipo="exito")
            if self.on_login_exitoso:
                # Dar 400ms para que el toast de éxito se vea antes de navegar
                self.after(400, lambda: self.on_login_exitoso(usuario))
        else:
            self.label_info.config(text="Usuario o contrasena incorrectos")
            _toast(self, "Usuario o contrasena incorrectos", tipo="error")

    def _manejar_crear_cuenta(self):
        # Si el main provee pantalla de registro, navegar hacia ella.
        if self.on_crear_cuenta:
            self.on_crear_cuenta()
            return

        usuario, password = self._obtener_credenciales_limpias()

        if not usuario:
            self.label_info.config(text="Ingresa un usuario para registrarte")
            _toast(self, "Ingresa un usuario para registrarte", tipo="error")
            return
        if not password:
            self.label_info.config(text="Ingresa una contrasena para registrarte")
            _toast(self, "Ingresa una contrasena para registrarte", tipo="error")
            return

        nuevo_usuario = self.gestor_usuarios.registrar_usuario(usuario, password)
        if nuevo_usuario is None:
            self.label_info.config(text="Ese usuario ya existe o hubo un error")
            _toast(self, "Ese usuario ya existe o hubo un error", tipo="error")
            return

        # GestorUsuarios retorna objeto Usuario (con .nombre), no dict.
        nombre = getattr(nuevo_usuario, "nombre", str(nuevo_usuario))
        self.label_info.config(text="")
        _toast(self, f"Cuenta '{nombre}' creada con exito", tipo="exito")

        if self.on_login_exitoso:
            self.after(400, lambda: self.on_login_exitoso(nombre))


if __name__ == "__main__":
    root = tk.Tk()
    root.title("RetroVault - Iniciar Sesion")
    root.geometry("1000x650")
    root.configure(bg=BG_DARK)
    root.resizable(False, False)

    pantalla = PantallaLogin(
        root,
        on_login_exitoso=lambda usr: print(f"Redirigiendo... Usuario autenticado: {usr}")
    )
    pantalla.pack(fill="both", expand=True)

    root.mainloop()
