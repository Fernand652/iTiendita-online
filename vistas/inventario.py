"""
inventario.py
Clases Producto e Inventario -- la fuente única de datos del catálogo.
"""

import json
import os


class Producto:
    """Representa un producto del catálogo."""

    def __init__(self, id, nombre, precio, stock, categoria, imagen=None):
        self.id = id
        self.nombre = nombre
        self.precio = precio
        self.stock = stock
        self.categoria = categoria
        self.imagen = imagen  # ruta relativa a un archivo PNG, o None si no tiene

    def to_dict(self):
        """Convierte el producto a diccionario (para guardar en JSON)."""
        return {
            "id": self.id, "nombre": self.nombre, "precio": self.precio,
            "stock": self.stock, "categoria": self.categoria, "imagen": self.imagen,
        }

    @classmethod
    def from_dict(cls, datos):
        """
        Crea un Producto a partir de un diccionario (al leer el JSON).
        Usa .get("imagen") en vez de ["imagen"] para que los productos
        que ya tenías guardados ANTES de esta actualización (sin ese
        campo) se sigan cargando sin error -- simplemente sin imagen.
        """
        return cls(
            datos["id"], datos["nombre"], datos["precio"], datos["stock"],
            datos["categoria"], datos.get("imagen")
        )

    def __str__(self):
        return f"[{self.id}] {self.nombre} | ${self.precio} | Stock: {self.stock} | {self.categoria}"


class Inventario:
    """
    Gestiona el catálogo completo: CRUD (Item 1), cálculos (Item 3)
    y persistencia automática en JSON (Item 2) -- cada operación que
    modifica el catálogo lo guarda solo, sin que tengas que acordarte
    de llamar a "guardar" aparte.
    """

    def __init__(self, archivo="productos.json"):
        self.archivo = archivo
        self.productos = self._cargar()

    def _cargar(self):
        """Carga el catálogo desde el JSON, o crea uno de ejemplo si no existe."""
        if not os.path.exists(self.archivo):
            productos_iniciales = [
                Producto(1, "Super Nintendo", 149990, 4, "Consolas"),
                Producto(2, "The Legend of Zelda: Ocarina of Time", 89990, 12, "Videojuegos"),
                Producto(3, "Super Mario 64", 99990, 0, "Videojuegos"),
            ]
            self.productos = productos_iniciales
            self._guardar()
            return productos_iniciales

        with open(self.archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return [Producto.from_dict(d) for d in datos]

    def _guardar(self):
        """Guarda el catálogo completo en el archivo JSON."""
        datos = [p.to_dict() for p in self.productos]
        with open(self.archivo, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)

    def _siguiente_id(self):
        """
        Genera el próximo ID disponible automáticamente. Así "Validar
        ID único" (requisito del Item 1) queda garantizado por diseño:
        el usuario nunca tiene que inventar un ID a mano.
        """
        if not self.productos:
            return 1
        return max(p.id for p in self.productos) + 1

    # ------------------------------------------------------------------
    # CRUD (Item 1)
    # ------------------------------------------------------------------
    def agregar_producto(self, nombre, precio, stock, categoria, imagen=None):
        nuevo = Producto(self._siguiente_id(), nombre, precio, stock, categoria, imagen)
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
        """Categorías únicas actualmente en uso (para el combo de la interfaz)."""
        categorias = []
        for p in self.productos:
            if p.categoria not in categorias:
                categorias.append(p.categoria)
        return categorias

    # ------------------------------------------------------------------
    # ITEM 3: cálculos matemáticos
    # ------------------------------------------------------------------
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
        """Reportes avanzados (opcional): suma precio * stock de todo el catálogo."""
        total = 0
        for p in self.productos:
            total += p.precio * p.stock
        return total


# ==============================================================================
# PRUEBA INDEPENDIENTE: ejecuta "python inventario.py" para probar el CRUD
# completo sin necesidad de tkinter ni ventanas.
# ==============================================================================
if __name__ == "__main__":
    inv = Inventario()
    print("Productos cargados:")
    for p in inv.productos:
        print(" ", p, "| imagen:", p.imagen)

    print("\nAgregando un producto CON imagen...")
    nuevo = inv.agregar_producto("Game Boy Color", 59990, 6, "Consolas", imagen="imagenes/gbc.png")
    print(" ID asignado:", nuevo.id, "| imagen:", nuevo.imagen)

    print("\nCompatibilidad con productos guardados ANTES de tener 'imagen'...")
    producto_viejo = Producto.from_dict({"id": 99, "nombre": "Test", "precio": 100, "stock": 1, "categoria": "X"})
    print(" ", producto_viejo, "| imagen:", producto_viejo.imagen)

    print("\nEliminando el producto de prueba...")
    inv.eliminar_producto(nuevo.id)
    print(" Productos restantes:", [p.nombre for p in inv.productos])
