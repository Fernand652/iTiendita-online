import csv

"""creacion de productos"""
class Producto:
    """esta definicion lo que hace es recolectar los datos del producto """
    def __init__( self,id,nombre, precio, stock, categoria):
        self.id=id
        self.nombre=nombre
        self.precio=precio
        self.stock=stock
        self.categoria=categoria
"""Esta clase almacena los productos,edita(precio, stock), elimina productos """
class Inventario:
    """guardado(creo)"""
    def __init__(self):
        self.productos= self.cargar_productos()
    """agregacion del producto """
    def agregar_producto(self, producto):
        self.productos.append(producto)
        self.guardar_productos()
    """muestraa del producto(puede ser uno o todos)"""
    def mostrar_producto(self):
        opcion = int(input("que quieres ver(1 para buscar un producto, 2 para verlos todos): "))
        if opcion==1:
            id_usuario=int(input("cual es el id del producto que estas buscando: "))
            producto=self.busqueda_por_id(id_usuario)
            while producto is None:
                print("el codigo proporcinado es erroneo intente de nuevo.", end="\n")
                id_usuario=int(input("cual es el id del producto que estas buscando: "))
                print()
                producto=self.busqueda_por_id(id_usuario)
            if producto :
                print("Producto: ")
                print(id_usuario)
                print(producto.nombre)
                print(producto.precio)
                print(producto.stock)
                print(producto.categoria) 
        elif opcion==2:              
            for producto in self.productos:
                print("Producto: ")
                print(producto.id)
                print(producto.nombre)
                print(producto.precio)
                print(producto.stock)
                print(producto.categoria)
                print()
        else:
            print("opcion erronea vuelva a intentar", end="\n")
    """Actualizacio del valor"""
    def actualizar_precio(self,id_posicion):
        
        nuevo_precio=float(input("el nuevo precio del producto: "))
        if nuevo_precio>=0:
            id_posicion.precio=nuevo_precio
            self.guardar_productos()
        else:
            print("error; valor inexistente, intente de nuevo", end="\n")
    """Actualizacio del stock"""
    def actualizar_stock(self,id_posicion):
        stock_nuevo=float(input("cual es la nueva cantidad del producto: "))
        if stock_nuevo>=0:
            id_posicion.stock=stock_nuevo
            self.guardar_productos()
        else:
            print("error; no puede haber un stock menor que 0, ", end="\n")
    def eliminar_producto(self,id_posicion):
        self.productos.remove(id_posicion)
        self.guardar_productos()
    def busqueda_por_id(self,id_main):
        for producto in self.productos:
            if producto.id==id_main:
                return producto
        return None

