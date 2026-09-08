"""
inventario.py
Modelo Inventario — CRUD + cálculos + persistencia automática en JSON.

La ruta del JSON vive en persistencia/gestor_persistencia.py
(data/productos.json). Cada operación que modifica el catálogo
se autogarda.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from modelos.producto import Producto
    from persistencia.gestor_persistencia import (
        RUTA_PRODUCTOS_JSON,
        cargar_json,
        guardar_json,
    )
except ImportError:  # fallback ejecución directa
    from producto import Producto
    from gestor_persistencia import (
        RUTA_PRODUCTOS_JSON,
        cargar_json,
        guardar_json,
    )


class Inventario:
    """
    Gestiona el catálogo completo: CRUD, cálculos por categoría
    y persistencia automática en JSON.
    """

    def __init__(self, archivo=None):
        self.archivo = str(archivo) if archivo else str(RUTA_PRODUCTOS_JSON)
        self.productos = self._cargar()

    def _cargar(self):
        """Carga el catálogo desde JSON, o crea uno VACÍO si no existe
        (según enunciado Hito 1: archivo inexistente → catálogo vacío)."""
        datos = cargar_json(self.archivo, default=None)
        if datos is None:
            self.productos = []
            self._guardar()
            return self.productos
        return [Producto.from_dict(d) for d in datos]

    def _guardar(self):
        """Guarda el catálogo completo en el archivo JSON."""
        guardar_json(self.archivo, [p.to_dict() for p in self.productos])

    def _siguiente_id(self):
        """Próximo ID disponible (ID único garantizado por diseño)."""
        if not self.productos:
            return 1
        return max(p.id for p in self.productos) + 1

    # CRUD
    def agregar_producto(self, nombre, precio, stock, categoria, imagen=None, id=None):
        if precio < 0:
            raise ValueError("El precio no puede ser negativo")
        if stock < 0:
            raise ValueError("El stock no puede ser negativo")
        if id is None:
            id = self._siguiente_id()
        else:
            # ID manual: entero mayor o igual a 1 y único en el catálogo
            if isinstance(id, bool) or not isinstance(id, int):
                raise ValueError("El ID debe ser un número entero")
            if id < 1:
                raise ValueError("El ID debe ser mayor o igual a 1")
            if self.buscar_por_id(id) is not None:
                raise ValueError(f"Ya existe un producto con ID {id}")
        nuevo = Producto(id, nombre, precio, stock, categoria, imagen)
        self.productos.append(nuevo)
        self._guardar()
        return nuevo

    def buscar_por_id(self, id_producto):
        for p in self.productos:
            if p.id == id_producto:
                return p
        return None

    def actualizar_producto(self, id_producto, nombre, precio, stock, categoria, imagen=None):
        producto = self.buscar_por_id(id_producto)
        if producto is None:
            return False
        if precio < 0:
            raise ValueError("El precio no puede ser negativo")
        if stock < 0:
            raise ValueError("El stock no puede ser negativo")
        producto.nombre = nombre
        producto.precio = precio
        producto.stock = stock
        producto.categoria = categoria
        producto.imagen = imagen
        self._guardar()
        return True

    def eliminar_producto(self, id_producto):
        producto = self.buscar_por_id(id_producto)
        if producto is None:
            return False
        self.productos.remove(producto)
        self._guardar()
        return True

    def obtener_categorias(self):
        """Categorías únicas en uso (para el combo de la interfaz)."""
        categorias = []
        for p in self.productos:
            if p.categoria not in categorias:
                categorias.append(p.categoria)
        return categorias

    # Búsqueda y filtrado (opcional enunciado Hito 1)
    def buscar_por_nombre(self, texto):
        """
        Búsqueda parcial case-insensitive en nombre o categoría.
        Texto vacío → todos los productos.
        """
        texto = (texto or "").strip().lower()
        if not texto:
            return list(self.productos)
        return [
            p for p in self.productos
            if texto in p.nombre.lower() or texto in p.categoria.lower()
        ]

    @staticmethod
    def parse_precio_filtro(txt):
        """
        Parser CLP tolerante para filtros: "50.000", "50000", " 50,000 "
        → 50000. Vacío → None (sin cota). No numérico → None.
        """
        txt = (txt or "").strip()
        if not txt:
            return None
        try:
            valor = float(txt.replace(".", "").replace(",", "").replace(" ", ""))
        except ValueError:
            return None
        return valor

    def filtrar_por_rango_precio(self, minimo=None, maximo=None, productos=None):
        """
        Filtra por rango de precios: min <= precio <= max.
        None = sin cota. min > max → lista vacía.
        Si se entrega `productos`, filtra sobre esa lista (para combinar
        con búsqueda por texto); si no, sobre todo el catálogo.
        """
        base = list(productos) if productos is not None else list(self.productos)
        if minimo is not None and maximo is not None and minimo > maximo:
            return []
        return [
            p for p in base
            if (minimo is None or float(p.precio) >= minimo)
            and (maximo is None or float(p.precio) <= maximo)
        ]

    def filtrar_por_categoria(self, categoria, productos=None):
        """
        Filtra por categoría EXACTA (case-insensitive).
        "Todas", "" o None → todo. Categoría inexistente → [].
        Si se entrega `productos`, filtra sobre esa lista (para el AND
        texto ∩ categoría ∩ rango); si no, sobre todo el catálogo.
        """
        base = list(productos) if productos is not None else list(self.productos)
        cat = (categoria or "").strip()
        if not cat or cat.lower() == "todas":
            return base
        return [p for p in base if p.categoria.lower() == cat.lower()]
    # Cálculos por categoría
    def calcular_promedio_categoria(self, categoria):
        productos_categoria = [p for p in self.productos if p.categoria.lower() == categoria.lower()]
        if not productos_categoria:
            return None
        return sum(p.precio for p in productos_categoria) / len(productos_categoria)
    def producto_menor_stock_categoria(self, categoria):
        productos_categoria = [p for p in self.productos if p.categoria.lower() == categoria.lower()]
        if not productos_categoria:
            return None
        minimo = productos_categoria[0]
        for p in productos_categoria:
            if p.stock < minimo.stock:
                minimo = p
        return minimo
    def calcular_valor_inventario(self):
        """Suma precio * stock de todo el catálogo."""
        total = 0
        for p in self.productos:
            total += p.precio * p.stock
        return total
# prueba: python -m modelos.inventario
if __name__ == "__main__":
    inv = Inventario()
    print("Productos cargados:", len(inv.productos))
    if not inv.productos:
        print(" (catálogo vacío: crea productos desde el admin)")
    for p in inv.productos:
        print(" ", p, "| imagen:", p.imagen)
