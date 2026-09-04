"""creacion de productos"""
class Producto:
    """esta definicion lo que hace es recolectar los datos del producto """
    def __init__( self,id,nombre, precio, stock, categoria):
        self.id=id
        self.nombre=nombre
        self.precio=precio
        self.stock=stock
        self.categoria=categoria