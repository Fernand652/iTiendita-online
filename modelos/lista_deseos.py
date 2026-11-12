"""Lista de deseos y suscripciones a reposición, persistidas por usuario."""
from persistencia.gestor_persistencia import RUTA_DESEOS_JSON, cargar_json, guardar_json


class ListaDeseos:
    def __init__(self):
        self.usuarios = cargar_json(RUTA_DESEOS_JSON, default={}) or {}
        if not isinstance(self.usuarios, dict):
            self.usuarios = {}

    def _datos(self, usuario):
        usuario = str(usuario or "").strip()
        if not usuario:
            raise ValueError("Inicia sesión para usar tu lista de deseos")
        datos = self.usuarios.setdefault(usuario, {"favoritos": [], "suscripciones": []})
        datos.setdefault("favoritos", [])
        datos.setdefault("suscripciones", [])
        return datos

    def guardar_favorito(self, usuario, id_producto):
        datos = self._datos(usuario)
        if id_producto in datos["favoritos"]:
            return False, "Este producto ya está en tu lista de deseos"
        datos["favoritos"].append(id_producto)
        self._guardar()
        return True, "Guardado en tu lista de deseos"

    def suscribirse(self, usuario, id_producto):
        datos = self._datos(usuario)
        if id_producto in datos["suscripciones"]:
            return False, "Ya estás suscrito a la reposición"
        datos["suscripciones"].append(id_producto)
        self._guardar()
        return True, "Te avisaremos cuando vuelva a estar disponible"

    def productos_de(self, usuario):
        datos = self._datos(usuario)
        return set(datos["favoritos"]) | set(datos["suscripciones"])

    def es_suscriptor(self, usuario, id_producto):
        return id_producto in self._datos(usuario)["suscripciones"]

    def _guardar(self):
        guardar_json(RUTA_DESEOS_JSON, self.usuarios)
