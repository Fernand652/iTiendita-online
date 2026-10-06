"""
servidor.py
============================
El SERVIDOR. Corre DENTRO del proceso del ADMIN (vistas/main_admin.py).

Usa el enfoque del material de sockets que pasó el profe
(Server_ProgProyV2.py), con dos diferencias importantes:

  1. En vez de aceptar UN cliente y atenderlo solo, hace un BUCLE de
     accept() y le abre un HILO a cada conexión. Eso es lo que pide la idea
     de las "cajas automáticas": muchas máquinas distintas, todas llegando
     al mismo lugar, y todas siendo atendidas a la vez.

  2. La lectura usa recv(4096) + un BUFFER que se recorta por los \n, igual
     que el material. recv() puede traer medio mensaje o tres juntos, así
     que lo que sobra se guarda para la próxima lectura.

POR QUÉ ESTE ARCHIVO ES EL DUEÑO DEL INVENTARIO
-----------------------------------------------
Inventario.descontar_stock() hace self._guardar(), o sea escribe
data/productos.json. Si el ADMIN y cada CLIENTE tuvieran su propia
copia del Inventario, los tres escriben el mismo archivo al mismo tiempo y
se pierden unidades. Por eso el stock se descuenta SOLO acá: los clientes
nunca tocan el archivo, mandan su carrito por el socket y el servidor es el
único que lo modifica. Esa es toda la gracia de poner un servidor en el medio.

CÓMO SE RESUELVE LA RESERVA DE STOCK (modelo optimista)
------------------------------------------------------
El cliente suma al carrito al instante, sin esperar, y avisa. Si al final
resulta que otro se llevó la última unidad, el cliente se enteró tarde. El
modo optimista prioriza que la interfaz se sienta rápida y acepta ese caso.

Para que no se pierdan unidades, el servidor NO confía: recalcula el
carrito que el cliente dice tener, lo compara con lo que realmente tiene
reservado, y aplica la DIFERENCIA. Si el stock no alcanza, sirve lo que
puede y le manda al cliente el carrito que realmente quedó (T_CARRITO_ESTADO)
para que se corrija.

REGLA DE ORO DE ESTE ARCHIVO (importante para la defensa)
--------------------------------------------------------
Los hilos del socket NUNCA tocan la ventana. Solo modifican datos y los
dejan en una bandeja (self.eventos). La ventana del ADMIN los lee después
con root.after(). Así nunca se rompe Tkinter.
"""

import os
import sys
import queue
import socket
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from red.protocolo import (
        HOST, PUERTO, TAMANO_BUFFER,
        T_REGISTRO, T_CARRITO, T_QUITAR, T_VACIAR, T_PAGO,
        T_INVENTARIO, T_STOCK, T_CARRITO_ESTADO, T_PAGO_OK,
        T_CARRITOS, T_ERROR,
        empaquetar, extraer_mensajes, normalizar_items, items_a_lista,
    )
except ImportError:  # ejecución directa dentro de red/
    from protocolo import (
        HOST, PUERTO, TAMANO_BUFFER,
        T_REGISTRO, T_CARRITO, T_QUITAR, T_VACIAR, T_PAGO,
        T_INVENTARIO, T_STOCK, T_CARRITO_ESTADO, T_PAGO_OK,
        T_CARRITOS, T_ERROR,
        empaquetar, extraer_mensajes, normalizar_items, items_a_lista,
    )

try:
    from persistencia.gestor_persistencia import (
        RUTA_VENTAS_JSON, cargar_json, guardar_json,
    )
except ImportError:  # ejecución directa dentro de red/
    from gestor_persistencia import (
        RUTA_VENTAS_JSON, cargar_json, guardar_json,
    )

# Cada cuánto revisamos el accept() para ver si hay que apagar el servidor.
TIMEOUT_ACCEPT = 0.5


