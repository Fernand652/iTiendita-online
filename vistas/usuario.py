"""
usuario.py
Clase GestorUsuarios: registro y autenticacion de usuarios, con
persistencia en JSON (reutiliza el mismo estilo de gestion de
archivos que el Inventario).

Amplia el trabajo original de Miguel Gonzalez (registro y
verificacion de usuario) para que la pantalla de login pueda
validar contra usuarios reales guardados en disco.
"""

import json
import os


class Usuario:
    """Representa un usuario registrado en la tienda."""

    def __init__(self, nombre, password):
        self.nombre = nombre
        self.password = password

    def to_dict(self):
        return {"nombre": self.nombre, "password": self.password}

    @classmethod
    def from_dict(cls, datos):
        return cls(datos["nombre"], datos["password"])


class GestorUsuarios:
    """
    Gestiona el registro y la verificacion de usuarios con
    persistencia automatica en archivo JSON.
    """

    def __init__(self, archivo="usuarios.json"):
        self.archivo = archivo
        self.usuarios = self._cargar()

    def _cargar(self):
        if not os.path.exists(self.archivo):
            # Un usuario admin por defecto para que el login funcione
            # apenas se abre la app por primera vez.
            inicial = [Usuario("admin", "1234")]
            self._guardar(inicial)
            return inicial

        with open(self.archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return [Usuario.from_dict(d) for d in datos]

    def _guardar(self, usuarios=None):
        lista = usuarios if usuarios is not None else self.usuarios
        datos = [u.to_dict() for u in lista]
        with open(self.archivo, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)

    def existe_usuario(self, nombre):
        """Retorna True si ya existe un usuario con ese nombre."""
        for u in self.usuarios:
            if u.nombre.lower() == nombre.lower():
                return True
        return False

    def registrar_usuario(self, nombre, password):
        """Registra un nuevo usuario. Retorna el Usuario o None si ya existe."""
        if not nombre.strip() or not password:
            return None
        if self.existe_usuario(nombre):
            return None
        nuevo = Usuario(nombre.strip(), password)
        self.usuarios.append(nuevo)
        self._guardar()
        return nuevo

    def verificar_usuario(self, nombre, password):
        """
        Verifica credenciales. Retorna True si el usuario existe y la
        contrasena coincide, False en caso contrario.
        """
        for u in self.usuarios:
            if u.nombre.lower() == nombre.lower() and u.password == password:
                return True
        return False


# ==============================================================================
# PRUEBA INDEPENDIENTE: ejecuta "python usuario.py"
# ==============================================================================
if __name__ == "__main__":
    gestor = GestorUsuarios()
    print("Usuarios registrados:", [u.nombre for u in gestor.usuarios])
    print("Login admin/1234:", gestor.verificar_usuario("admin", "1234"))
    print("Login admin/incorrecta:", gestor.verificar_usuario("admin", "xxxx"))
    print("Registro nuevo 'miguel'/'clave':", gestor.registrar_usuario("miguel", "clave"))
