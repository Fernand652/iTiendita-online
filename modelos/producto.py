"""
producto.py
Modelo Producto — fuente única de la entidad producto.
"""

try:
    from persistencia.gestor_persistencia import RUTA_PRODUCTOS_JSON  # noqa: F401 (referencia documental)
except ImportError:  # ejecución directa dentro de modelos/
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from persistencia.gestor_persistencia import RUTA_PRODUCTOS_JSON  # noqa: F401


class Producto:
    """Representa un producto del catálogo."""

    def __init__(self, id, nombre, precio, stock, categoria, imagen=None):
        self.id = id
        self.nombre = nombre
        self.precio = precio
        self.stock = stock
        self.categoria = categoria
        self.imagen = imagen  # ruta relativa a un PNG, o None

    def to_dict(self):
        """Convierte el producto a diccionario (para guardar en JSON)."""
        return {
            "id": self.id, "nombre": self.nombre, "precio": self.precio,
            "stock": self.stock, "categoria": self.categoria, "imagen": self.imagen,
        }

    @classmethod
    def from_dict(cls, datos):
        """
        Crea un Producto desde un diccionario.
        Usa .get("imagen") para compatibilidad con registros
        guardados antes de existir ese campo.
        """
        return cls(
            datos["id"], datos["nombre"], datos["precio"], datos["stock"],
            datos["categoria"], datos.get("imagen")
        )

    def __str__(self):
        return f"[{self.id}] {self.nombre} | ${self.precio} | Stock: {self.stock} | {self.categoria}"
