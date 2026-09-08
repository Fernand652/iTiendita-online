"""Tests de persistencia JSON (unittest, stdlib)."""
import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persistencia.gestor_persistencia import (
    cargar_json,
    guardar_json,
    migrar_csv_a_json,
)


class TestPersistencia(unittest.TestCase):
    def test_cargar_faltante_retorna_default(self):
        self.assertEqual(cargar_json("/tmp/no_existe_xyz_123.json", default=[]), [])
        self.assertIsNone(cargar_json("/tmp/no_existe_xyz_123.json", default=None))

    def test_guardar_cargar_roundtrip(self):
        ruta = tempfile.mktemp(suffix=".json")
        try:
            datos = [{"id": 1, "nombre": "A"}, {"id": 2, "nombre": "B"}]
            guardar_json(ruta, datos)
            self.assertEqual(cargar_json(ruta, default=None), datos)
        finally:
            if os.path.exists(ruta):
                os.remove(ruta)

    def test_corrupto_retorna_default(self):
        ruta = tempfile.mktemp(suffix=".json")
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("{json roto,,,")
            self.assertEqual(cargar_json(ruta, default=[]), [])
        finally:
            if os.path.exists(ruta):
                os.remove(ruta)

    def test_migrar_csv_agrega_sin_pisar(self):
        d = tempfile.mkdtemp()
        csv_path = os.path.join(d, "productos.csv")
        json_path = os.path.join(d, "productos.json")
        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["ID", "Nombre", "Precio", "Stock", "Categoria"])
                w.writerow([10, "CsvProd", 1000, 2, "Cat"])
                w.writerow([1, "Duplicado", 5, 1, "Cat"])
            guardar_json(json_path, [{"id": 1, "nombre": "Ya", "precio": 9,
                                      "stock": 1, "categoria": "Cat", "imagen": None}])
            final = migrar_csv_a_json(csv_path=csv_path, json_path=json_path)
            ids = sorted(p["id"] for p in final)
            self.assertEqual(ids, [1, 10])
        finally:
            for p in (csv_path, json_path):
                if os.path.exists(p):
                    os.remove(p)
            os.rmdir(d)


if __name__ == "__main__":
    unittest.main()
