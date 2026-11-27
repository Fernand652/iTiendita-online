

import os
import shutil
import socket
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos.despacho import Despacho
from modelos.inventario import Inventario
from persistencia.gestor_pedidos import GestorPedidos
from persistencia.gestor_tarifas import GestorTarifas
from red import servidor as servidor_mod
from red.protocolo import (
    T_CARRITO,
    T_CARRITO_ESTADO,
    T_INVENTARIO,
    T_REGISTRO,
    T_STOCK,
    desempaquetar,
    empaquetar,
)
from red.servidor import ServidorCarritos


def _puerto_libre():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class _ClienteSocketPrueba:
    def __init__(self, puerto):
        self.sock = socket.create_connection(("127.0.0.1", puerto), timeout=3)
        self.sock.settimeout(3)
        self.buffer = ""

    def enviar(self, mensaje):
        self.sock.sendall(empaquetar(mensaje))

    def leer(self):
        while "\n" not in self.buffer:
            datos = self.sock.recv(4096)
            if not datos:
                raise AssertionError("El servidor cerró la conexión inesperadamente")
            self.buffer += datos.decode("utf-8")
        linea, self.buffer = self.buffer.split("\n", 1)
        mensaje = desempaquetar(linea)
        if mensaje is None:
            raise AssertionError(f"Mensaje JSON inválido recibido: {linea!r}")
        return mensaje

    def esperar(self, tipo_mensaje, maximo=25):
        for _ in range(maximo):
            mensaje = self.leer()
            if mensaje.get("type") == tipo_mensaje:
                return mensaje
        raise AssertionError(f"No llegó el mensaje de tipo {tipo_mensaje!r}")

    def registrar(self, usuario, rol="normal"):
        self.enviar({"type": T_REGISTRO, "usuario": usuario, "rol": rol})
        return self.esperar(T_INVENTARIO)

    def mandar_carrito(self, usuario, items):
        self.enviar({"type": T_CARRITO, "usuario": usuario, "items": items})

    def cerrar(self):
        try:
            self.sock.close()
        except OSError:
            pass


