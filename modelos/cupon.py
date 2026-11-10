"""Reglas de validación, cálculo y serialización de cupones del hito 3."""
from datetime import date


class Cupon:
    TIPOS = ("porcentaje", "monto_fijo")

    def __init__(self, codigo, tipo, valor, fecha_vencimiento, usos_maximos, usos=0):
        self.codigo = str(codigo).strip().upper()
        self.tipo = tipo
        self.valor = float(valor)
        self.fecha_vencimiento = fecha_vencimiento
        self.usos_maximos = int(usos_maximos)
        self.usos = int(usos)

    def validar(self):
        """Retorna (válido, motivo) sin consumir un uso del cupón."""
        if self.tipo not in self.TIPOS or self.valor <= 0:
            return False, "Cupón con configuración inválida"
        try:
            vencimiento = date.fromisoformat(self.fecha_vencimiento)
        except (TypeError, ValueError):
            return False, "Cupón con fecha de vencimiento inválida"
        if date.today() > vencimiento:
            return False, "Este cupón está vencido"
        if self.usos >= self.usos_maximos:
            return False, "Este cupón ya no tiene usos disponibles"
        return True, "Cupón aplicado"

    def calcular_descuento(self, subtotal):
        """Calcula un descuento acotado al subtotal, sin registrar el uso."""
        valido, motivo = self.validar()
        if not valido:
            return 0.0, motivo
        subtotal = max(0.0, float(subtotal))
        descuento = subtotal * self.valor / 100 if self.tipo == "porcentaje" else self.valor
        return min(descuento, subtotal), motivo

    def registrar_uso(self):
        valido, motivo = self.validar()
        if valido:
            self.usos += 1
        return valido, motivo

    def to_dict(self):
        return {"codigo": self.codigo, "tipo": self.tipo, "valor": self.valor,
                "fecha_vencimiento": self.fecha_vencimiento,
                "usos_maximos": self.usos_maximos, "usos": self.usos}

    @classmethod
    def from_dict(cls, datos):
        return cls(datos["codigo"], datos["tipo"], datos["valor"],
                   datos["fecha_vencimiento"], datos["usos_maximos"],
                   datos.get("usos", 0))
