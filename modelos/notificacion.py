"""Mensaje de aviso enviado por el servidor a clientes conectados."""


class Notificacion:
    """Representa una notificación simple y serializable para el socket."""

    def __init__(self, tipo, mensaje, **datos):
        self.tipo = str(tipo)
        self.mensaje = str(mensaje)
        self.datos = datos

    def to_dict(self):
        """Convierte la notificación al diccionario que viaja como JSON."""
        return {
            "type": "notificacion",
            "tipo": self.tipo,
            "mensaje": self.mensaje,
            **self.datos,
        }
