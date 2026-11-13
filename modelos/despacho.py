from datetime import date, datetime, timedelta


class Direccion:
    def __init__(self, region="", receptor="", direccion="", comuna=""):
        self.region = (region or "").strip()
        self.receptor = (receptor or "").strip()
        self.direccion = (direccion or "").strip()
        self.comuna = (comuna or "").strip()

    def validar(self, regiones_validas=None):
        if not self.receptor:
            return False, "Ingresa el nombre de quien recibe"
        if not self.region:
            return False, "Selecciona una región"
        if regiones_validas is not None and self.region not in regiones_validas:
            return False, "La región seleccionada no tiene tarifa de envío"
        if not self.direccion:
            return False, "Ingresa una dirección para el despacho"
        if not self.comuna:
            return False, "Ingresa una comuna para el despacho"
        return True, ""

    def to_dict(self):
        return {
            "region": self.region,
            "receptor": self.receptor,
            "direccion": self.direccion,
            "comuna": self.comuna,
        }

    @classmethod
    def from_dict(cls, datos):
        datos = datos or {}
        return cls(
            datos.get("region", ""),
            datos.get("receptor", ""),
            datos.get("direccion", ""),
            datos.get("comuna", ""),
        )


class TarifaEnvio:
    REGIONES = [
        "Maule", "Metropolitana", "O'Higgins", "Ñuble", "Biobío",
        "Araucanía", "Los Ríos", "Los Lagos", "Aysén", "Magallanes",
        "Coquimbo", "Valparaíso", "Atacama", "Antofagasta", "Tarapacá",
        "Arica y Parinacota",
    ]
    TARIFAS_POR_DEFECTO = {"Maule": 4990, "Metropolitana": 5990}
    TARIFA_RESTO_POR_DEFECTO = 7990
    ENVIO_GRATIS_POR_DEFECTO = 100000
    REGION_TIENDA_POR_DEFECTO = "Maule"
    DIAS_TIENDA = 2
    DIAS_RESTO = 5

    def __init__(self, tarifas=None, tarifa_resto=None, envio_gratis_desde=None,
                 region_tienda=None):
        self.tarifa_resto = int(
            self.TARIFA_RESTO_POR_DEFECTO if tarifa_resto is None else tarifa_resto
        )
        self.envio_gratis_desde = int(
            self.ENVIO_GRATIS_POR_DEFECTO
            if envio_gratis_desde is None else envio_gratis_desde
        )
        self.region_tienda = str(
            region_tienda or self.REGION_TIENDA_POR_DEFECTO
        ).strip()
        self.tarifas = {region: self.tarifa_resto for region in self.REGIONES}
        self.tarifas.update(self.TARIFAS_POR_DEFECTO)
        if isinstance(tarifas, dict):
            for region, monto in tarifas.items():
                self.tarifas[str(region)] = int(monto)

    def calcular(self, region, subtotal):
        subtotal = float(subtotal or 0)
        if subtotal >= self.envio_gratis_desde:
            return 0
        return self.tarifas.get(region, self.tarifa_resto)

    def dias_entrega(self, region):
        return self.DIAS_TIENDA if region == self.region_tienda else self.DIAS_RESTO

    def to_dict(self):
        return {
            "tarifas": dict(self.tarifas),
            "tarifa_resto": self.tarifa_resto,
            "envio_gratis_desde": self.envio_gratis_desde,
            "region_tienda": self.region_tienda,
        }

    @classmethod
    def from_dict(cls, datos):
        datos = datos or {}
        return cls(
            datos.get("tarifas"),
            datos.get("tarifa_resto"),
            datos.get("envio_gratis_desde"),
            datos.get("region_tienda"),
        )

    @classmethod
    def config_por_defecto(cls):
        return cls().to_dict()


def _sumar_dias_habiles(fecha_base, dias):
    if isinstance(fecha_base, str):
        try:
            fecha_base = datetime.fromisoformat(fecha_base).date()
        except ValueError:
            fecha_base = date.today()
    elif isinstance(fecha_base, datetime):
        fecha_base = fecha_base.date()
    elif not isinstance(fecha_base, date):
        fecha_base = date.today()

    dias = max(0, int(dias or 0))
    fecha = fecha_base
    while dias > 0:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5:
            dias -= 1
    return fecha


class Despacho:
    REGIONES = TarifaEnvio.REGIONES
    TARIFAS = dict(TarifaEnvio.TARIFAS_POR_DEFECTO)
    TARIFA_RESTO = TarifaEnvio.TARIFA_RESTO_POR_DEFECTO
    ENVIO_GRATIS_DESDE = TarifaEnvio.ENVIO_GRATIS_POR_DEFECTO
    REGION_TIENDA = TarifaEnvio.REGION_TIENDA_POR_DEFECTO
    TARIFA_ENVIO = TarifaEnvio()

    def __init__(self, modalidad="retiro", region="", receptor="", direccion="", comuna=""):
        self.modalidad = "domicilio" if modalidad == "domicilio" else "retiro"
        self.region = (region or "").strip()
        self.receptor = (receptor or "").strip()
        self.direccion = (direccion or "").strip()
        self.comuna = (comuna or "").strip()

    def calcular(self, subtotal):
        if self.modalidad == "retiro":
            return 0
        return self.TARIFA_ENVIO.calcular(self.region, subtotal)

    def dias_entrega(self):
        if self.modalidad == "retiro":
            return 0
        return self.TARIFA_ENVIO.dias_entrega(self.region)

    def fecha_estimada_entrega(self, fecha_base=None):
        if self.modalidad == "retiro":
            return None
        return _sumar_dias_habiles(
            fecha_base if fecha_base is not None else date.today(),
            self.dias_entrega(),
        )

    def validar(self):
        if self.modalidad != "domicilio":
            return True, ""
        return Direccion(
            self.region, self.receptor, self.direccion, self.comuna
        ).validar(self.TARIFA_ENVIO.tarifas)

    def to_dict(self, fecha_base=None):
        fecha_estimada = self.fecha_estimada_entrega(fecha_base)
        return {
            "modalidad": self.modalidad,
            "region": self.region,
            "receptor": self.receptor,
            "direccion": self.direccion,
            "comuna": self.comuna,
            "dias_entrega": self.dias_entrega(),
            "fecha_estimada_entrega": (
                fecha_estimada.isoformat() if fecha_estimada is not None else None
            ),
        }

    @classmethod
    def from_dict(cls, datos):
        datos = datos or {}
        return cls(
            datos.get("modalidad", "retiro"),
            datos.get("region", ""),
            datos.get("receptor", ""),
            datos.get("direccion", ""),
            datos.get("comuna", ""),
        )

    @classmethod
    def aplicar_config(cls, config=None):
        tarifa = TarifaEnvio.from_dict(config or cls.config_por_defecto())
        cls.TARIFA_ENVIO = tarifa
        cls.TARIFAS = dict(tarifa.tarifas)
        cls.TARIFA_RESTO = tarifa.tarifa_resto
        cls.ENVIO_GRATIS_DESDE = tarifa.envio_gratis_desde
        cls.REGION_TIENDA = tarifa.region_tienda
        return tarifa

    @classmethod
    def config_por_defecto(cls):
        return TarifaEnvio.config_por_defecto()
