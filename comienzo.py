import csv

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

