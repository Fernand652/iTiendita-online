"""
test_red.py
============================
Pruebas de la capa de sockets: protocolo y servidor real.

Estas pruebas NO usan mocks para el servidor: levantan un socket de verdad en
127.0.0.1 con un puerto libre y se comunican con él, que es la única forma de
verificar de verdad que lo que viaja por el cable tiene sentido.

Para correr:
    python -m unittest discover -s tests
    python -m unittest tests.test_red -v
"""

import os
import shutil
import socket
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos.inventario import Inventario
from modelos.producto import Producto

from red.protocolo import (
    empaquetar, desempaquetar, extraer_mensajes, normalizar_items,
    items_a_lista, carrito_a_mensaje, normalizar_items as _norm,
    T_REGISTRO, T_CARRITO, T_QUITAR, T_VACIAR, T_PAGO,
    T_INVENTARIO, T_STOCK, T_CARRITO_ESTADO, T_PAGO_OK,
    T_CARRITOS, T_ERROR,
)
from red.servidor import ServidorCarritos


# ==============================================================================
# PROTOCOLO
# ==============================================================================

class TestProtocolo(unittest.TestCase):
    """El idioma: dict -> JSON + \\n -> dict."""

    def test_ida_y_vuelta_de_un_mensaje(self):
        original = {"type": T_CARRITO, "usuario": "ana",
                    "items": [{"id": 1, "cantidad": 2}]}
        self.assertEqual(desempaquetar(empaquetar(original)), original)

    def test_el_mensaje_termina_en_salto_de_linea(self):
        # El \n es el separador: sin él el receptor no puede saber que
        # terminó el mensaje.
        self.assertTrue(empaquetar({"type": "x"}).endswith(b"\n"))

    def test_acepta_acentos(self):
        original = {"type": "x", "nombre": "Cafetera Ñandú"}
        self.assertEqual(desempaquetar(empaquetar(original)), original)

    def test_linea_corrupta_no_rompe(self):
        self.assertIsNone(desempaquetar(b"esto no es json"))
        self.assertIsNone(desempaquetar(b"\xff\xfe no utf8"))

    def test_carrito_a_mensaje(self):
        mensaje = carrito_a_mensaje("ana", [{"id": 1, "cantidad": 2},
                                            {"id": 3, "cantidad": 1}])
        self.assertEqual(mensaje["type"], T_CARRITO)
        self.assertEqual(mensaje["usuario"], "ana")
        self.assertEqual(mensaje["items"],
                         [{"id": 1, "cantidad": 2}, {"id": 3, "cantidad": 1}])


class TestExtraerMensajes(unittest.TestCase):
    """
    recv(4096) devuelve bytes pelados: puede llegar la MITAD de un mensaje, o
    tres mensajes completos de un tirón. Acá se prueba el buffer.
    """

    def test_mensaje_completo(self):
        mensajes, buffer = extraer_mensajes("", empaquetar({"type": "hola"}))
        self.assertEqual(mensajes, [{"type": "hola"}])
        self.assertEqual(buffer, "")

    def test_medio_mensaje_se_arma_al_llegar_el_resto(self):
        entero = empaquetar({"type": T_CARRITO, "items": []})
        mensajes, buffer = extraer_mensajes("", entero[:10])
        self.assertEqual(mensajes, [])          # todavía no hay \n

        mensajes, buffer = extraer_mensajes(buffer, entero[10:])
        self.assertEqual(mensajes, [{"type": T_CARRITO, "items": []}])
        self.assertEqual(buffer, "")

    def test_varios_mensajes_en_un_solo_recv(self):
        datos = empaquetar({"type": "a"}) + empaquetar({"type": "b"})
        mensajes, buffer = extraer_mensajes("", datos)
        self.assertEqual([m["type"] for m in mensajes], ["a", "b"])
        self.assertEqual(buffer, "")

    def test_lo_que_sobra_queda_para_la_proxima_lectura(self):
        datos = empaquetar({"type": "a"}) + b'{"type": "b"'
        mensajes, buffer = extraer_mensajes("", datos)
        self.assertEqual(len(mensajes), 1)
        self.assertEqual(buffer, '{"type": "b"')

    def test_lineas_vacias_y_basura_se_ignoran(self):
        mensajes, buffer = extraer_mensajes("", b"\n\nesto no es json\n")
        self.assertEqual(mensajes, [])
        self.assertEqual(buffer, "")


