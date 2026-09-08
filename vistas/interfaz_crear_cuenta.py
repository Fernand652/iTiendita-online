"""
interfaz_crear_cuenta.py
Pantalla de registro de nuevos usuarios en RetroVault.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
try:
    from vistas.estilos import *
except ImportError:  # permite ejecutar este archivo directamente
    from estilos import *
try:
    from modelos.usuario import GestorUsuarios, es_correo_valido
except ImportError:
    try:
        from usuario import GestorUsuarios, es_correo_valido
    except ImportError:
        GestorUsuarios = None
        es_correo_valido = None

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


class PantallaCrearCuenta(tk.Frame):
    """
    Pantalla de registro de cuenta.

    Parámetros:
        parent:             Widget contenedor (root u otro Frame).
        on_registro_exitoso: Función llamada al completar el registro. Recibe un dict con los datos.
        on_ir_a_login:      Función llamada al pulsar en 'INICIAR SESIÓN'.
    """

    def __init__(self, parent, on_registro_exitoso=None, on_ir_a_login=None, gestor_usuarios=None, on_ir_explorar=None, on_ver_carrito=None):
        super().__init__(parent, bg=BG_DARK)
        self.on_registro_exitoso = on_registro_exitoso
        self.on_ir_a_login = on_ir_a_login
        self.on_ir_explorar = on_ir_explorar
        self.on_ver_carrito = on_ver_carrito
        if gestor_usuarios is not None:
            self.gestor_usuarios = gestor_usuarios
        elif GestorUsuarios is not None:
            self.gestor_usuarios = GestorUsuarios()
        else:
            self.gestor_usuarios = None

        self._crear_barra_superior()
        self._crear_tarjeta_registro()


    # BARRA SUPERIOR
    def _crear_barra_superior(self):
        # Sin acceso invitado: solo logo. Para ver el catálogo o el
        # carrito hay que registrarse e iniciar sesión primero.
        barra = tk.Frame(self, bg=BG_DARK)
        barra.pack(fill="x", padx=40, pady=20)

        tk.Label(
            barra, text="RETRO VAULT", font=FUENTE_LOGO,
            bg=BG_DARK, fg=GREEN
        ).pack(side="left")

    def _ir_explorar(self):
        # Botón eliminado de la barra; se mantiene por compatibilidad:
        # sin sesión siempre pide iniciar sesión.
        self._mostrar_error("Inicia sesión para continuar")
        _toast(self, "Inicia sesión para continuar", tipo="info")

    def _ir_carrito(self):
        self._mostrar_error("Inicia sesión para continuar")
        _toast(self, "Inicia sesión para continuar", tipo="info")

    # TARJETA DE REGISTRO
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

        self.label_error = tk.Label(
            tarjeta, text="", font=FUENTE_BODY,
            bg=WHITE, fg="#c0392b", wraplength=260
        )
        self.label_error.pack(pady=(4, 0))

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

    # VALIDACIONES Y EVENTOS
    def _mostrar_error(self, msg):
        """Muestra un error EN PANTALLA (label rojo + toast flotante 2s)."""
        self.label_error.config(text=msg)
        _toast(self, msg, tipo="error")
        return None

    def _mostrar_exito(self, msg):
        """Éxito EN PANTALLA (limpia label + toast flotante 1.5s)."""
        self.label_error.config(text="")
        _toast(self, msg, tipo="exito")

    def _manejar_registro(self):
        nombres = self.entry_nombres.get().strip()
        apellidos = self.entry_apellidos.get().strip()
        pais = self.entry_pais.get().strip()
        correo = self.entry_correo.get().strip()
        password = self.entry_password.get().strip()
        confirmar = self.entry_confirmar_password.get().strip()

        # Validación de campos obligatorios (errores por pantalla)
        if nombres == self.entry_nombres.placeholder or not nombres:
            return self._mostrar_error("Debes ingresar tus nombres")
        if apellidos == self.entry_apellidos.placeholder or not apellidos:
            return self._mostrar_error("Debes ingresar tus apellidos")
        if pais == self.entry_pais.placeholder or not pais:
            return self._mostrar_error("Debes ingresar tu país")
        if correo == self.entry_correo.placeholder or not correo:
            return self._mostrar_error("Debes ingresar un correo electrónico")
        if es_correo_valido is not None and not es_correo_valido(correo):
            return self._mostrar_error("El correo electrónico no es válido")
        if password == self.entry_password.placeholder or not password:
            return self._mostrar_error("Debes ingresar una contraseña")
        if confirmar == self.entry_confirmar_password.placeholder or not confirmar:
            return self._mostrar_error("Debes confirmar tu contraseña")

        # Validación de coincidencia de contraseñas
        if password != confirmar:
            return self._mostrar_error("Las contraseñas no coinciden")

        # Nombre de login: se usa el correo como identificador único
        # (compatible con GestorUsuarios que persiste en data/usuarios.json).
        datos_usuario = {
            "nombres": nombres,
            "apellidos": apellidos,
            "pais": pais,
            "correo": correo,
            "password": password
        }

        if self.gestor_usuarios is not None:
            nuevo = self.gestor_usuarios.registrar_usuario(correo, password)
            if nuevo is None:
                self._mostrar_error("Ese correo ya está registrado")
                return
            self._mostrar_exito(f"Cuenta '{correo}' creada con éxito")
        else:
            self.label_error.config(text="")
            _toast(self, f"Cuenta '{correo}' creada", tipo="exito")

        if self.on_registro_exitoso:
            # 400ms para que el toast de éxito se vea antes de navegar
            datos = dict(datos_usuario)
            self.after(400, lambda: self.on_registro_exitoso(datos))

    def _manejar_ir_a_login(self):
        if self.on_ir_a_login:
            self.on_ir_a_login()
# PRUEBA INDEPENDIENTE
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