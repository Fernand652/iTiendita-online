class Despacho:
    TARIFAS= {"Maule": 4990, "Metropolitana": 5990}
    TARIFA_RESTO= 7990
    ENVIO_GRATIS_DESDE= 100000
    REGION_TIENDA= "Maule"
    REGIONES= ["Maule", "Metropolitana", "O'Higgins", "Ñuble", "Biobío", "Araucanía", "Los Ríos", "Los Lagos", "Aysén", "Magallanes", "Coquimbo", "Valparaíso", "Atacama", "Antofagasta", "Tarapacá", "Arica y Parinacota"]
    def __init__(self,modalidad="retiro",region="",receptor="",direccion="",comuna=""):
        self.modalidad= "domicilio" if modalidad=="domicilio" else "retiro"
        self.region= (region or "").strip()
        self.receptor= (receptor or "").strip()
        self.direccion= (direccion or "").strip()
        self.comuna= (comuna or "").strip()

    def calcular(self, subtotal):
        subtotal= float(subtotal or 0)
        if self.modalidad=="retiro" or subtotal>=self.ENVIO_GRATIS_DESDE:
            return 0
        return self.TARIFAS.get(self.region, self.TARIFA_RESTO)

    def dias_entrega(self):
        if self.modalidad=="retiro":
            return 0
        return 2 if self.region==self.REGION_TIENDA else 5

    def to_dict(self):
        return {
            "modalidad": self.modalidad,
            "region": self.region,
            "receptor": self.receptor,
            "direccion": self.direccion,
            "comuna": self.comuna,
            "dias_entrega": self.dias_entrega(),
        }
    @classmethod
    def from_dict(cls,datos):
        datos=datos or {}
        return cls(
            datos.get("modalidad", "retiro"),
            datos.get("region", ""),
            datos.get("receptor", ""),
            datos.get("direccion", ""),
            datos.get("comuna", ""),
        )
    