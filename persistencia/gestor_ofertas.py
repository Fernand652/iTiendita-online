"""Persistencia y aplicación de ofertas temporales."""
from datetime import date

from modelos.oferta import Oferta
from persistencia.gestor_persistencia import RUTA_OFERTAS_JSON, cargar_json, guardar_json


class GestorOfertas:
    def __init__(self, archivo=None):
        self.archivo = archivo or RUTA_OFERTAS_JSON
        self.ofertas = []
        self.cargar()

    def cargar(self):
        self.ofertas = []
        for datos in cargar_json(self.archivo, default=[]) or []:
            try:
                oferta = Oferta.from_dict(datos)
                if oferta.validar()[0]:
                    self.ofertas.append(oferta)
            except (KeyError, TypeError, ValueError):
                continue
        return self.ofertas

    def guardar(self):
        guardar_json(self.archivo, [oferta.to_dict() for oferta in self.ofertas])

    def _siguiente_id(self):
        numeros = [int(o.id_oferta[2:]) for o in self.ofertas
                   if o.id_oferta.startswith("O-") and o.id_oferta[2:].isdigit()]
        return f"O-{max(numeros, default=0) + 1:04d}"

    def crear(self, tipo, objetivo, precio_oferta, fecha_inicio, fecha_fin):
        oferta = Oferta(self._siguiente_id(), tipo, objetivo, precio_oferta,
                        fecha_inicio, fecha_fin)
        ok, mensaje = oferta.validar()
        if not ok:
            raise ValueError(mensaje)
        self.ofertas.append(oferta)
        self.guardar()
        return oferta

    def eliminar(self, id_oferta):
        for oferta in self.ofertas:
            if oferta.id_oferta == str(id_oferta):
                self.ofertas.remove(oferta)
                self.guardar()
                return True
        return False

    def precio_vigente(self, producto, hoy=None):
        normal = float(getattr(producto, "precio_normal", producto.precio))
        aplicables = [o.precio_oferta for o in self.ofertas
                      if o.vigente(hoy) and o.aplica_a(producto)]
        return min([normal] + aplicables)

    def aplicar_a_inventario(self, inventario, hoy=None):
        """Actualiza precios vigentes sin perder el precio normal persistido."""
        cambio = False
        for producto in inventario.productos:
            if not hasattr(producto, "precio_normal"):
                producto.precio_normal = float(producto.precio)
            vigente = self.precio_vigente(producto, hoy)
            if float(producto.precio) != vigente:
                producto.precio = vigente
                cambio = True
        if cambio:
            inventario._guardar()
        return cambio

    def activas(self, hoy=None):
        return [oferta for oferta in self.ofertas if oferta.vigente(hoy or date.today())]
