"""Pruebas del modelo de despacho: tarifas, envío gratis y datos de entrega."""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos.despacho import (
    Despacho,
    Direccion,
    TarifaEnvio,
    _sumar_dias_habiles,
)


class TestDespacho(unittest.TestCase):
    def setUp(self):
        Despacho.aplicar_config(Despacho.config_por_defecto())

    def tearDown(self):
        Despacho.aplicar_config(Despacho.config_por_defecto())

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

    def test_validar_domicilio_incompleto(self):
        ok, motivo = Despacho("domicilio", "Maule", "", "Av. 1", "Talca").validar()
        self.assertFalse(ok)
        self.assertIn("recibe", motivo)

    def test_validar_domicilio_completo(self):
        d = Despacho("domicilio", "Maule", "Ana", "Av. 1", "Talca")
        self.assertEqual(d.validar(), (True, ""))

    def test_validar_retiro_sin_datos(self):
        self.assertEqual(Despacho().validar(), (True, ""))

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

    def test_configuracion_cambia_tarifas_y_envio_gratis(self):
        config = Despacho.config_por_defecto()
        config["tarifas"]["Maule"] = 1234
        config["envio_gratis_desde"] = 50000
        Despacho.aplicar_config(config)
        self.assertEqual(Despacho("domicilio", "Maule").calcular(40000), 1234)
        self.assertEqual(Despacho("domicilio", "Maule").calcular(50000), 0)
        self.assertEqual(Despacho.ENVIO_GRATIS_DESDE, 50000)

    def test_tarifa_envio_y_direccion(self):
        tarifa = TarifaEnvio({"Maule": 1000}, envio_gratis_desde=5000)
        self.assertEqual(tarifa.calcular("Maule", 1000), 1000)
        self.assertEqual(tarifa.calcular("Maule", 5000), 0)
        self.assertEqual(tarifa.dias_entrega("Maule"), 2)
        self.assertEqual(tarifa.dias_entrega("Biobío"), 5)
        direccion = Direccion("Maule", "Ana", "Av. 1", "Talca")
        self.assertEqual(direccion.validar({"Maule": 4990}), (True, ""))

    def test_sumar_dias_habiles_salta_fin_de_semana(self):
        viernes = date(2026, 11, 13)
        sabado = date(2026, 11, 14)
        self.assertEqual(_sumar_dias_habiles(viernes, 1), date(2026, 11, 16))
        self.assertEqual(_sumar_dias_habiles(sabado, 2), date(2026, 11, 17))

    def test_fecha_estimada_entrega(self):
        viernes = date(2026, 11, 13)
        maule = Despacho("domicilio", "Maule", "Ana", "Av. 1", "Talca")
        metropolitana = Despacho("domicilio", "Metropolitana", "Ana", "Av. 1", "Santiago")
        self.assertEqual(maule.fecha_estimada_entrega(viernes), date(2026, 11, 17))
        self.assertEqual(
            metropolitana.fecha_estimada_entrega(viernes), date(2026, 11, 20)
        )
        self.assertIsNone(Despacho("retiro", "Maule").fecha_estimada_entrega(viernes))

    def test_to_dict_incluye_fecha_estimada(self):
        despacho = Despacho("domicilio", "Maule", "Ana", "Av. 1", "Talca")
        datos = despacho.to_dict(date(2026, 11, 13))
        self.assertEqual(datos["fecha_estimada_entrega"], "2026-11-17")
        retiro = Despacho("retiro", "Maule").to_dict(date(2026, 11, 13))
        self.assertIsNone(retiro["fecha_estimada_entrega"])


if __name__ == "__main__":
    unittest.main()
