"""Lista de deseos y suscripciones a reposición, persistidas por usuario."""
from persistencia.gestor_persistencia import RUTA_DESEOS_JSON, cargar_json, guardar_json


class ListaDeseos:
    def __init__(self, archivo=None):
        """Carga la lista desde ``archivo`` o desde la ruta real de la tienda.

        El parámetro opcional permite probar la persistencia en un archivo
        temporal sin modificar las listas reales de los clientes.
        """
        self.archivo = archivo or RUTA_DESEOS_JSON
        self.usuarios = cargar_json(self.archivo, default={}) or {}
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

    def datos_de(self, usuario):
        # lo que el servidor le pasa al cliente: favoritos y suscripciones
        # no uso _datos a proposito: el invitado todavia no tiene entrada
        # y no quiero crearla ni tirar ValueError aca
        datos = self.usuarios.get(str(usuario or "").strip(), {})
        return {
            "favoritos": list(datos.get("favoritos") or []),
            "suscripciones": list(datos.get("suscripciones") or []),
            "historial": list(datos.get("historial") or []),
        }

    def reemplazar_datos(self, usuario, favoritos, suscripciones):
        # el cliente copia aca lo que el servidor dice que es la verdad
        datos = self._datos(usuario)
        datos["favoritos"] = list(favoritos or [])
        datos["suscripciones"] = list(suscripciones or [])
        # La copia recibida por socket queda en memoria: solo el servidor
        # escribe el archivo compartido, incluidos los avisos pendientes.
        return True, "Lista de deseos actualizada"

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

    def quitar(self, usuario, id_producto, suscripcion=False):
        clave = "suscripciones" if suscripcion else "favoritos"
        elementos = self._datos(usuario)[clave]
        if id_producto in elementos:
            elementos.remove(id_producto)
            self._guardar()
        return True, "Suscripción cancelada" if suscripcion else "Favorito eliminado"

    def guardar_aviso(self, usuario, aviso):
        from uuid import uuid4
        from datetime import datetime
        mensaje = dict(aviso, id_aviso=uuid4().hex, fecha=datetime.now().isoformat(timespec="seconds"))
        self._datos(usuario).setdefault("avisos", []).append(mensaje)
        self.registrar_historial(usuario, mensaje)
        self._guardar()
        return mensaje

    def avisos_pendientes(self, usuario):
        return list(self._datos(usuario).get("avisos", []))

    def registrar_historial(self, usuario, aviso):
        historial = self._datos(usuario).setdefault("historial", [])
        if not any(a.get("id_aviso") == aviso.get("id_aviso") for a in historial):
            historial.append(dict(aviso))

    def confirmar_aviso(self, usuario, id_aviso):
        datos = self._datos(usuario)
        datos["avisos"] = [a for a in datos.get("avisos", []) if a.get("id_aviso") != id_aviso]
        self._guardar()

    def es_suscriptor(self, usuario, id_producto):
        return id_producto in self._datos(usuario)["suscripciones"]

    def usuarios_suscritos(self, id_producto):
        # avisamos de reposicion solo a quienes pidieron este producto
        return [usuario for usuario, datos in self.usuarios.items()
                if isinstance(datos, dict)
                and id_producto in (datos.get("suscripciones") or [])]

    def usuarios_con_favorito(self, id_producto):
        # avisamos de rebajas solo a quienes lo tienen guardado
        return [usuario for usuario, datos in self.usuarios.items()
                if isinstance(datos, dict)
                and id_producto in (datos.get("favoritos") or [])]

    def cantidad_esperando(self, id_producto):
        """Cantidad de clientes suscritos a la reposición de un producto."""
        return len(self.usuarios_suscritos(id_producto))

    def _guardar(self):
        guardar_json(self.archivo, self.usuarios)
