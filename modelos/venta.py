from datetime import datetime

class Venta:
    def __init__(self, id_venta, run_cliente=None, productos=None, total=0.0, fecha=None):
        self.id_venta = id_venta
        self.run_cliente = run_cliente if run_cliente else "Anonimo"
        self.productos = productos if productos is not None else []
        self.total = float(total)
        self.fecha = fecha if fecha else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        return {
            "id_venta": self.id_venta,
            "run_cliente": self.run_cliente,
            "productos": self.productos,
            "total": self.total,
            "fecha": self.fecha
        }