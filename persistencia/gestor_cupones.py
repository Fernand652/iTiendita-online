"""Repositorio JSON de cupones; una única fuente de verdad para la tienda."""
from modelos.cupon import Cupon
from persistencia.gestor_persistencia import RUTA_CUPONES_JSON, cargar_json, guardar_json


class GestorCupones:
    def __init__(self):
        self.cupones = {}
        self.cargar()

    def cargar(self):
        self.cupones = {}
        for datos in cargar_json(RUTA_CUPONES_JSON, default=[]) or []:
            try:
                cupon = Cupon.from_dict(datos)
                self.cupones[cupon.codigo] = cupon
            except (KeyError, TypeError, ValueError):
                continue
        return self.cupones

    def guardar(self):
        guardar_json(RUTA_CUPONES_JSON, [c.to_dict() for c in self.cupones.values()])

    def crear(self, codigo, tipo, valor, fecha_vencimiento, usos_maximos):
        cupon = Cupon(codigo, tipo, valor, fecha_vencimiento, usos_maximos)
        if not cupon.codigo:
            raise ValueError("El código no puede estar vacío")
        if cupon.codigo in self.cupones:
            raise ValueError("Ya existe un cupón con ese código")
        if cupon.tipo not in Cupon.TIPOS or cupon.valor <= 0 or cupon.usos_maximos < 1:
            raise ValueError("Revisa tipo, valor y cantidad máxima de usos")
        valido, motivo = cupon.validar()
        if not valido:
            raise ValueError(motivo)
        self.cupones[cupon.codigo] = cupon
        self.guardar()
        return cupon

    def consumir(self, codigo, subtotal):
        cupon = self.cupones.get((codigo or "").strip().upper())
        if cupon is None:
            return False, 0.0, "El cupón no existe"
        descuento, motivo = cupon.calcular_descuento(subtotal)
        if not descuento:
            return False, 0.0, motivo
        cupon.usos += 1
        self.guardar()
        return True, descuento, "Cupón aplicado"
