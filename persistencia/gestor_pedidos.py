"""Persistencia y transiciones de pedidos."""
import re
import threading

from modelos.pedido import Pedido
from persistencia.gestor_persistencia import (
    RUTA_PEDIDOS_JSON, cargar_json, guardar_json,
)


class GestorPedidos:
    def __init__(self, archivo=None):
        self.archivo = archivo or RUTA_PEDIDOS_JSON
        self._lock = threading.RLock()
        self._pedidos = []
        self.recargar()

    def recargar(self):
        with self._lock:
            datos = cargar_json(str(self.archivo), default=[]) or []
            if not isinstance(datos, list):
                datos = []
            pedidos = []
            for item in datos:
                try:
                    pedidos.append(Pedido.from_dict(item))
                except (TypeError, ValueError):
                    continue
            self._pedidos = pedidos
            return [p.to_dict() for p in pedidos]

    def _guardar(self):
        guardar_json(str(self.archivo), [p.to_dict() for p in self._pedidos])

    def todos(self):
        with self._lock:
            return [p.to_dict() for p in self._pedidos]

    def de_cliente(self, cliente):
        cliente = str(cliente or "").strip()
        with self._lock:
            return [p.to_dict() for p in self._pedidos if p.cliente == cliente]

    def obtener(self, id_pedido):
        id_pedido = str(id_pedido)
        with self._lock:
            for pedido in self._pedidos:
                if pedido.id_pedido == id_pedido:
                    return pedido.to_dict()
        return None

    def _siguiente_id(self):
        maximo = 0
        for pedido in self._pedidos:
            coincidencia = re.fullmatch(r"P-(\d+)", pedido.id_pedido)
            if coincidencia:
                maximo = max(maximo, int(coincidencia.group(1)))
        return f"P-{maximo + 1:06d}"

    def crear_desde_venta(self, venta):
        if not isinstance(venta, dict):
            raise ValueError("Venta inválida")
        with self._lock:
            id_venta = venta.get("id_venta")
            if id_venta is not None:
                for existente in self._pedidos:
                    if str(existente.id_venta) == str(id_venta):
                        return existente.to_dict()
            pedido = Pedido.desde_venta(venta)
            pedido.id_pedido = self._siguiente_id()
            self._pedidos.append(pedido)
            self._guardar()
            return pedido.to_dict()

    def avanzar(self, id_pedido):
        id_pedido = str(id_pedido)
        with self._lock:
            for pedido in self._pedidos:
                if pedido.id_pedido == id_pedido:
                    ok, mensaje = pedido.avanzar()
                    if ok:
                        self._guardar()
                    return ok, mensaje, pedido.to_dict()
        return False, "Pedido no encontrado", None
