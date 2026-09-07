"""
login_vista.py
Pantalla de inicio de sesión de RetroVault conectada a usuarios.json.
"""

import json
import os
import tkinter as tk
from tkinter import messagebox

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


class GestorUsuariosJSON:
    """Clase encargada de leer y validar las credenciales desde usuarios.json."""

    def __init__(self, ruta_json="usuarios.json"):
        self.ruta_json = ruta_json

    def _cargar_usuarios(self):
        """Lee el archivo usuarios.json desde la raíz del proyecto."""
        if not os.path.exists(self.ruta_json):
            print(f"Advertencia: No se encontro {self.ruta_json}")
            return []
        try:
            with open(self.ruta_json, "r", encoding="utf-8") as archivo:
                return json.load(archivo)
        except Exception as e:
            print(f"Error al cargar {self.ruta_json}: {e}")
            return []

    def verificar_usuario(self, nombre, password):
        """Compara el nombre y contraseña con los registros del JSON."""
        usuarios = self._cargar_usuarios()
        for u in usuarios:
            if u.get("nombre") == nombre and u.get("password") == password:
                return True
        return False

    def registrar_usuario(self, nombre, password):
        """Agrega un nuevo usuario al archivo usuarios.json."""
        usuarios = self._cargar_usuarios()
        for u in usuarios:
            if u.get("nombre") == nombre:
                return None  # El usuario ya existe

        nuevo_usuario = {"nombre": nombre, "password": password}
        usuarios.append(nuevo_usuario)

        try:
            with open(self.ruta_json, "w", encoding="utf-8") as archivo:
                json.dump(usuarios, archivo, indent=2)
            return nuevo_usuario
        except Exception as e:
            print(f"Error al guardar usuario en {self.ruta_json}: {e}")
            return None


class PantallaLogin(tk.Frame):
    def __init__(self, parent, on_login_exitoso=None, on_crear_cuenta=None, gestor_usuarios=None):
        super().__init__(parent, bg=BG_DARK)
        self.on_login_exitoso = on_login_exitoso
        self.on_crear_cuenta = on_crear_cuenta
        self.gestor_usuarios = gestor_usuarios if gestor_usuarios is not None else GestorUsuariosJSON()

        self._crear_barra_superior()
        self._crear_tarjeta_login()

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
            on_click=lambda: print("Ir a explorar catalogo")
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
            return
        if not password:
            self.label_info.config(text="Debes ingresar una contrasena")
            return

        # Verificacion contra usuarios.json
        if self.gestor_usuarios.verificar_usuario(usuario, password):
            self.label_info.config(text="")
            print(f"Sesion iniciada con exito: {usuario}")
            if self.on_login_exitoso:
                self.on_login_exitoso(usuario)
        else:
            self.label_info.config(text="Usuario o contrasena incorrectos")

    def _manejar_crear_cuenta(self):
        usuario, password = self._obtener_credenciales_limpias()

        if not usuario:
            self.label_info.config(text="Ingresa un usuario para registrarte")
            return
        if not password:
            self.label_info.config(text="Ingresa una contrasena para registrarte")
            return

        nuevo_usuario = self.gestor_usuarios.registrar_usuario(usuario, password)
        if nuevo_usuario is None:
            self.label_info.config(text="Ese usuario ya existe o hubo un error")
            return

        self.label_info.config(text="")
        print(f"Cuenta registrada en JSON: {nuevo_usuario['nombre']}")
        messagebox.showinfo("Registro exitoso", f"Cuenta '{nuevo_usuario['nombre']}' creada con exito")

        if self.on_login_exitoso:
            self.on_login_exitoso(nuevo_usuario["nombre"])


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
