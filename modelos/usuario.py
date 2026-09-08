"""
usuarios.py
Maneja el registro y la verificacion de usuarios: carga y guarda en
un archivo JSON (persistencia sin librerias externas).

Contrasenas con hash SHA-256 (hashlib es parte de la libreria
estandar, asi que no rompe la restriccion "sin librerias externas"):
nunca se guarda la contrasena real, solo su huella digital.

API usada por el proyecto y los tests:
    GestorUsuarios(archivo=None)     -> usa data/usuarios.json por defecto
    verificar_usuario(nombre, pwd)   -> True/False (login)
    registrar_usuario(nombre, pwd)   -> Usuario nuevo (rol normal) o None
    es_admin(nombre)                 -> True solo para rol admin
Alias de compatibilidad: verificar_credenciales()
"""

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from persistencia.gestor_persistencia import (
        RUTA_USUARIOS_JSON,
        cargar_json,
        guardar_json,
    )
except ImportError:  # fallback: ejecucion directa dentro de modelos/
    from gestor_persistencia import (
        RUTA_USUARIOS_JSON,
        cargar_json,
        guardar_json,
    )


class Usuario:
    """Representa un usuario registrado: nombre + rol (admin o normal)."""

    def __init__(self, nombre, password_hash, rol="normal"):
        self.nombre = nombre
        self.password_hash = password_hash
        self.rol = rol

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "password_hash": self.password_hash,
            "rol": self.rol,
        }

    def __str__(self):
        return f"{self.nombre} ({self.rol})"


def _rol_para(nombre):
    """Rol por defecto al migrar registros legacy sin campo 'rol'."""
    if (nombre or "").strip().lower() == "admin":
        return "admin"
    return "normal"


def _es_hash(texto):
    """True si el texto parece un hash SHA-256 (64 caracteres hex)."""
    if not isinstance(texto, str):
        return False
    return len(texto) == 64 and all(c in "0123456789abcdef" for c in texto.lower())


class GestorUsuarios:
    """
    Administra los usuarios: verifica credenciales, registra cuentas
    nuevas y consulta el rol (admin/normal). Persistencia automatica
    en JSON; las contrasenas se guardan con hash SHA-256.
    """

    def __init__(self, archivo=None):
        self.archivo = str(archivo) if archivo else str(RUTA_USUARIOS_JSON)
        self.usuarios = self._cargar()

    def _hash_password(self, password):
        """
        Convierte la contraseña en un hash SHA-256: nunca se guarda
        la contraseña real, solo esta "huella digital" de un solo
        sentido (no se puede revertir el hash para obtener la
        contraseña original).
        """
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _cargar(self):
        """Carga los usuarios desde el JSON, o siembra admin/1234 si no existe."""
        datos = cargar_json(self.archivo, default=None)
        if datos is None:
            inicial = [Usuario("admin", self._hash_password("1234"), rol="admin")]
            self._guardar(inicial)
            return inicial
        return self._normalizar_datos(datos)

    def _normalizar_datos(self, datos):
        """
        Convierte lo que haya en el archivo a objetos Usuario.
        Acepta el formato actual (lista de dicts) y el legacy
        (diccionario usuario -> hash) para no romper datos viejos.
        """
        usuarios = []

        if isinstance(datos, dict):
            # Formato legacy: {"usuario": "hash_sha256"}
            for nombre, valor in datos.items():
                if not nombre or not valor:
                    continue
                storage = valor if _es_hash(valor) else self._hash_password(str(valor))
                usuarios.append(Usuario(nombre, storage, _rol_para(nombre)))
            return usuarios

        for d in datos:
            nombre = (d.get("nombre") or "").strip()
            if not nombre:
                continue
            rol = d.get("rol") or _rol_para(nombre)
            raw = d.get("password_hash") or d.get("password") or ""
            storage = raw if _es_hash(raw) else self._hash_password(str(raw))
            usuarios.append(Usuario(nombre, storage, rol))

        return usuarios

    def _guardar(self, usuarios=None):
        lista = usuarios if usuarios is not None else self.usuarios
        guardar_json(self.archivo, [u.to_dict() for u in lista])

    # ------------------------------------------------------------------
    # API principal
    # ------------------------------------------------------------------
    def existe_usuario(self, nombre):
        """True si ya existe un usuario con ese nombre (sin importar mayúsculas)."""
        nombre = (nombre or "").strip()
        if not nombre:
            return False
        return any(u.nombre.lower() == nombre.lower() for u in self.usuarios)

    def verificar_usuario(self, nombre, password):
        """Autentica (case-insensitive en el nombre). Retorna True/False."""
        nombre = (nombre or "").strip()
        for u in self.usuarios:
            if u.nombre.lower() == nombre.lower():
                return u.password_hash == self._hash_password(password)
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
        nuevo = Usuario(nombre, self._hash_password(password), rol="normal")
        self.usuarios.append(nuevo)
        self._guardar()
        return nuevo


# ==============================================================================
# PRUEBA INDEPENDIENTE: ejecuta "python -m modelos.usuario"
# ==============================================================================
if __name__ == "__main__":
    gestor = GestorUsuarios()
    print("Usuarios cargados:", [u.nombre for u in gestor.usuarios])
    print("admin / 1234        ->", gestor.verificar_usuario("admin", "1234"))
    print("admin / clave_mala  ->", gestor.verificar_usuario("admin", "clave_mala"))
    print("es_admin('admin')   ->", gestor.es_admin("admin"))
    print("es_admin('nadie')   ->", gestor.es_admin("nadie"))
    print("registrar 'juan'    ->", gestor.registrar_usuario("juan", "abcd"))
    print("juan / abcd         ->", gestor.verificar_usuario("juan", "abcd"))