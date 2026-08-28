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


    #se encarga de guardar los productos en un archivo CSV
    def guardar_productos(self):
        with open("productos.csv", "w", newline="") as archivo:
            escritor=csv.writer(archivo)
            escritor.writerow(["ID","Nombre","Precio","Stock","Categoria"])
            for producto in self.productos:
                escritor.writerow([producto.id,producto.nombre,producto.precio,producto.stock,producto.categoria])
    #Se encarga de cargar los productos desde un archivo CSV
    def cargar_productos(self):
        productos=[]
        try:
            with open("productos.csv", "r") as archivo:
                lector=csv.reader(archivo)
                next(lector,None)  # Saltar la primera fila (encabezados)
                for fila in lector:
                    if fila:  # Verificar si la fila no está vacía
                        id=int(fila[0])
                        nombre=fila[1]
                        precio=float(fila[2])
                        stock=float(fila[3])
                        categoria=fila[4]
                        producto=Producto(id,nombre,precio,stock,categoria)
                        productos.append(producto)
        except FileNotFoundError:
            pass
        return productos

mi_inventario=Inventario()

"""MAIN"""
bandera=True
while bandera==True:
    print("===== INVENTARIO =====")
    print("1. Agregar producto")
    print("2. Mostrar producto")
    print("3. Actualizar precio")
    print("4. Actualizar stock")
    print("5. Eliminar producto")
    print("6. Salir")
    cliente=int(input("¿Qué quieres hacer?: "))
    #Agrega un producto
    if cliente==1:
        id_producto=int(input("ingresa el id del producto: "))
        nombre=input("ingresa el nombre del producto: ")
        precio=float(input("ingresa el precio del producto: "))
        stock=float(input("ingresa el stock del producto: "))
        categoria=input("ingresa la categoria del producto: ")

        producto_nuevo=Producto(id_producto,nombre,precio,stock,categoria)

        mi_inventario.agregar_producto(producto_nuevo)

        print("producto agregado con exito.", end="\n")
    #Muestra el producto o productos
    elif cliente==2:
        mi_inventario.mostrar_producto()
    #Actualiza el precio del producto
    elif cliente==3:
        id_main=int(input("ingresa el id que buscas: "))
        id_posicion = mi_inventario.busqueda_por_id(id_main)
        mi_inventario.actualizar_precio(id_posicion)

    #Actualiza el stock del producto
    elif cliente==4:
        id_main=int(input("ingresa el id que buscas: "))
        id_posicion = mi_inventario.busqueda_por_id(id_main)
        mi_inventario.actualizar_stock(id_posicion)

    #Elimina un producto
    elif cliente==5:
        id_main=int(input("ingresa el id que buscas: "))
        id_posicion = mi_inventario.busqueda_por_id(id_main)
        mi_inventario.eliminar_producto(id_posicion)

    #Salir del programa
    elif cliente==6:
        print("Saliendo del sistema...", end="\n")
        bandera=False