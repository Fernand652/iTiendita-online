"""
Cómo correr el proyecto 
Requisitos: se debe de tener una version de python 3.10+ con tkinter 
1. Clonar y entrar a la carpeta o tener los codigos:
   git clone <url> iTiendita-online
   cd iTiendita-online
2. Ejecutar la app (desde la raíz del proyecto):
   python vistas/main_gui.py
   o python -m vistas.main_gui
3. Login inicial: El usuario(admin) es nombre: admin, clave: 1234.

Cómo correr los tests

Desde la raíz:
python -m unittest discover -s tests -v
Archivos compartidos (flujo en equipo)

-Cuando se crea un producto como admin se guarda en data/productos.json.
-Para agregar foto se debe dejar en cualquier lado del equipo(debe saber donde esta, pero nunca en la carpeta de imagenes del proyecto porque o si no le dara un error a la hora de crear el producto por duplicados), en admin pulsa Examinar PNG,
  llena nombre/precio/stock/categoría (ID vacío = automático) y pulsa Guardar.
 Compilación a ejecutable (.exe, opcional)

Como ejecutar:
1. hacer pull o obtener acceso al codigo 
2. Correr el main
3. ver las interfaces 
4. hacer lo que te piden las interfaces es bastante intuitivo 

Modo cajas de autopago (dos o más computadores)

Solo un computador debe ser el ADMIN y servidor. En ese computador, desde la
raíz del proyecto, ejecutar:
py vistas/main_admin.py --host 0.0.0.0

En cada computador que será una caja cliente, ejecutar (reemplaza IP_ADMIN
por la IPv4 local que muestra el computador ADMIN):
py vistas/main_cliente.py --host IP_ADMIN

No se deben abrir dos ADMIN ni ejecutar main_gui.py para probar la red: cada
uno de esos procesos tendría su catálogo local. Al abrir, los clientes reciben
automáticamente el catálogo del ADMIN; las modificaciones de productos, el
stock y los carritos activos se sincronizan en tiempo real. Si Windows pide
permiso para la red privada, se debe aceptar para Python.
"""
