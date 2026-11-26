"""Reglas de una oferta temporal por producto o categoría."""
from datetime import date


class Oferta:
    TIPOS = ("producto", "categoria")

    def __init__(self, id_oferta, tipo, objetivo, precio_oferta,
                 fecha_inicio, fecha_fin):
        self.id_oferta = str(id_oferta)
        self.tipo = str(tipo).strip().lower()
        self.objetivo = str(objetivo).strip()
        self.precio_oferta = float(precio_oferta)
        self.fecha_inicio = str(fecha_inicio)
        self.fecha_fin = str(fecha_fin)

    def validar(self):
        if self.tipo not in self.TIPOS:
            return False, "Tipo de oferta inválido"
        if not self.objetivo:
            return False, "Selecciona un producto o categoría"
        if self.precio_oferta < 0:
            return False, "El precio de oferta no puede ser negativo"
        try:
            inicio = date.fromisoformat(self.fecha_inicio)
            fin = date.fromisoformat(self.fecha_fin)
        except ValueError:
            return False, "Las fechas deben usar AAAA-MM-DD"
        if fin < inicio:
            return False, "La fecha de término no puede ser anterior al inicio"
        return True, ""

    def vigente(self, hoy=None):
        ok, _ = self.validar()
        if not ok:
            return False
        hoy = hoy or date.today()
        if isinstance(hoy, str):
            hoy = date.fromisoformat(hoy)
        return date.fromisoformat(self.fecha_inicio) <= hoy <= date.fromisoformat(self.fecha_fin)

    def aplica_a(self, producto):
        if self.tipo == "producto":
            return str(getattr(producto, "id", "")) == self.objetivo
        return str(getattr(producto, "categoria", "")).casefold() == self.objetivo.casefold()

    def to_dict(self):
        return {"id_oferta": self.id_oferta, "tipo": self.tipo,
                "objetivo": self.objetivo, "precio_oferta": self.precio_oferta,
                "fecha_inicio": self.fecha_inicio, "fecha_fin": self.fecha_fin}

    @classmethod
    def from_dict(cls, datos):
        return cls(datos["id_oferta"], datos["tipo"], datos["objetivo"],
                   datos["precio_oferta"], datos["fecha_inicio"], datos["fecha_fin"])
