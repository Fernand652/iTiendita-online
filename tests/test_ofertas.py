import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos.inventario import Inventario
from persistencia.gestor_ofertas import GestorOfertas


class TestOfertas(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.ruta_productos = os.path.join(self.tempdir, "productos.json")
        self.ruta_ofertas = os.path.join(self.tempdir, "ofertas.json")
        self.inventario = Inventario(archivo=self.ruta_productos)
        self.juego = self.inventario.agregar_producto("Juego", 10000, 3, "Juegos")
        self.consola = self.inventario.agregar_producto("Consola", 50000, 2, "Consolas")
        self.gestor = GestorOfertas(archivo=self.ruta_ofertas)

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_oferta_por_producto_aplica_y_al_eliminar_restaura_precio(self):
        oferta = self.gestor.crear("producto", self.juego.id, 7000,
                                   "2026-01-01", "2026-12-31")
        self.gestor.aplicar_a_inventario(self.inventario, hoy="2026-06-01")
        self.assertEqual(self.juego.precio, 7000)
        self.assertEqual(self.juego.precio_normal, 10000)
        self.gestor.eliminar(oferta.id_oferta)
        self.gestor.aplicar_a_inventario(self.inventario, hoy="2026-06-01")
        self.assertEqual(self.juego.precio, 10000)

    def test_oferta_por_categoria_y_oferta_vencida(self):
        self.gestor.crear("categoria", "Juegos", 8000,
                           "2026-01-01", "2026-12-31")
        self.gestor.crear("producto", self.consola.id, 30000,
                           "2026-01-01", "2026-01-31")
        self.gestor.aplicar_a_inventario(self.inventario, hoy="2026-06-01")
        self.assertEqual(self.juego.precio, 8000)
        self.assertEqual(self.consola.precio, 50000)

    def test_persistencia_y_prioridad_del_mejor_precio(self):
        self.gestor.crear("categoria", "Juegos", 8500,
                           "2026-01-01", "2026-12-31")
        self.gestor.crear("producto", self.juego.id, 6500,
                           "2026-01-01", "2026-12-31")
        recargado = GestorOfertas(archivo=self.ruta_ofertas)
        self.assertEqual(len(recargado.ofertas), 2)
        self.assertEqual(recargado.precio_vigente(self.juego, "2026-06-01"), 6500)


if __name__ == "__main__":
    unittest.main()