class ServidorCarritos(threading.Thread):
    """
    Servidor de sockets que es el dueño del catálogo y de los carritos.

    Es un HILO (Thread) para que la ventana del ADMIN siga respondiendo
    mientras el servidor espera conexiones. El hilo principal de Tkinter nunca
    se bloquea.
    """

    def __init__(self, inventario, host=HOST, puerto=PUERTO):
        super().__init__(daemon=True)
        self.inventario = inventario
        self.host = host
        self.puerto = puerto

        # Carritos de cada cliente: {usuario: {id_producto: cantidad}}
        # Ej: {"ana": {1: 2, 5: 1}, "beto": {1: 1}}
        # Esta es la verdad: lo que dice cada cliente, ya validado contra stock.
        self.carritos = {}

        # Conexiones vivas: {socket: {"usuario": str|None, "rol": str}}
        self.clientes = {}

        # BANDEJA de eventos para la ventana. Los hilos escriben acá, la
        # ventana (hilo principal) lee con root.after().
        self.eventos = queue.Queue()

        # Candado: si dos clientes mandan su carrito al MISMO tiempo, el
        # diccionario de carritos y el Inventario no se pueden modificar a la vez.
        self._lock = threading.RLock()

        # Candado de ESCRITURA. Muy importante: cuando el servidor avisa a
        # todos, dos hilos podrían escribir bytes en el mismo socket a la vez
        # y los mensajes saldrían mezclados.
        self._envio_lock = threading.Lock()

        self._srv = None            # socket que escucha
        self._parar = threading.Event()
        self.error = None           # si el puerto está ocupado, queda el motivo

    # ------------------------------------------------------------------
    # ARRANQUE Y APAGADO
    # ------------------------------------------------------------------
    def run(self):
        """
        Cuerpo del hilo: abre el puerto y acepta clientes para siempre.

        A diferencia del material del profe (que acepta UNO y lo atiende), acá
        hay un while: cada accept() abre un hilo nuevo para esa "caja
        automática", así pueden conectarse varios clientes al mismo tiempo.
        """
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((self.host, self.puerto))
            srv.listen()
            # Timeout corto: si no llega nadie, accept() se corta solo y
            # podemos revisar si hay que apagar el servidor.
            srv.settimeout(TIMEOUT_ACCEPT)
        except OSError as e:
            # Lo más común: el puerto 65433 ya está en uso por otra copia del
            # servidor que quedó abierta.
            self.error = f"No se pudo abrir el puerto {self.puerto} en {self.host}: {e}"
            self.eventos.put({"type": T_ERROR, "mensaje": self.error})
            return

        self._srv = srv
        self.eventos.put({
            "type": T_INVENTARIO,
            "productos": self._catalogo(),
            "mensaje": f"Servidor escuchando en {self.host}:{self.puerto}",
        })

        try:
            while not self._parar.is_set():
                try:
                    conexion, direccion = srv.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                # Esta línea es la "caja automática": un hilo por conexión.
                threading.Thread(
                    target=self._atender_cliente,
                    args=(conexion, direccion),
                    daemon=True,
                ).start()
        finally:
            self._srv = None
            try:
                srv.close()
            except OSError:
                pass

    def detener(self):
        """
        Cierra el servidor (se llama al salir de la aplicación y en los tests).

        No alcanza con avisar que hay que parar: hay que cerrar el socket que
        escucha para que el puerto quede libre de una, y recién ahí esperar a
        que el hilo termine. Si no, el siguiente servidor que abra el mismo
        puerto se pisa con el que todavía está cerrando.
        """
        self._parar.set()
        with self._lock:
            conexiones = list(self.clientes.keys())
        for conexion in conexiones:
            try:
                conexion.close()
            except OSError:
                pass

        srv = self._srv
        if srv is not None:
            try:
                srv.close()   # esto hace que accept() se corte enseguida
            except OSError:
                pass

        if self.is_alive() and threading.current_thread() is not self:
            self.join(timeout=2)

    @property
    def activo(self):
        return self._srv is not None and self.error is None

    def sacar_evento(self):
        """
        Saca UN evento de la bandeja, o None si está vacía.

        La ventana del ADMIN la llama desde root.after() en el hilo principal
        de Tk. Esa es la regla de oro: el hilo del socket deja el evento en
        la bandeja y no toca nunca la ventana.
        """
        try:
            return self.eventos.get_nowait()
        except queue.Empty:
            return None

    # ------------------------------------------------------------------
    # DATOS QUE SE LE MANDAN A LOS CLIENTES
    # ------------------------------------------------------------------
    def _catalogo(self):
        """El catálogo completo como lista de dicts (para T_INVENTARIO)."""
        with self._lock:
            return [p.to_dict() for p in self.inventario.productos]

    def _snapshot_carritos(self):
        """Foto de todos los carritos, lista para T_CARRITOS."""
        with self._lock:
            carritos = {
                usuario: items_a_lista(items)
                for usuario, items in self.carritos.items() if items
            }
            conectados = [
                info["usuario"] for info in self.clientes.values() if info["usuario"]
            ]
        return {"type": T_CARRITOS, "carritos": carritos, "conectados": conectados}

    # ------------------------------------------------------------------
    # RECEPCIÓN DE MENSAJES (corre dentro del hilo de cada cliente)
    # ------------------------------------------------------------------
    def _atender_cliente(self, conexion, direccion):
        """
        Atiende a UN cliente (una "caja automática"). Se ejecuta una vez por
        conexión, en su propio hilo.

        La lectura es la del material del profe: recv(4096) y un buffer que se
        recorta por los \n, porque recv() no respeta los mensajes.
        """
        with self._lock:
            self.clientes[conexion] = {"usuario": None, "rol": None,
                                       "direccion": direccion}

        usuario = None
        buffer = ""
        try:
            while not self._parar.is_set():
                datos = conexion.recv(TAMANO_BUFFER)
                if not datos:
                    break  # el cliente cerró la conexión

                mensajes, buffer = extraer_mensajes(buffer, datos)
                for mensaje in mensajes:
                    tipo = mensaje.get("type")
                    if tipo == T_REGISTRO:
                        usuario = self._procesar_registro(conexion, mensaje)
                    elif usuario is None:
                        continue  # todo lo demás exige haberiously registrado
                    elif tipo == T_CARRITO:
                        self._procesar_carrito(conexion, usuario, mensaje)
                    elif tipo == T_QUITAR:
                        self._procesar_quitar(conexion, usuario, mensaje)
                    elif tipo == T_VACIAR:
                        self._procesar_vaciar(conexion, usuario)
                    elif tipo == T_PAGO:
                        self._procesar_pago(conexion, usuario)
        except (OSError, ValueError):
            # Cliente cerró la ventana o se cortó el cable. No es un error de
            # verdad, es la forma normal de terminar una conexión.
            pass
        finally:
            self._procesar_desconexion(conexion, usuario)

    def _procesar_registro(self, conexion, mensaje):
        """El cliente se identifica. Le respondemos con el catálogo."""
        usuario = str(mensaje.get("usuario") or "").strip()
        rol = str(mensaje.get("rol") or "normal")

        with self._lock:
            if conexion not in self.clientes:
                return None
            self.clientes[conexion]["usuario"] = usuario
            self.clientes[conexion]["rol"] = rol

        # Le mandamos el catálogo COMPLETO para que pueda explorar.
        self._enviar(conexion, {"type": T_INVENTARIO, "productos": self._catalogo()})
        self._difundir_carritos()
        return usuario

    def _procesar_carrito(self, conexion, usuario, mensaje):
        """
        El cliente mandó su carrito (modelo optimista).

        No le creemos a ciegas: comparamos lo que dice tener con lo que
        realmente tiene reservado, y aplicamos solo la DIFERENCIA contra el
        stock real. Si algo no se puede cumplir, se sirve lo que hay y se le
        devuelve el carrito verdadero para que se corrija.
        """
        deseado = normalizar_items(mensaje.get("items") or [])
        with self._lock:
            self.carritos[usuario], tocados = self._reconciliar(usuario, deseado)

        # Avisamos los stocks que cambiaron, para que el cliente actualice
        # los botones "sin stock".
        for id_producto in tocados:
            producto = self.inventario.buscar_por_id(id_producto)
            if producto is not None:
                self._enviar(conexion, {"type": T_STOCK, "id": producto.id,
                                        "stock": producto.stock})

        # Si el carrito que quedó NO es el que el cliente cree, se lo
        # corregimos (mensaje autoritativo).
        if self.carritos[usuario] != deseado:
            self._enviar(conexion, {
                "type": T_CARRITO_ESTADO,
                "items": items_a_lista(self.carritos[usuario]),
            })

        self._difundir_carritos()

    def _reconciliar(self, usuario, deseado):
        """
        Calcula y aplica el stock reservado para que el carrito de `usuario`
        sea `deseado` (o lo más cerca que permita el stock real).

        Devuelve (carrito_resultante, ids_de_productos_afectados).

        Se llama con self._lock tomado.
        """
        actual = dict(self.carritos.get(usuario, {}))
        resultado = {}
        tocados = []

        for id_producto in sorted(set(actual) | set(deseado)):
            objetivo = deseado.get(id_producto, 0)
            reservado = actual.get(id_producto, 0)
            if objetivo == reservado:
                if objetivo > 0:
                    resultado[id_producto] = objetivo
                continue

            if objetivo > reservado:
                # Hay que RESERVAR más. Se descuenta de a una unidad porque
                # descontar_stock() es "todo o nada": asking for 4 when there
                # are 3 would fail the whole thing.
                servidas = 0
                for _ in range(objetivo - reservado):
                    if not self.inventario.descontar_stock(id_producto, 1):
                        break
                    servidas += 1
                if servidas > 0:
                    resultado[id_producto] = reservado + servidas
                tocados.append(id_producto)
            else:
                # El cliente quiere MENOS: lo que sobra vuelve al stock.
                self.inventario.devolver_stock(id_producto, reservado - objetivo)
                if objetivo > 0:
                    resultado[id_producto] = objetivo
                tocados.append(id_producto)

        self.carritos[usuario] = resultado
        if not resultado:
            self.carritos.pop(usuario, None)
            resultado = {}
        return resultado, tocados

    def _procesar_quitar(self, conexion, usuario, mensaje):
        """El cliente saca unidades de un producto (el stock vuelve)."""
        try:
            id_producto = int(mensaje.get("id"))
            cantidad = max(0, int(mensaje.get("cantidad", 1)))
        except (TypeError, ValueError):
            return

        with self._lock:
            actual = dict(self.carritos.get(usuario, {}))
            quitado = min(cantidad, actual.get(id_producto, 0))
            if quitado <= 0:
                return
            actual[id_producto] -= quitado
            if actual[id_producto] <= 0:
                actual.pop(id_producto)
            self.inventario.devolver_stock(id_producto, quitado)
            self.carritos[usuario] = actual
            if not actual:
                self.carritos.pop(usuario, None)
            producto = self.inventario.buscar_por_id(id_producto)

        if producto is not None:
            self._enviar(conexion, {"type": T_STOCK, "id": producto.id,
                                    "stock": producto.stock})
        self._enviar(conexion, {
            "type": T_CARRITO_ESTADO,
            "items": items_a_lista(self.carritos.get(usuario, {})),
        })
        self._difundir_carritos()

    def _procesar_vaciar(self, conexion, usuario):
        """El cliente vacía su carrito: todo el stock reservado vuelve."""
        with self._lock:
            vacio, tocados = self._reconciliar(usuario, {})

        for id_producto in tocados:
            producto = self.inventario.buscar_por_id(id_producto)
            if producto is not None:
                self._enviar(conexion, {"type": T_STOCK, "id": producto.id,
                                        "stock": producto.stock})
        self._enviar(conexion, {"type": T_CARRITO_ESTADO, "items": items_a_lista(vacio)})
        self._difundir_carritos()

    def _procesar_pago(self, conexion, usuario):
        """
        Confirma la compra: se registra la venta en data/ventas.json y el
        carrito se limpia SIN devolver el stock (ya se cobró).
        """
        with self._lock:
            items = dict(self.carritos.get(usuario, {}))
            if not items:
                self._enviar(conexion, {"type": T_ERROR,
                                        "mensaje": "Tu carrito está vacío"})
                return

            detalle, total = [], 0.0
            for id_producto, cantidad in sorted(items.items()):
                producto = self.inventario.buscar_por_id(id_producto)
                if producto is None:
                    continue
                subtotal = float(producto.precio) * cantidad
                total += subtotal
                detalle.append({"id": producto.id, "nombre": producto.nombre,
                                "precio": producto.precio, "cantidad": cantidad})

            self._guardar_venta(usuario, detalle, total)
            self.carritos.pop(usuario, None)

        self._enviar(conexion, {"type": T_PAGO_OK, "total": total})
        self._enviar(conexion, {"type": T_CARRITO_ESTADO, "items": []})
        self._difundir_carritos()

    def _guardar_venta(self, usuario, detalle, total):
        """Escribe la venta en data/ventas.json (la usa el panel del ADMIN)."""
        try:
            from datetime import datetime
            fecha = datetime.now().isoformat(timespec="seconds")
        except Exception:
            fecha = ""
        try:
            subtotal=float (total)
            iva=subtotal*0.19
            total_finalsubtotal+iva
            ventas=cargar_json(str(RUTA_VENTAS_JSON), default=[]) or []
            guardar_json(str(RUTA_VENTAS_JSON), ventas)
            max_id=0
            for v in ventas:
                try:
                    vid=int(v.get("id_venta",0) or 0)
                except(ValueError,TypeError,AttributeError):
                    vid=0
                if vid>max_id:
                    max_id=vid
            ventas.append({"id_venta":max_id+1,"cliente": usuario, "fecha": fecha,
                           "items": detalle, "subtotal": subtotal, "iva": iva, "total": total_final})
            guardar_json(str(RUTA_VENTAS_JSON), ventas)
        except Exception:
            pass   # que un problema de disco no tumbe la venta

    def _procesar_desconexion(self, conexion, usuario):
        """
        El cliente se fue (cerró la app o la ventana). Lo sacamos de la lista
        de conectados y le DEVOLVEMOS el stock que tenía reservado, porque ya
        no está mirando esa pantalla.
        """
        with self._lock:
            self.clientes.pop(conexion, None)
            liberado, _ = self._reconciliar(usuario, {}) if usuario else ({}, [])

        try:
            conexion.close()
        except OSError:
            pass

        self._difundir_carritos()

    # ------------------------------------------------------------------
    # ENVÍO DE MENSAJES
    # ------------------------------------------------------------------
    def _enviar(self, conexion, mensaje):
        """Manda un mensaje a UNA conexión. Nunca lanza excepciones."""
        datos = empaquetar(mensaje)
        # El candado garantiza que el mensaje completo se escribe de un tirón.
        with self._envio_lock:
            try:
                conexion.sendall(datos)
            except (OSError, AttributeError):
                # Se cayó esa conexión. No importa: la siguiente difusión se
                # encarga de limpiarla en _procesar_desconexion.
                pass

    def difundir_inventario(self):
        """
        Avisa a todos el CATÁLOGO COMPLETO. Se llama desde la ventana del
        ADMIN cuando crea, edita o elimina un producto.
        """
        mensaje = {"type": T_INVENTARIO, "productos": self._catalogo()}
        with self._lock:
            conexiones = list(self.clientes.keys())
        for conexion in conexiones:
            self._enviar(conexion, mensaje)
        # Y a la bandeja, para que la ventana del ADMIN recargue su tabla.
        self.eventos.put(mensaje)
        self._difundir_carritos()

    def _difundir_carritos(self):
        """
        Manda la foto de todos los carritos.

        Importante: en este proyecto el ADMIN no es un cliente por socket, es
        el MISMO proceso que corre el servidor. Por eso la foto también se
        deja en self.eventos, que es la bandeja que lee la ventana del admin
        (hilo principal de Tkinter). Además se la enviamos a cualquier
        cliente registrado con rol "admin", por si en el futuro se abre un
        admin remoto.
        """
        mensaje = self._snapshot_carritos()
        self.eventos.put(mensaje)
        with self._lock:
            conexiones_admin = [
                conexion for conexion, info in self.clientes.items()
                if info.get("rol") == "admin"
            ]
        for conexion in conexiones_admin:
            self._enviar(conexion, mensaje)


