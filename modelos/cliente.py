class Cliente:
    def __init__(self, run, nombre=""):
        self.run = run
        self.nombre = nombre

    def to_dict(self):
        return {
            "run": self.run,
            "nombre": self.nombre
        }