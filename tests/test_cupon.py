import unittest
from datetime import date, timedelta
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelos.cupon import Cupon


class TestCupon(unittest.TestCase):

    def test_cupon_porcentaje(self):
        venc = (date.today() + timedelta(days=5)).isoformat()
        c = Cupon("CYBER10", "porcentaje", 10, venc, 50)
        ok, msg = c.validar()
        desc, _ = c.calcular_descuento(100000)
        self.assertTrue(ok)
        self.assertEqual(desc, 10000)

    def test_cupon_monto_fijo(self):
        venc = (date.today() + timedelta(days=5)).isoformat()
        c = Cupon("PROMO5000", "monto_fijo", 5000, venc, 10)
        desc, _ = c.calcular_descuento(40000)
        self.assertEqual(desc, 5000)

    def test_cupon_vencido(self):
        ayer = (date.today() - timedelta(days=1)).isoformat()
        c = Cupon("VIEJO", "porcentaje", 15, ayer, 10)
        ok, msg = c.validar()
        desc, _ = c.calcular_descuento(20000)
        self.assertFalse(ok)
        self.assertEqual(desc, 0.0)

    def test_cupon_sin_usos(self):
        venc = (date.today() + timedelta(days=5)).isoformat()
        c = Cupon("AGOTADO", "porcentaje", 10, venc, 3, usos=3)
        ok, msg = c.validar()
        self.assertFalse(ok)

    def test_descuento_tope_subtotal(self):
        venc = (date.today() + timedelta(days=5)).isoformat()
        c = Cupon("ALTO", "monto_fijo", 50000, venc, 5)
        desc, _ = c.calcular_descuento(30000)
        self.assertEqual(desc, 30000)


if __name__ == "__main__":
    unittest.main()