def calcular_promedio_categoria(self, categoria):
        """Calcula el precio promedio de una categoria"""   
        #FILTRAR PRODUCTOS
        productos_categoria = [p for p in self.productos if p.categoria.lower() == categoria.lower()]
        
        #VALIDAMOS (en caso de no encontrar productos)
        if not productos_categoria:
            print(f"No existen productos en la categoría '{categoria}'")

            return
        
        #SUMAMOS, CONTAMOS Y DIVIDIMOS
        suma_precios = sum(p.precio for p in productos_categoria)
        cantidad = len(productos_categoria)
        promedio = suma_precios / cantidad
        
        # PASO 4: MOSTRAMOS EL RESULTADO
        print(f"\nPROMEDIO DE PRECIOS - Categoría '{categoria}':")
        print(f"   Cantidad de productos: {cantidad}")
        print(f"   Suma total: ${suma_precios:.2f}")
        print(f"   Promedio: ${promedio:.2f}\n")
        
        return promedio
    
#PARTE 2: ENCONTRAR PRODUCTO CON MENOR STOCK
def producto_menor_stock_categoria(self, categoria):
        """ Encuentra el producto con MENOR STOCK de una categoría """       
        #FILTRAMOS
        productos_categoria = [p for p in self.productos if p.categoria.lower() == categoria.lower()]
        
        #VALIDAMOS
        if not productos_categoria:
            print(f" No existen productos en la categoría '{categoria}'")

            return
        
        #ENCONTRAR EL MENOR STOCK
        producto_minimo = productos_categoria[0]
        for producto in productos_categoria:
            if producto.stock < producto_minimo.stock:
                producto_minimo = producto
        
        #MOSTRAR RESULTADO
        print(f"\n PRODUCTO CON MENOR STOCK - Categoría '{categoria}':")
        print(f"   {producto_minimo}")
        print(f"    ALERTA: Solo {producto_minimo.stock} unidades disponibles\n")
        
        return producto_minimo