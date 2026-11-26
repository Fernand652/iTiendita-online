"""Tests del seguimiento de pedidos y su cancelación (unittest, stdlib)."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos.pedido import EstadoPedido, Pedido
from persistencia.gestor_pedidos import GestorPedidos


def _venta(id_venta=1, cliente="ana", cantidad=2):
    return {
        "id_venta": id_venta,
        "cliente": cliente,
        "items": [{"id": 1, "nombre": "Producto A", "precio": 1000,
                   "cantidad": cantidad, "subtotal": 1000 * cantidad}],
        "total": 2380.0,
        "fecha": "2026-01-01T10:00:00",
    }


class TestPedidoEstados(unittest.TestCase):
    def _pedido(self, estado=EstadoPedido.PENDIENTE):
        return Pedido("P-000001", 1, "ana",
                      [{"id": 1, "cantidad": 2}], 2380.0, estado)

    def test_estado_inicial_pendiente(self):
        pedido = self._pedido()
        self.assertEqual(pedido.estado, EstadoPedido.PENDIENTE)
        self.assertTrue(pedido.puede_avanzar)

    def test_avanzar_recorre_el_flujo_hasta_entregado(self):
        pedido = self._pedido()
        for esperado in (EstadoPedido.EN_PREPARACION,
                         EstadoPedido.DESPACHADO,
                         EstadoPedido.ENTREGADO):
            ok, _mensaje = pedido.avanzar()
            self.assertTrue(ok)
            self.assertEqual(pedido.estado, esperado)
        ok, mensaje = pedido.avanzar()
        self.assertFalse(ok)
        self.assertIn("entregado", mensaje.lower())

    def test_cancelar_permitido_antes_de_despachar(self):
        for estado in (EstadoPedido.PENDIENTE, EstadoPedido.EN_PREPARACION):
            pedido = self._pedido(estado)
            ok, _mensaje, restaurar = pedido.cancelar()
            self.assertTrue(ok)
            self.assertTrue(restaurar)
            self.assertEqual(pedido.estado, EstadoPedido.CANCELADO)

    def test_cancelar_rechazado_despachado_o_entregado(self):
        for estado in (EstadoPedido.DESPACHADO, EstadoPedido.ENTREGADO):
            pedido = self._pedido(estado)
            ok, _mensaje, restaurar = pedido.cancelar()
            self.assertFalse(ok)
            self.assertFalse(restaurar)
            self.assertEqual(pedido.estado, estado)

    def test_cancelado_no_avanza(self):
        pedido = self._pedido(EstadoPedido.CANCELADO)
        ok, _mensaje = pedido.avanzar()
        self.assertFalse(ok)


class TestGestorPedidos(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.archivo = os.path.join(self.tempdir, "pedidos.json")
        self.gestor = GestorPedidos(archivo=self.archivo)

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_crear_desde_venta_genera_pendiente_y_numero_unico(self):
        primero = self.gestor.crear_desde_venta(_venta(1))
        segundo = self.gestor.crear_desde_venta(_venta(2))
        self.assertEqual(primero["estado"], EstadoPedido.PENDIENTE)
        self.assertEqual(primero["id_pedido"], "P-000001")
        self.assertEqual(segundo["id_pedido"], "P-000002")

    def test_cancelar_persiste_y_una_segunda_vez_falla(self):
        pedido = self.gestor.crear_desde_venta(_venta(1))
        ok, _mensaje, cancelado = self.gestor.cancelar(pedido["id_pedido"])
        self.assertTrue(ok)
        self.assertEqual(cancelado["estado"], EstadoPedido.CANCELADO)

        recargado = GestorPedidos(archivo=self.archivo)
        self.assertEqual(recargado.obtener(pedido["id_pedido"])["estado"],
                         EstadoPedido.CANCELADO)

        ok, _mensaje, cancelado = self.gestor.cancelar(pedido["id_pedido"])
        self.assertFalse(ok)
        self.assertEqual(cancelado["estado"], EstadoPedido.CANCELADO)

    def test_no_se_puede_cancelar_despues_de_despachar(self):
        pedido = self.gestor.crear_desde_venta(_venta(1))
        self.gestor.avanzar(pedido["id_pedido"])
        self.gestor.avanzar(pedido["id_pedido"])
        ok, mensaje, actual = self.gestor.cancelar(pedido["id_pedido"])
        self.assertFalse(ok)
        self.assertIn("despachar", mensaje.lower())
        self.assertEqual(actual["estado"], EstadoPedido.DESPACHADO)

    def test_cancelar_inexistente(self):
        ok, mensaje, pedido = self.gestor.cancelar("P-999999")
        self.assertFalse(ok)
        self.assertIsNone(pedido)
        self.assertIn("no encontrado", mensaje.lower())


if __name__ == "__main__":
    unittest.main()