class TestNormalizarItems(unittest.TestCase):
    """Limpieza de la lista de items que llega del cliente."""

    def test_une_duplicados(self):
        self.assertEqual(normalizar_items([{"id": 1, "cantidad": 2},
                                           {"id": 1, "cantidad": 3}]), {1: 5})

    def test_descarta_cantidades_cero_o_negativas(self):
        self.assertEqual(normalizar_items([{"id": 1, "cantidad": 0},
                                           {"id": 2, "cantidad": -3}]), {})

    def test_ignora_basura(self):
        self.assertEqual(normalizar_items([{"id": "uno", "cantidad": 2},
                                           "no soy un dict",
                                           {"cantidad": 2}]), {})

    def test_ida_y_vuelta_por_la_lista(self):
        pedido = {2: 1, 1: 3}
        self.assertEqual(normalizar_items(items_a_lista(pedido)), pedido)


# ==============================================================================
# SERVIDOR REAL CON SOCKETS
# ==============================================================================

def _puerto_libre():
    """
    Le pide al sistema operativo un puerto libre (bind en el puerto 0).

    Cada test usa un puerto distinto: si todos usaran el mismo, el servidor
    del test anterior puede quedar cerrándose mientras el siguiente abre el
    mismo puerto, y los clientes se conectan al servidor equivocado.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _ClienteFalso:
    """Cliente mínimo por socket para hablar con el servidor en tests."""

    def __init__(self, puerto):
        self.sock = socket.create_connection(("127.0.0.1", puerto), timeout=3)
        self.sock.settimeout(3)
        self.buffer = ""

    def enviar(self, mensaje):
        self.sock.sendall(empaquetar(mensaje))

    def leer(self):
        """Lee hasta armar un mensaje completo (misma lógica del cliente real)."""
        while "\n" not in self.buffer:
            datos = self.sock.recv(4096)
            if not datos:
                raise AssertionError("El servidor cerró la conexión")
            self.buffer += datos.decode("utf-8")
        linea, self.buffer = self.buffer.split("\n", 1)
        mensaje = desempaquetar(linea)
        if mensaje is None:
            raise AssertionError(f"Mensaje ilegible: {linea!r}")
        return mensaje

    def esperar(self, tipo, maximo=20):
        """Lee hasta encontrar un mensaje del tipo pedido."""
        for _ in range(maximo):
            mensaje = self.leer()
            if mensaje.get("type") == tipo:
                return mensaje
        raise AssertionError(f"Nunca llegó un mensaje de tipo {tipo}")

    def buscar(self, tipo, predicado, maximo=20):
        """Como esperar(), pero acepta el primer mensaje que cumpla la condición."""
        for _ in range(maximo):
            mensaje = self.leer()
            if mensaje.get("type") == tipo and predicado(mensaje):
                return mensaje
        raise AssertionError(f"Nunca llegó un {tipo} que cumpla la condición")

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


class TestServidorCarritos(unittest.TestCase):
    """
    Prueba el mecanismo de comunicación contra el servidor real:
      - el cliente se registra y recibe el catálogo
      - el carrito del cliente descuenta stock de verdad
      - si no hay stock, el servidor corrige al cliente
      - varios clientes a la vez, cada uno con su carrito
      - al vaciar o desconectar, el stock vuelve
    """

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.ruta = os.path.join(self.tempdir, "productos.json")

        inventario = Inventario(archivo=self.ruta)
        inventario.productos = []
        inventario._guardar()
        inventario.agregar_producto("Producto A", 1000, 3, "Cat")   # id 1
        inventario.agregar_producto("Producto B", 2000, 5, "Cat")   # id 2
        self.inventario = inventario

        # Loopback + puerto libre por test, así no se pisan entre sí.
        self.puerto = _puerto_libre()
        self.servidor = ServidorCarritos(
            inventario, host="127.0.0.1", puerto=self.puerto
        )
        self.servidor.start()
        self._esperar_arranque()
        self.clientes = []

    def tearDown(self):
        for cliente in self.clientes:
            cliente.cerrar()
        self.servidor.detener()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    # -- helpers ------------------------------------------------------
    def _esperar_arranque(self):
        for _ in range(60):
            if self.servidor.activo:
                return
            if self.servidor.error:
                self.fail(self.servidor.error)
            time.sleep(0.05)
        self.fail("El servidor no arrancó")

    def _cliente(self, usuario):
        cliente = _ClienteFalso(self.puerto)
        self.clientes.append(cliente)
        cliente.registrar(usuario)
        return cliente

    def _stock(self, id_producto):
        return self.inventario.buscar_por_id(id_producto).stock

    def _esperar(self, condicion, descripcion):
        """
        Espera a que se cumpla una condición.

        Toma el candado del servidor mientras mira, porque si no se puede ver
        un estado intermedio: el servidor descuenta el stock y recien después
        saca el carrito del diccionario, y un test que mire justo en ese
        medio segundo ve el stock devuelto con el carrito todavía anotado.
        """
        for _ in range(60):
            with self.servidor._lock:
                if condicion():
                    return
            time.sleep(0.05)
        with self.servidor._lock:
            self.fail(descripcion)

    def _esperar_stock(self, id_producto, esperado):
        self._esperar(
            lambda: self._stock(id_producto) == esperado,
            f"El stock de {id_producto} quedó en {self._stock(id_producto)}, "
            f"se esperaba {esperado}",
        )

    # -- tests --------------------------------------------------------
    def test_registro_recibe_el_catalogo(self):
        cliente = self._cliente("ana")
        # _cliente() ya consumió el T_INVENTARIO del registro. Ahora pedimos
        # el catálogo de nuevo con otro cliente para poder mirarlo de cerca.
        otro = _ClienteFalso(self.puerto)
        self.clientes.append(otro)
        otro.enviar({"type": T_REGISTRO, "usuario": "beto", "rol": "normal"})
        catalogo = otro.esperar(T_INVENTARIO)
        self.assertEqual([p["id"] for p in catalogo["productos"]], [1, 2])
        self.assertEqual(catalogo["productos"][0]["stock"], 3)
        self.assertEqual(catalogo["productos"][0]["nombre"], "Producto A")

    def test_agregar_al_carrito_descuenta_stock(self):
        cliente = self._cliente("ana")
        cliente.mandar_carrito("ana", [{"id": 1, "cantidad": 2}])
        self._esperar_stock(1, 1)                      # 3 - 2
        self.assertEqual(self.servidor.carritos["ana"], {1: 2})

    def test_si_no_alcanza_el_stock_el_servidor_corrige(self):
        """
        El cliente pidió 4 pero hay 3. El servidor sirve lo que puede y le
        devuelve el carrito REAL para que la pantalla se corrija.
        """
        cliente = self._cliente("ana")
        cliente.mandar_carrito("ana", [{"id": 1, "cantidad": 4}])
        correccion = cliente.esperar(T_CARRITO_ESTADO)
        self.assertEqual(correccion["items"], [{"id": 1, "cantidad": 3}])
        self._esperar_stock(1, 0)
        self.assertEqual(self.servidor.carritos["ana"], {1: 3})

    def test_quitar_un_producto_devuelve_el_stock(self):
        cliente = self._cliente("ana")
        cliente.mandar_carrito("ana", [{"id": 1, "cantidad": 2}])
        self._esperar_stock(1, 1)
        cliente.enviar({"type": T_QUITAR, "usuario": "ana", "id": 1, "cantidad": 1})
        cliente.esperar(T_STOCK)
        self._esperar_stock(1, 2)                      # vuelve 1 unidad
        self.assertEqual(self.servidor.carritos["ana"], {1: 1})

    def test_vaciar_devuelve_todo_el_stock(self):
        cliente = self._cliente("ana")
        cliente.mandar_carrito("ana", [{"id": 1, "cantidad": 3}])
        self._esperar_stock(1, 0)
        cliente.enviar({"type": T_VACIAR, "usuario": "ana"})
        cliente.esperar(T_CARRITO_ESTADO)
        self._esperar_stock(1, 3)
        self.assertNotIn("ana", self.servidor.carritos)

    def test_dos_clientes_tienen_su_propio_carrito(self):
        ana = self._cliente("ana")
        beto = self._cliente("beto")
        ana.mandar_carrito("ana", [{"id": 1, "cantidad": 1}])
        beto.mandar_carrito("beto", [{"id": 2, "cantidad": 2}])
        self._esperar_stock(1, 2)
        self._esperar_stock(2, 3)
        self.assertEqual(self.servidor.carritos["ana"], {1: 1})
        self.assertEqual(self.servidor.carritos["beto"], {2: 2})

    def test_la_ultima_unidad_no_se_puede_dar_dos_veces(self):
        """
        Ana pide todo el stock, y al mismo tiempo Beto pide lo que queda.
        Gana una sola: las unidades no se duplican.
        """
        ana = self._cliente("ana")
        beto = self._cliente("beto")
        ana.mandar_carrito("ana", [{"id": 1, "cantidad": 3}])
        beto.mandar_carrito("beto", [{"id": 1, "cantidad": 3}])
        self._esperar_stock(1, 0)
        total = sum(cant for carrito in self.servidor.carritos.values()
                    for pid, cant in carrito.items() if pid == 1)
        self.assertEqual(total, 3, "Se vendieron más unidades de las que hay")

    def test_desconectar_devuelve_el_stock(self):
        cliente = self._cliente("ana")
        cliente.mandar_carrito("ana", [{"id": 1, "cantidad": 2}])
        self._esperar_stock(1, 1)
        cliente.cerrar()
        self.clientes.remove(cliente)
        # Ya no hay nadie mirando esa pantalla: el stock vuelve y el carrito
        # se borra. Las dos cosas tienen que estar listas JUNTAS, por eso
        # esperamos la condición completa y no el stock por separado.
        self._esperar(
            lambda: self._stock(1) == 3 and "ana" not in self.servidor.carritos,
            "Al desconectar de ana el stock no volvió o el carrito quedó anotado",
        )

    def test_el_admin_recibe_los_carritos_por_la_bandeja(self):
        """El ADMIN lee T_CARRITOS de la bandeja del servidor (sin tocar Tk)."""
        cliente = self._cliente("ana")
        cliente.mandar_carrito("ana", [{"id": 1, "cantidad": 2}])

        for _ in range(60):
            mensaje = self.servidor.sacar_evento()
            if mensaje and mensaje.get("type") == T_CARRITOS:
                if mensaje.get("carritos", {}).get("ana"):
                    self.assertEqual(mensaje["carritos"]["ana"],
                                     [{"id": 1, "cantidad": 2}])
                    self.assertIn("ana", mensaje["conectados"])
                    return
            time.sleep(0.05)
        self.fail("El admin nunca recibió el carrito de ana")

    def test_pagar_registra_la_venta_y_limpia_el_carrito(self):
        cliente = self._cliente("ana")
        cliente.mandar_carrito("ana", [{"id": 1, "cantidad": 2}])
        self._esperar_stock(1, 1)
        cliente.enviar({"type": T_PAGO, "usuario": "ana"})
        ok = cliente.esperar(T_PAGO_OK)
        # 2 x 1000
        self.assertEqual(ok["total"], 2000)
        # El pago NO devuelve el stock: ya se cobró.
        self._esperar_stock(1, 1)
        self.assertNotIn("ana", self.servidor.carritos)

    def test_pagar_sin_carrito_avisa_error(self):
        cliente = self._cliente("ana")
        cliente.enviar({"type": T_PAGO, "usuario": "ana"})
        error = cliente.esperar(T_ERROR)
        self.assertIn("vacío", error["mensaje"])
