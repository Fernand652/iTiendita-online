"""Pedido y sus estados para el seguimiento del hito 4."""
from datetime import datetime


class EstadoPedido:
    PENDIENTE = "Pendiente"
    EN_PREPARACION = "En preparación"
    DESPACHADO = "Despachado"
    ENTREGADO = "Entregado"
    CANCELADO = "Cancelado"
    FLUJO = (PENDIENTE, EN_PREPARACION, DESPACHADO, ENTREGADO)
    CANCELABLES = (PENDIENTE, EN_PREPARACION)
    TODOS = FLUJO + (CANCELADO,)


class Pedido:
    def __init__(self, id_pedido, id_venta, cliente, items=None, total=0.0,
                 estado=EstadoPedido.PENDIENTE, fecha=None):
        self.id_pedido = str(id_pedido)
        self.id_venta = id_venta
        self.cliente = cliente
        self.items = list(items or [])
        self.total = float(total or 0)
        self.estado = estado if estado in EstadoPedido.TODOS else EstadoPedido.PENDIENTE
        self.fecha = fecha or datetime.now().isoformat(timespec="seconds")

    @classmethod
    def desde_venta(cls, venta):
        id_venta = venta.get("id_venta")
        codigo = f"P-{id_venta}" if id_venta else f"P-{datetime.now():%Y%m%d%H%M%S}"
        return cls(codigo, id_venta, venta.get("cliente") or "Invitado",
                   venta.get("items") or venta.get("productos"),
                   venta.get("total"), fecha=venta.get("fecha"))

    @classmethod
    def from_dict(cls, datos):
        if not isinstance(datos, dict) or not datos.get("id_pedido"):
            raise ValueError("Pedido inválido")
        return cls(datos["id_pedido"], datos.get("id_venta"),
                   datos.get("cliente") or "Invitado", datos.get("items"),
                   datos.get("total"),
                   datos.get("estado") or EstadoPedido.PENDIENTE,
                   datos.get("fecha"))

    @property
    def siguiente_estado(self):
        if self.estado not in EstadoPedido.FLUJO:
            return None
        indice = EstadoPedido.FLUJO.index(self.estado)
        if indice == len(EstadoPedido.FLUJO) - 1:
            return None
        return EstadoPedido.FLUJO[indice + 1]

    @property
    def puede_avanzar(self):
        return self.siguiente_estado is not None

    def avanzar(self):
        if self.estado not in EstadoPedido.FLUJO:
            return False, f"El pedido está {self.estado.lower()} y no puede avanzar"
        indice = EstadoPedido.FLUJO.index(self.estado)
        if indice == len(EstadoPedido.FLUJO) - 1:
            return False, "El pedido ya fue entregado"
        self.estado = EstadoPedido.FLUJO[indice + 1]
        return True, f"Pedido {self.id_pedido}: {self.estado}"

    def cancelar(self):
        if self.estado not in EstadoPedido.CANCELABLES:
            return False, "Solo se puede cancelar antes de despachar", False
        self.estado = EstadoPedido.CANCELADO
        return True, f"Pedido {self.id_pedido} cancelado", True

    def to_dict(self):
        return {"id_pedido": self.id_pedido, "id_venta": self.id_venta,
                "cliente": self.cliente, "items": self.items, "total": self.total,
                "estado": self.estado, "fecha": self.fecha}
