"""
usuario.py
Modelo de usuarios: registro y autenticación con persistencia en JSON (texto plano).

Ubicación canónica del GestorUsuarios (antes vivía en vistas/).
La ruta del JSON vive en persistencia/gestor_persistencia.py
(data/usuarios.json).

Roles: "admin" | "normal". Los nuevos registros son SIEMPRE "normal".
Las contraseñas se guardan en texto plano (sin hash) por decisión del equipo.

API usada por el proyecto y los tests:
    GestorUsuarios(archivo=None)     -> usa data/usuarios.json por defecto
    verificar_usuario(nombre, pwd)   -> True/False (login)
    registrar_usuario(nombre, pwd)   -> Usuario nuevo (rol normal) o None
    es_admin(nombre)                 -> True solo para rol admin
    existe_usuario(nombre)           -> True/False
    obtener_usuario(nombre)          -> Usuario o None
Alias de compatibilidad: verificar_credenciales()
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from persistencia.gestor_persistencia import (
        RUTA_USUARIOS_JSON,
        cargar_json,
        guardar_json,
    )
except ImportError:  # fallback ejecucion directa dentro de modelos/
    from gestor_persistencia import (
        RUTA_USUARIOS_JSON,
        cargar_json,
        guardar_json,
    )


class Usuario:
    """Representa un usuario registrado: nombre + rol (admin o normal)."""

    def __init__(self, nombre, password, rol="normal"):
        self.nombre = nombre
        self.password = password
        self.rol = rol if rol in ("admin", "normal") else "normal"

    def to_dict(self):
        return {"nombre": self.nombre, "password": self.password, "rol": self.rol}

    @classmethod
    def from_dict(cls, datos):
        rol = datos.get("rol")
        if rol not in ("admin", "normal"):
            # Migración de registros antiguos sin rol
            rol = "admin" if (datos.get("nombre") or "").strip().lower() == "admin" else "normal"
        # Acepta "password" (actual) y "password_hash" (legado con hash:
        # se conserva tal cual para no perder la cuenta).
        raw = datos.get("password", None)
        if raw is None:
            raw = datos.get("password_hash", "")
        return cls(datos["nombre"], raw, rol)

    def es_admin(self):
        return self.rol == "admin"

    def __str__(self):
        return f"{self.nombre} ({self.rol})"


def _rol_para(nombre):
    """Rol por defecto al migrar registros legacy sin campo 'rol'."""
    if (nombre or "").strip().lower() == "admin":
        return "admin"
    return "normal"


def es_correo_valido(correo):
    """
    Valida un correo con reglas simples (sin librerías externas):
    - No vacío y contiene exactamente un '@'.
    - Parte local no vacía (antes del @).
    - Dominio no vacío y contiene un punto, con parte local de dominio
      y TLD no vacías (dominio.tld).
    """
    correo = (correo or "").strip()
    partes = correo.split("@")
    if len(partes) != 2:
        return False
    local, dominio = partes
    if not local or not dominio:
        return False
    if "." not in dominio:
        return False
    antes_punto, _, tld = dominio.rpartition(".")
    if not antes_punto or not tld:
        return False
    return True


class GestorUsuarios:
    """
    Gestiona registro y verificación de usuarios con
    persistencia automática en archivo JSON (texto plano).
    """

    def __init__(self, archivo=None):
        self.archivo = str(archivo) if archivo else str(RUTA_USUARIOS_JSON)
        self.usuarios = self._cargar()

    def _cargar(self):
        """Carga los usuarios desde el JSON, o siembra admin/1234 si no existe."""
        datos = cargar_json(self.archivo, default=None)
        if datos is None:
            # Usuario admin por defecto para primer arranque.
            inicial = [Usuario("admin", "1234", "admin")]
            self._guardar(inicial)
            return inicial
        return self._normalizar_datos(datos)

    def _normalizar_datos(self, datos):
        """
        Convierte lo que haya en el archivo a objetos Usuario.
        Acepta lista de dicts (actual) y dict legacy {usuario: password}.
        """
        usuarios = []

        if isinstance(datos, dict):
            # Formato legacy: {"usuario": "password"}
            for nombre, valor in datos.items():
                if not nombre or not valor:
                    continue
                usuarios.append(Usuario(nombre, str(valor), _rol_para(nombre)))
            return usuarios

        for d in datos:
            nombre = (d.get("nombre") or "").strip()
            if not nombre:
                continue
            rol = d.get("rol") or _rol_para(nombre)
            raw = d.get("password", None)
            if raw is None:
                raw = d.get("password_hash", "")
            usuarios.append(Usuario(nombre, str(raw), rol))

        # Si la migración agregó roles, persistirla una vez
        if any("rol" not in d for d in datos) if isinstance(datos, list) and datos else False:
            self._guardar(usuarios)
        return usuarios

    def _guardar(self, usuarios=None):
        lista = usuarios if usuarios is not None else self.usuarios
        guardar_json(self.archivo, [u.to_dict() for u in lista])

    def existe_usuario(self, nombre):
        """True si ya existe un usuario con ese nombre (sin importar mayúsculas)."""
        nombre = (nombre or "").strip()
        if not nombre:
            return False
        return any(u.nombre.lower() == nombre.lower() for u in self.usuarios)

    def obtener_usuario(self, nombre):
        """Retorna el Usuario o None si no existe."""
        nombre = (nombre or "").strip()
        for u in self.usuarios:
            if u.nombre.lower() == nombre.lower():
                return u
        return None

    def verificar_usuario(self, nombre, password):
        """Verifica credenciales (case-insensitive en el nombre). Retorna True/False."""
        nombre = (nombre or "").strip()
        for u in self.usuarios:
            if u.nombre.lower() == nombre.lower():
                return u.password == (password if isinstance(password, str) else "")
        return False

    def verificar_credenciales(self, usuario, password):
        """Alias de verificar_usuario (compatibilidad con version anterior)."""
        return self.verificar_usuario(usuario, password)

    def es_admin(self, nombre):
        """True solo si el usuario existe y tiene rol 'admin'."""
        if nombre is None:
            return False
        nombre = str(nombre).strip()
        for u in self.usuarios:
            if u.nombre.lower() == nombre.lower():
                return u.rol == "admin"
        return False

    def registrar_usuario(self, nombre, password):
        """
        Registra un usuario nuevo con rol "normal".
        Retorna el Usuario creado, o None si el nombre/contraseña no
        son válidos o el nombre ya está en uso.
        """
        nombre = (nombre or "").strip()
        password = password if isinstance(password, str) else ""
        if not nombre or not password:
            return None
        if self.existe_usuario(nombre):
            return None
        nuevo = Usuario(nombre, password, rol="normal")
        self.usuarios.append(nuevo)
        self._guardar()
        return nuevo


# ==============================================================================
# PRUEBA INDEPENDIENTE: ejecuta "python -m modelos.usuario"
# ==============================================================================
if __name__ == "__main__":
    gestor = GestorUsuarios()
    print("Usuarios registrados:", [(u.nombre, u.rol) for u in gestor.usuarios])
    print("Login admin/1234:", gestor.verificar_usuario("admin", "1234"))
    print("es_admin admin:", gestor.es_admin("admin"))
