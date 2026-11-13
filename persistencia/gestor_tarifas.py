from modelos.despacho import Despacho, TarifaEnvio
from persistencia.gestor_persistencia import (
    RUTA_CONFIG_DESPACHO_JSON,
    cargar_json,
    guardar_json,
)


class GestorTarifas:
    def __init__(self, archivo=None):
        self.archivo = archivo or RUTA_CONFIG_DESPACHO_JSON
        self.config = self.cargar()
        Despacho.aplicar_config(self.config)

    def cargar(self):
        datos = cargar_json(self.archivo, default=None)
        if not isinstance(datos, dict):
            return Despacho.config_por_defecto()
        try:
            return self._normalizar(datos)
        except (TypeError, ValueError):
            return Despacho.config_por_defecto()

    def _normalizar(self, datos):
        if not isinstance(datos, dict):
            raise ValueError("La configuración de despacho debe ser un objeto")
        tarifa = TarifaEnvio.from_dict(datos)
        if tarifa.tarifa_resto < 0 or tarifa.envio_gratis_desde < 0:
            raise ValueError("Las tarifas y el envío gratis no pueden ser negativos")
        if any(monto < 0 for monto in tarifa.tarifas.values()):
            raise ValueError("Las tarifas no pueden ser negativas")
        if tarifa.region_tienda not in TarifaEnvio.REGIONES:
            raise ValueError("La región de la tienda no es válida")
        return tarifa.to_dict()

    def aplicar(self, datos):
        self.config = self._normalizar(datos)
        Despacho.aplicar_config(self.config)
        return self.config

    def guardar(self, datos=None):
        if datos is not None:
            self.config = self._normalizar(datos)
            Despacho.aplicar_config(self.config)
        guardar_json(self.archivo, self.config)
        return self.config
