"""Pruebas del modelo de despacho: tarifas, envío gratis y datos de entrega."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos.despacho import Despacho


class TestDespacho(unittest.TestCase):
    def test_retiro_no_cobra_envio(self):
        self.assertEqual(Despacho("retiro", "Metropolitana").calcular(50000), 0)

    def test_tarifas_por_region(self):
        self.assertEqual(Despacho("domicilio", "Maule").calcular(50000), 4990)
        self.assertEqual(Despacho("domicilio", "Metropolitana").calcular(50000), 5990)
        self.assertEqual(Despacho("domicilio", "Biobío").calcular(50000), 7990)

    def test_envio_gratis_desde_el_monto_configurado(self):
        self.assertEqual(Despacho("domicilio", "Maule").calcular(100000), 0)
        self.assertEqual(Despacho("domicilio", "Maule").calcular(99999), 4990)

    def test_dias_de_entrega(self):
        self.assertEqual(Despacho("retiro", "Maule").dias_entrega(), 0)
        self.assertEqual(Despacho("domicilio", "Maule").dias_entrega(), 2)
        self.assertEqual(Despacho("domicilio", "Metropolitana").dias_entrega(), 5)

    def test_ida_y_vuelta_con_direccion_y_comuna(self):
        original = Despacho(
            "domicilio", "Maule", "ana",
            "Av. Siempre Viva 742", "Talca",
        )
        datos = original.to_dict()
        self.assertEqual(datos["direccion"], "Av. Siempre Viva 742")
        self.assertEqual(datos["comuna"], "Talca")
        self.assertEqual(datos["dias_entrega"], 2)
        copia = Despacho.from_dict(datos)
        self.assertEqual(copia.modalidad, "domicilio")
        self.assertEqual(copia.region, "Maule")
        self.assertEqual(copia.receptor, "ana")
        self.assertEqual(copia.direccion, "Av. Siempre Viva 742")
        self.assertEqual(copia.comuna, "Talca")


if __name__ == "__main__":
    unittest.main()
