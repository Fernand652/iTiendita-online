"""
test_api_gemini.py
==================
Pruebas del texto que se le manda a Gemini. No hacen llamadas a la API.

Los productos sin stock SIGUEN apareciendo en el catalogo (el asistente puede
mostrarlos); el bloqueo se hace al intentar agregarlos, no al armar el texto.

Para correr:
    python -m unittest tests.test_api_gemini -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos.api_gemini import armar_catalogo, armar_instruccion


class TestCatalogoParaGemini(unittest.TestCase):

    def test_muestra_todos_incluso_los_sin_stock(self):
        catalogo = armar_catalogo([
            {"nombre": "Con stock", "precio": 100, "stock": 3},
            {"nombre": "Agotado", "precio": 200, "stock": 0},
        ])
        self.assertIn("Con stock", catalogo)
        self.assertIn("Agotado", catalogo)
        self.assertIn("stock: 0", catalogo)
        self.assertNotIn("PRODUCTOS SIN STOCK", catalogo)

    def test_instruccion_avisa_si_quieren_agregar_sin_stock(self):
        instruccion = armar_instruccion([
            {"nombre": "Agotado", "precio": 200, "stock": 0},
        ])
        self.assertIn("stock 0", instruccion)
        self.assertIn("no hay existencias", instruccion)

    def test_catalogo_vacio(self):
        self.assertEqual(armar_catalogo([]), "(sin productos)")


if __name__ == "__main__":
    unittest.main()
