"""Tests del modelo Inventario (unittest, stdlib)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos.inventario import Inventario
from modelos.producto import Producto


def _tmp():
    return tempfile.mktemp(suffix=".json")


class TestInventarioCRUD(unittest.TestCase):
    def setUp(self):
        self.archivo = _tmp()
        self.inv = Inventario(archivo=self.archivo)

    def tearDown(self):
        if os.path.exists(self.archivo):
            os.remove(self.archivo)

    def test_archivo_inexistente_crea_catalogo_vacio(self):
        self.assertEqual(self.inv.productos, [])

    def test_agregar_y_buscar_por_id(self):
        p = self.inv.agregar_producto("Laptop Gamer", 999990, 10, "Electrónicos")
        self.assertEqual(p.id, 1)
        self.assertIs(self.inv.buscar_por_id(1), p)
        self.assertIsNone(self.inv.buscar_por_id(999))

    def test_actualizar(self):
        p = self.inv.agregar_producto("Mouse", 20000, 5, "Accesorios")
        self.assertTrue(self.inv.actualizar_producto(p.id, "Mouse Pro", 25000, 3, "Accesorios"))
        self.assertEqual((p.nombre, p.precio, p.stock), ("Mouse Pro", 25000, 3))

    def test_actualizar_inexistente_retorna_false(self):
        self.assertFalse(self.inv.actualizar_producto(999, "X", 1, 1, "Y"))

    def test_eliminar(self):
        p = self.inv.agregar_producto("Teclado", 49990, 20, "Electrónicos")
        self.assertTrue(self.inv.eliminar_producto(p.id))
        self.assertIsNone(self.inv.buscar_por_id(p.id))
        self.assertFalse(self.inv.eliminar_producto(p.id))

    def test_id_unico_no_se_reutiliza(self):
        a = self.inv.agregar_producto("A", 1, 1, "C")
        b = self.inv.agregar_producto("B", 1, 1, "C")
        self.inv.eliminar_producto(a.id)
        c = self.inv.agregar_producto("C", 1, 1, "C")
        self.assertEqual(c.id, b.id + 1)
        self.assertEqual(len({p.id for p in self.inv.productos}), 2)

    def test_id_manual_ok(self):
        p = self.inv.agregar_producto("Manual", 100, 1, "C", id=7)
        self.assertEqual(p.id, 7)
        self.assertIs(self.inv.buscar_por_id(7), p)

    def test_id_manual_duplicado_lanza_y_no_persiste(self):
        self.inv.agregar_producto("A", 1, 1, "C", id=7)
        with self.assertRaises(ValueError):
            self.inv.agregar_producto("B", 1, 1, "C", id=7)
        self.assertEqual(len(self.inv.productos), 1)
        inv2 = Inventario(archivo=self.archivo)
        self.assertEqual(len(inv2.productos), 1)

    def test_id_manual_invalido_lanza(self):
        for malo in (0, -3, True, 1.5, "7"):
            with self.assertRaises(ValueError, msg=f"id={malo!r}"):
                self.inv.agregar_producto("X", 1, 1, "C", id=malo)
        self.assertEqual(self.inv.productos, [])

    def test_auto_tras_manual_alto(self):
        self.inv.agregar_producto("M", 1, 1, "C", id=10)
        auto = self.inv.agregar_producto("A", 1, 1, "C")
        self.assertEqual(auto.id, 11)

    def test_persistencia_roundtrip_con_imagen(self):
        self.inv.agregar_producto("Foto", 1000, 2, "Cat", imagen="data/imagenes/id_1.png")
        inv2 = Inventario(archivo=self.archivo)
        self.assertEqual(len(inv2.productos), 1)
        self.assertEqual(inv2.productos[0].imagen, "data/imagenes/id_1.png")

    def test_obtener_categorias_unicas(self):
        self.inv.agregar_producto("A", 1, 1, "X")
        self.inv.agregar_producto("B", 1, 1, "Y")
        self.inv.agregar_producto("C", 1, 1, "X")
        self.assertEqual(self.inv.obtener_categorias(), ["X", "Y"])


class TestInventarioValidaciones(unittest.TestCase):
    def setUp(self):
        self.archivo = _tmp()
        self.inv = Inventario(archivo=self.archivo)

    def tearDown(self):
        if os.path.exists(self.archivo):
            os.remove(self.archivo)

    def test_agregar_precio_negativo_lanza_y_no_persiste(self):
        with self.assertRaises(ValueError):
            self.inv.agregar_producto("Malo", -5, 1, "C")
        self.assertEqual(self.inv.productos, [])
        inv2 = Inventario(archivo=self.archivo)
        self.assertEqual(inv2.productos, [])

    def test_agregar_stock_negativo_lanza(self):
        with self.assertRaises(ValueError):
            self.inv.agregar_producto("Malo", 5, -1, "C")
        self.assertEqual(self.inv.productos, [])

    def test_actualizar_negativo_lanza_y_no_muta(self):
        p = self.inv.agregar_producto("Ok", 100, 5, "C")
        with self.assertRaises(ValueError):
            self.inv.actualizar_producto(p.id, "Ok", 100, -2, "C")
        with self.assertRaises(ValueError):
            self.inv.actualizar_producto(p.id, "Ok", -1, 5, "C")
        self.assertEqual((p.precio, p.stock), (100, 5))


class TestInventarioCalculosYFiltros(unittest.TestCase):
    def setUp(self):
        self.archivo = _tmp()
        self.inv = Inventario(archivo=self.archivo)
        self.inv.productos = [
            Producto(1, "Laptop Gamer", 999990, 10, "Electrónicos"),
            Producto(2, "Teclado Mecánico", 49990, 20, "Electrónicos"),
            Producto(3, "Mouse", 50000, 5, "Accesorios"),
            Producto(4, "Monitor", 100000, 7, "Electrónicos"),
        ]

    def tearDown(self):
        if os.path.exists(self.archivo):
            os.remove(self.archivo)

    def test_promedio_categoria(self):
        prom = self.inv.calcular_promedio_categoria("Electrónicos")
        self.assertAlmostEqual(prom, (999990 + 49990 + 100000) / 3)

    def test_promedio_categoria_vacia_none(self):
        self.assertIsNone(self.inv.calcular_promedio_categoria("Nada"))

    def test_menor_stock(self):
        self.assertEqual(self.inv.producto_menor_stock_categoria("Electrónicos").nombre, "Monitor")

    def test_menor_stock_vacia_none(self):
        self.assertIsNone(self.inv.producto_menor_stock_categoria("Nada"))

    def test_valor_total(self):
        self.assertEqual(
            self.inv.calcular_valor_inventario(),
            999990 * 10 + 49990 * 20 + 50000 * 5 + 100000 * 7,
        )

    def test_buscar_parcial_insensitive(self):
        self.assertEqual([p.id for p in self.inv.buscar_por_nombre("laptop")], [1])
        self.assertEqual([p.id for p in self.inv.buscar_por_nombre("TEC")], [2])
        self.assertEqual(len(self.inv.buscar_por_nombre("")), 4)

    def test_rango_inclusivo_bordes(self):
        ids = sorted(p.id for p in self.inv.filtrar_por_rango_precio(50000, 100000))
        self.assertEqual(ids, [3, 4])

    def test_rango_sin_cotas_y_min_mayor(self):
        self.assertEqual(len(self.inv.filtrar_por_rango_precio(None, None)), 4)
        self.assertEqual(self.inv.filtrar_por_rango_precio(100000, 50000), [])

    def test_categoria_exacta_y_todas(self):
        self.assertEqual(
            sorted(p.id for p in self.inv.filtrar_por_categoria("electrónicos")), [1, 2, 4]
        )
        self.assertEqual(len(self.inv.filtrar_por_categoria("Todas")), 4)
        self.assertEqual(self.inv.filtrar_por_categoria("Nope"), [])

    def test_combinado_texto_categoria_rango(self):
        base = self.inv.buscar_por_nombre("electr")
        base = self.inv.filtrar_por_categoria("Electrónicos", base)
        final = self.inv.filtrar_por_rango_precio(40000, 60000, base)
        self.assertEqual([p.id for p in final], [2])

    def test_parse_precio_filtro(self):
        P = Inventario.parse_precio_filtro
        self.assertEqual(P("50.000"), 50000)
        self.assertEqual(P("50000"), 50000)
        self.assertIsNone(P(""))
        self.assertIsNone(P("   "))
        self.assertIsNone(P("abc"))


if __name__ == "__main__":
    unittest.main()