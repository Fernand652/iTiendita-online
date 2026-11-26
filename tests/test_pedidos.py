import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos.pedido import EstadoPedido
from persistencia.gestor_pedidos import GestorPedidos


class TestPedidos(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.gestor = GestorPedidos(archivo=os.path.join(self.tempdir, "pedidos.json"))
        self.pedido = self.gestor.crear_desde_venta({
            "id_venta": 12, "cliente": "ana", "total": 15000,
            "items": [{"id": 2, "cantidad": 3}],
        })

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_crea_pedido_pendiente_unico(self):
        self.assertEqual(self.pedido["estado"], EstadoPedido.PENDIENTE)
        self.assertTrue(self.pedido["id_pedido"].startswith("P-"))
        self.assertEqual(self.gestor.crear_desde_venta({"id_venta": 12}), self.pedido)

    def test_cancelar_pendiente_y_bloquear_segunda_cancelacion(self):
        ok, _, cancelado = self.gestor.cancelar(self.pedido["id_pedido"])
        self.assertTrue(ok)
        self.assertEqual(cancelado["estado"], EstadoPedido.CANCELADO)
        ok, _, _ = self.gestor.cancelar(self.pedido["id_pedido"])
        self.assertFalse(ok)

    def test_no_permite_cancelar_despachado(self):
        self.gestor.avanzar(self.pedido["id_pedido"])
        self.gestor.avanzar(self.pedido["id_pedido"])
        ok, _, pedido = self.gestor.cancelar(self.pedido["id_pedido"])
        self.assertFalse(ok)
        self.assertEqual(pedido["estado"], EstadoPedido.DESPACHADO)


if __name__ == "__main__":
    unittest.main()
