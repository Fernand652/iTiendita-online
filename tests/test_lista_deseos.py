import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos.lista_deseos import ListaDeseos


class TestListaDeseos(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.ruta = os.path.join(self.tempdir, "listas_deseos.json")
        self.lista = ListaDeseos(archivo=self.ruta)

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_guardar_favorito_y_evitar_duplicado(self):
        self.assertEqual(
            self.lista.guardar_favorito("ana", 7),
            (True, "Guardado en tu lista de deseos"),
        )
        ok, mensaje = self.lista.guardar_favorito("ana", 7)
        self.assertFalse(ok)
        self.assertIn("ya está", mensaje)
        self.assertEqual(self.lista.productos_de("ana"), {7})

    def test_suscripciones_cuentan_clientes_distintos(self):
        self.lista.suscribirse("ana", 4)
        self.lista.suscribirse("beto", 4)
        self.lista.suscribirse("beto", 9)
        ok, _ = self.lista.suscribirse("ana", 4)
        self.assertFalse(ok)
        self.assertEqual(self.lista.cantidad_esperando(4), 2)
        self.assertEqual(self.lista.cantidad_esperando(9), 1)
        self.assertEqual(self.lista.cantidad_esperando(99), 0)

    def test_persistencia_de_favoritos_y_suscripciones(self):
        self.lista.guardar_favorito("ana", 3)
        self.lista.suscribirse("ana", 8)
        recargada = ListaDeseos(archivo=self.ruta)
        self.assertEqual(recargada.productos_de("ana"), {3, 8})
        self.assertTrue(recargada.es_suscriptor("ana", 8))


if __name__ == "__main__":
    unittest.main()