class TestExpiracionCarrito(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.ruta_productos = os.path.join(self.tempdir, "productos.json")
        self.ruta_ventas = os.path.join(self.tempdir, "ventas.json")
        self._ruta_ventas_original = servidor_mod.RUTA_VENTAS_JSON
        servidor_mod.RUTA_VENTAS_JSON = self.ruta_ventas

        inventario = Inventario(archivo=self.ruta_productos)
        inventario.productos = []
        inventario._guardar()
        inventario.agregar_producto("Consola Retro", 120000, 1, "Consolas")
        inventario.agregar_producto("Cartucho Clásico", 45000, 4, "Juegos")
        self.inventario = inventario

        self.gestor_tarifas = GestorTarifas(
            archivo=os.path.join(self.tempdir, "config_despacho.json")
        )
        self.gestor_pedidos = GestorPedidos(
            archivo=os.path.join(self.tempdir, "pedidos.json")
        )
        Despacho.aplicar_config(Despacho.config_por_defecto())

        self.puerto = _puerto_libre()
        self.servidor = ServidorCarritos(
            self.inventario,
            host="127.0.0.1",
            puerto=self.puerto,
            gestor_tarifas=self.gestor_tarifas,
            gestor_pedidos=self.gestor_pedidos,
        )
        self.servidor.start()
        self._esperar_arranque()
        self.clientes = []

    def tearDown(self):
        servidor_mod.RUTA_VENTAS_JSON = self._ruta_ventas_original
        for cliente in self.clientes:
            cliente.cerrar()
        self.servidor.detener()
        for _ in range(100):
            with self.servidor._lock:
                if not self.servidor.clientes:
                    break
            time.sleep(0.01)
        Despacho.aplicar_config(Despacho.config_por_defecto())
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def _esperar_arranque(self):
        for _ in range(60):
            if self.servidor.activo:
                return
            if self.servidor.error:
                self.fail(self.servidor.error)
            time.sleep(0.05)
        self.fail("El servidor no arrancó a tiempo")

    def _cliente(self, usuario):
        cliente = _ClienteSocketPrueba(self.puerto)
        self.clientes.append(cliente)
        cliente.registrar(usuario)
        return cliente

    def _stock(self, id_producto):
        return self.inventario.buscar_por_id(id_producto).stock

    def _esperar_condicion(self, condicion, descripcion):
        for _ in range(60):
            with self.servidor._lock:
                if condicion():
                    return
            time.sleep(0.05)
        with self.servidor._lock:
            self.fail(descripcion)

    def test_configurar_tiempo_carritos_limites(self):
        ok_min, _ = self.servidor.configurar_tiempo_carritos(1)
        self.assertTrue(ok_min)
        self.assertEqual(self.servidor.tiempo_limite_carritos_minutos, 1)

        ok_max, _ = self.servidor.configurar_tiempo_carritos(120)
        self.assertTrue(ok_max)
        self.assertEqual(self.servidor.tiempo_limite_carritos_minutos, 120)

        for invalido in (0, -3, 121, "abc", None):
            ok, _ = self.servidor.configurar_tiempo_carritos(invalido)
            self.assertFalse(ok, f"Debió rechazar {invalido!r}")

    def test_expiracion_libera_stock_y_avisa_al_cliente(self):
        ana = self._cliente("ana")
        ana.mandar_carrito("ana", [{"id": 1, "cantidad": 1}])
        self._esperar_condicion(
            lambda: self._stock(1) == 0 and self.servidor.carritos.get("ana") == {1: 1},
            "Ana no reservó la unidad del producto 1",
        )

        with self.servidor._lock:
            self.servidor.carritos_timestamps["ana"] = time.time() - (
                self.servidor.tiempo_limite_carritos_minutos * 60 + 5
            )

        self.servidor.verificar_carritos_expirados()

        self.assertEqual(self._stock(1), 1)
        self.assertNotIn("ana", self.servidor.carritos)
        estado = ana.esperar(T_CARRITO_ESTADO)
        self.assertTrue(estado.get("expirado"))
        self.assertEqual(estado.get("items"), [])
        aviso_stock = ana.esperar(T_STOCK)
        self.assertEqual(aviso_stock.get("id"), 1)
        self.assertEqual(aviso_stock.get("stock"), 1)

    def test_modificar_carrito_renueva_reserva_y_no_expira_prematuramente(self):
        ana = self._cliente("ana")
        ana.mandar_carrito("ana", [{"id": 2, "cantidad": 1}])
        self._esperar_condicion(
            lambda: self._stock(2) == 3 and self.servidor.carritos.get("ana") == {2: 1},
            "Ana no reservó inicialmente el producto 2",
        )

        limite_seg = self.servidor.tiempo_limite_carritos_minutos * 60
        with self.servidor._lock:
            self.servidor.carritos_timestamps["ana"] = time.time() - (limite_seg - 2)

        ana.mandar_carrito("ana", [{"id": 2, "cantidad": 2}])
        self._esperar_condicion(
            lambda: self._stock(2) == 2 and self.servidor.carritos.get("ana") == {2: 2},
            "Ana no actualizó su carrito a 2 unidades",
        )

        with self.servidor._lock:
            self.servidor.carritos_timestamps["ana"] -= 5

        self.servidor.verificar_carritos_expirados()

        self.assertEqual(self._stock(2), 2)
        self.assertEqual(self.servidor.carritos.get("ana"), {2: 2})

    def test_stock_liberado_por_expiracion_queda_disponible_para_otro_cliente(self):
        ana = self._cliente("ana")
        beto = self._cliente("beto")

        ana.mandar_carrito("ana", [{"id": 1, "cantidad": 1}])
        self._esperar_condicion(
            lambda: self._stock(1) == 0,
            "El producto 1 debía quedar con stock 0 reservado por ana",
        )

        with self.servidor._lock:
            self.servidor.carritos_timestamps["ana"] = time.time() - (
                self.servidor.tiempo_limite_carritos_minutos * 60 + 5
            )
        self.servidor.verificar_carritos_expirados()
        self.assertEqual(self._stock(1), 1)

        beto.mandar_carrito("beto", [{"id": 1, "cantidad": 1}])
        self._esperar_condicion(
            lambda: self._stock(1) == 0 and self.servidor.carritos.get("beto") == {1: 1},
            "Beto debía poder reservar la unidad liberada tras expirar el carrito de ana",
        )


if __name__ == "__main__":
    unittest.main()