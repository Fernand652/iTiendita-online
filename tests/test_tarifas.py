import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos.despacho import Despacho
from persistencia.gestor_tarifas import GestorTarifas


class TestGestorTarifas(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.ruta = os.path.join(self.tempdir, "config_despacho.json")
        Despacho.aplicar_config(Despacho.config_por_defecto())

    def tearDown(self):
        Despacho.aplicar_config(Despacho.config_por_defecto())
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_archivo_inexistente_usa_valores_por_defecto(self):
        gestor = GestorTarifas(archivo=self.ruta)
        self.assertEqual(gestor.config["tarifas"]["Maule"], 4990)
        self.assertEqual(gestor.config["envio_gratis_desde"], 100000)
        self.assertFalse(os.path.exists(self.ruta))

    def test_guardar_y_recargar(self):
        gestor = GestorTarifas(archivo=self.ruta)
        config = dict(gestor.config)
        config["tarifas"] = dict(config["tarifas"])
        config["tarifas"]["Maule"] = 1234
        config["envio_gratis_desde"] = 50000
        gestor.guardar(config)
        self.assertEqual(Despacho("domicilio", "Maule").calcular(40000), 1234)
        self.assertEqual(Despacho("domicilio", "Maule").calcular(50000), 0)
        otro = GestorTarifas(archivo=self.ruta)
        self.assertEqual(otro.config["tarifas"]["Maule"], 1234)
        self.assertEqual(otro.config["envio_gratis_desde"], 50000)

    def test_archivo_corrupto_usa_valores_por_defecto(self):
        with open(self.ruta, "w", encoding="utf-8") as archivo:
            archivo.write("{json roto")
        gestor = GestorTarifas(archivo=self.ruta)
        self.assertEqual(gestor.config["tarifas"]["Maule"], 4990)
        self.assertEqual(Despacho.ENVIO_GRATIS_DESDE, 100000)

    def test_configuracion_invalida_no_se_guarda(self):
        gestor = GestorTarifas(archivo=self.ruta)
        with self.assertRaises(ValueError):
            gestor.guardar({"tarifas": {"Maule": "no es un monto"}})
        self.assertFalse(os.path.exists(self.ruta))


if __name__ == "__main__":
    unittest.main()