if __name__ == "__main__":
    # Prueba rápida SIN ventana: levanta el servidor 5 segundos con un
    # inventario de prueba y muestra lo que llega por un socket real.
    import time
    from modelos.inventario import Inventario

    ruta_prueba = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "_servidor_prueba.json"
    )
    inv = Inventario(archivo=ruta_prueba)
    inv.productos = []
    inv.agregar_producto("Producto de prueba", 1000, 3, "Prueba")

    srv = ServidorCarritos(inv, host="127.0.0.1", puerto=65434)
    srv.start()
    time.sleep(0.5)
    print("Servidor listo:", srv.activo, srv.error)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 65434))
    s.sendall(empaquetar({"type": T_REGISTRO, "usuario": "ana", "rol": "normal"}))

    buffer = ""
    for _ in range(2):
        mensajes, buffer = extraer_mensajes(buffer, s.recv(TAMANO_BUFFER))
        for m in mensajes:
            if m.get("type") == T_INVENTARIO:
                print("Ana recibió el catálogo:", m["productos"])
    s.sendall(empaquetar({"type": T_CARRITO, "usuario": "ana",
                          "items": [{"id": 1, "cantidad": 4}]}))
    time.sleep(0.3)
    print("Pidió 4 pero solo hay 3 -> carritos:", srv.carritos)

    s.close()
    time.sleep(0.4)
    print("Al desconectar vuelve el stock:", srv.inventario.buscar_por_id(1).stock)
    srv.detener()