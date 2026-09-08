"""Tests del modelo de usuarios (unittest, stdlib)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos.usuario import GestorUsuarios


def _tmp():
    return tempfile.mktemp(suffix=".json")


class TestGestorUsuarios(unittest.TestCase):
    def setUp(self):
        self.archivo = _tmp()
        self.g = GestorUsuarios(archivo=self.archivo)

    def tearDown(self):
        if os.path.exists(self.archivo):
            os.remove(self.archivo)

    def test_seed_admin(self):
        self.assertTrue(self.g.verificar_usuario("admin", "1234"))
        self.assertTrue(self.g.es_admin("admin"))

    def test_registro_siempre_normal(self):
        u = self.g.registrar_usuario("juan", "clave")
        self.assertIsNotNone(u)
        self.assertEqual(u.rol, "normal")
        self.assertFalse(self.g.es_admin("juan"))

    def test_registro_duplicado_insensitive(self):
        self.g.registrar_usuario("Juan", "a")
        self.assertIsNone(self.g.registrar_usuario("juan", "b"))
        self.assertIsNone(self.g.registrar_usuario("JUAN", "c"))

    def test_registro_vacio_none(self):
        self.assertIsNone(self.g.registrar_usuario("   ", "x"))
        self.assertIsNone(self.g.registrar_usuario("y", ""))

    def test_verificar(self):
        self.g.registrar_usuario("ana", "1234")
        self.assertTrue(self.g.verificar_usuario("ana", "1234"))
        self.assertTrue(self.g.verificar_usuario("ANA", "1234"))
        self.assertFalse(self.g.verificar_usuario("ana", "mal"))
        self.assertFalse(self.g.verificar_usuario("nadie", "1234"))

    def test_es_admin_casos(self):
        self.g.registrar_usuario("normal1", "x")
        self.assertTrue(self.g.es_admin("admin"))
        self.assertFalse(self.g.es_admin("normal1"))
        self.assertFalse(self.g.es_admin(None))
        self.assertFalse(self.g.es_admin("noexiste"))

    def test_migracion_legacy_sin_rol(self):
        legacy = [
            {"nombre": "admin", "password": "1234"},
            {"nombre": "viejo", "password": "pw"},
        ]
        with open(self.archivo, "w", encoding="utf-8") as f:
            json.dump(legacy, f)
        g2 = GestorUsuarios(archivo=self.archivo)
        self.assertTrue(g2.es_admin("admin"))
        self.assertFalse(g2.es_admin("viejo"))

    def test_persistencia_roundtrip(self):
        self.g.registrar_usuario("pers", "pw")
        g2 = GestorUsuarios(archivo=self.archivo)
        self.assertTrue(g2.verificar_usuario("pers", "pw"))
        self.assertFalse(g2.es_admin("pers"))


if __name__ == "__main__":
    unittest.main()