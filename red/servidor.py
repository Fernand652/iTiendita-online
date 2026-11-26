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
import time 
from red.protocolo import T_QUITAR_DESEO, T_CANCELAR_SUSCRIPCION, T_AVISO_RECIBIDO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from red.protocolo import (
        HOST, PUERTO, TAMANO_BUFFER,
        T_REGISTRO, T_CARRITO, T_QUITAR, T_VACIAR, T_PAGO, T_GUARDAR_DESEO, T_SUSCRIBIR_REPOSICION,
        T_PREGUNTA, T_INVENTARIO, T_STOCK, T_CARRITO_ESTADO, T_PAGO_OK, T_RESPUESTA, T_CUPONES,
        T_TARIFAS, T_DESEOS, T_NOTIFICACION, T_CARRITOS, T_ERROR,
        T_PEDIDOS, T_PEDIDO_ESTADO,
        empaquetar, extraer_mensajes, normalizar_items, items_a_lista,
    )
except ImportError:  # ejecución directa dentro de red/
    from protocolo import (
        HOST, PUERTO, TAMANO_BUFFER,
        T_REGISTRO, T_CARRITO, T_QUITAR, T_VACIAR, T_PAGO, T_GUARDAR_DESEO, T_SUSCRIBIR_REPOSICION,
        T_PREGUNTA, T_INVENTARIO, T_STOCK, T_CARRITO_ESTADO, T_PAGO_OK, T_RESPUESTA, T_CUPONES,
        T_TARIFAS, T_DESEOS, T_NOTIFICACION, T_CARRITOS, T_ERROR,
        T_PEDIDOS, T_PEDIDO_ESTADO,
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

try:
    from modelos.despacho import Despacho
    from modelos.api_gemini import consultar_gemini
    from modelos.lista_deseos import ListaDeseos
    from modelos.notificacion import Notificacion
    from persistencia.gestor_cupones import GestorCupones
    from persistencia.gestor_tarifas import GestorTarifas
    from persistencia.gestor_pedidos import GestorPedidos
    from persistencia.gestor_ofertas import GestorOfertas
except ImportError:  # ejecución directa dentro de red/
    from despacho import Despacho
    from api_gemini import consultar_gemini
    from lista_deseos import ListaDeseos
    from notificacion import Notificacion
    from gestor_cupones import GestorCupones
    from gestor_tarifas import GestorTarifas
    from gestor_pedidos import GestorPedidos
    from gestor_ofertas import GestorOfertas

# Cada cuánto revisamos el accept() para ver si hay que apagar el servidor.
TIMEOUT_ACCEPT = 0.5


class ServidorCarritos(threading.Thread):
    """
    Servidor de sockets que es el dueño del catálogo y de los carritos.

    Es un HILO (Thread) para que la ventana del ADMIN siga respondiendo
    mientras el servidor espera conexiones. El hilo principal de Tkinter nunca
    se bloquea.
    """

    def __init__(self, inventario, host=HOST, puerto=PUERTO, gestor_tarifas=None,
                 gestor_pedidos=None):
        super().__init__(daemon=True)
        self.inventario = inventario
        self.gestor_cupones = GestorCupones()
        self.gestor_tarifas = gestor_tarifas or GestorTarifas()
        self.gestor_pedidos = gestor_pedidos or GestorPedidos()
        self.gestor_ofertas = GestorOfertas()
        self.gestor_ofertas.aplicar_a_inventario(self.inventario)
        self.lista_deseos = ListaDeseos()
        self.host = host
        self.puerto = puerto

        # Carritos de cada cliente: {usuario: {id_producto: cantidad}}
        # Ej: {"ana": {1: 2, 5: 1}, "beto": {1: 1}}
        # Esta es la verdad: lo que dice cada cliente, ya validado contra stock.
        self.carritos = {}
        self.carritos_timestamps = {}
        self.tiempo_limite_carritos_minutos = 5

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
        self._catalogo_anterior = self._catalogo_por_id()

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
                    self.verificar_carritos_expirados()
                    self.verificar_ofertas_vencidas()
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
            

    def verificar_carritos_expirados(self):
        """Revisa si algún carrito superó el tiempo límite sin actividad."""
        tiempo_actual = time.time()
        limite_segundos = self.tiempo_limite_carritos_minutos * 60
        usuarios_expirados = []

        with self._lock:
            for usuario, ultimo_tiempo in list(self.carritos_timestamps.items()):
                if (tiempo_actual - ultimo_tiempo) > limite_segundos:
                    usuarios_expirados.append(usuario)

            tocados_totales = []
            for usuario in usuarios_expirados:
                _, tocados = self._reconciliar(usuario, {})
                self.carritos.pop(usuario, None)
                self.carritos_timestamps.pop(usuario, None)
                tocados_totales.extend(tocados)

        if usuarios_expirados:
            with self._lock:
                conexiones_por_usuario = {
                    info.get("usuario"): conn
                    for conn, info in self.clientes.items()
                    if info.get("usuario") in usuarios_expirados
                }
            for usuario, conn in conexiones_por_usuario.items():
                self._enviar(conn, {
                    "type": T_CARRITO_ESTADO,
                    "items": [],
                    "expirado": True,
                    "mensaje": "Tu carrito expiró por inactividad y se liberó el stock.",
                })
            self._difundir_stock(list(set(tocados_totales)))
            self._difundir_carritos()

    def configurar_tiempo_carritos(self, minutos):
        try:
            minutos = int(minutos)
        except (TypeError, ValueError):
            return False, "El tiempo debe ser un número entero"
        if not 1 <= minutos <= 120:
            return False, "El tiempo debe estar entre 1 y 120 minutos"
        self.tiempo_limite_carritos_minutos = minutos
        return True, f"Reserva configurada en {minutos} minutos"

    def verificar_ofertas_vencidas(self):
        """Restaura precios normales al vencer una oferta y lo difunde."""
        if self.gestor_ofertas.aplicar_a_inventario(self.inventario):
            self.difundir_inventario()
                

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

    def _catalogo_por_id(self):
        return {p.id: {"nombre": p.nombre, "precio": float(p.precio), "stock": int(p.stock)}
                for p in self.inventario.productos}

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
                        self._procesar_pago(conexion, usuario, mensaje)
                    elif tipo == T_PREGUNTA:
                        self._procesar_pregunta(conexion, mensaje)
                    elif tipo == T_GUARDAR_DESEO:
                        self._procesar_deseo(conexion, usuario, mensaje)
                    elif tipo == T_SUSCRIBIR_REPOSICION:
                        self._procesar_deseo(conexion, usuario, mensaje, suscripcion=True)
                    elif tipo in (T_QUITAR_DESEO, T_CANCELAR_SUSCRIPCION):
                        with self._lock:
                            ok, texto = self.lista_deseos.quitar(usuario, mensaje.get("id"),
                                                               tipo == T_CANCELAR_SUSCRIPCION)
                            datos = self.lista_deseos.datos_de(usuario)
                        self._enviar(conexion, dict(type=T_DESEOS, ok=ok, mensaje=texto, **datos))
                        self.eventos.put({"type": T_DESEOS})
                    elif tipo == T_AVISO_RECIBIDO:
                        with self._lock:
                            self.lista_deseos.confirmar_aviso(usuario, mensaje.get("id_aviso"))
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

        tocados = []
        with self._lock:
            if conexion not in self.clientes:
                return None
            anterior = self.clientes[conexion].get("usuario")
            # Un cliente entra primero como invitado para recibir el catálogo
            # y después puede iniciar sesión. Su carrito temporal debe dejar
            # de reservar stock antes de asociar el mismo socket al usuario.
            if anterior and anterior != usuario:
                _, tocados = self._reconciliar(anterior, {})
            self.clientes[conexion]["usuario"] = usuario
            self.clientes[conexion]["rol"] = rol

        self._difundir_stock(tocados)
        # Le mandamos el catálogo COMPLETO para que pueda explorar.
        self._enviar(conexion, {"type": T_INVENTARIO, "productos": self._catalogo()})
        self._enviar(conexion, {"type": T_CUPONES,
                     "cupones": [c.to_dict() for c in self.gestor_cupones.cupones.values()]})
        self._enviar(conexion, {"type": T_TARIFAS,
                     "config": self.gestor_tarifas.config})
        self._enviar(conexion, {"type": T_DESEOS, **self.lista_deseos.datos_de(usuario)})
        with self._lock:
            pendientes = self.lista_deseos.avisos_pendientes(usuario)
        for aviso in pendientes:
            self._enviar(conexion, aviso)
        self._enviar(conexion, {"type": T_PEDIDOS,
                     "pedidos": self.gestor_pedidos.de_cliente(usuario)})
        self._difundir_carritos()
        return usuario

    def _procesar_deseo(self, conexion, usuario, mensaje, suscripcion=False):
        producto = self.inventario.buscar_por_id(mensaje.get("id"))
        if producto is None or (suscripcion and producto.stock > 0):
            self._enviar(conexion, {"type": T_ERROR, "mensaje": "Producto no disponible para esta acción"})
            return
        accion = self.lista_deseos.suscribirse if suscripcion else self.lista_deseos.guardar_favorito
        ok, texto = accion(usuario, producto.id)
        self._enviar(conexion, {"type": T_DESEOS, **self.lista_deseos.datos_de(usuario), "ok": ok, "mensaje": texto})
        self.eventos.put({"type": T_DESEOS})

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
        if self.carritos.get(usuario):
            self.carritos_timestamps[usuario] = time.time()
        else:
            self.carritos_timestamps.pop(usuario, None)

        # Todas las cajas necesitan ver el stock real, no solo la que hizo
        # el cambio. Esto es lo que hace que funcionen como cajas de autopago.
        self._difundir_stock(tocados)

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
            if self.carritos.get(usuario):
                self.carritos_timestamps[usuario] = time.time()
            else:
                self.carritos_timestamps.pop(usuario, None)
            producto = self.inventario.buscar_por_id(id_producto)

        self._difundir_stock([id_producto])
        self._enviar(conexion, {
            "type": T_CARRITO_ESTADO,
            "items": items_a_lista(self.carritos.get(usuario, {})),
        })
        self._difundir_carritos()

    def _procesar_vaciar(self, conexion, usuario):
        """El cliente vacía su carrito: todo el stock reservado vuelve."""
        with self._lock:
            vacio, tocados = self._reconciliar(usuario, {})
            self.carritos_timestamps.pop(usuario, None)


        self._difundir_stock(tocados)
        self._enviar(conexion, {"type": T_CARRITO_ESTADO, "items": items_a_lista(vacio)})
        self._difundir_carritos()

    def _procesar_pago(self, conexion, usuario, mensaje=None):
        """
        Confirma la compra: se registra la venta en data/ventas.json (con
        envío, despacho e IVA) y el carrito se limpia SIN devolver el stock
        (ya se cobró).
        """
        despacho = Despacho.from_dict((mensaje or {}).get("despacho"))
        valido, motivo = despacho.validar()
        if not valido:
            self._enviar(conexion, {"type": T_ERROR, "mensaje": motivo})
            return
        with self._lock:
            items = dict(self.carritos.get(usuario, {}))
            if not items:
                self._enviar(conexion, {"type": T_ERROR,
                                        "mensaje": "Tu carrito está vacío"})
                return

            detalle, subtotal = [], 0.0
            for id_producto, cantidad in sorted(items.items()):
                producto = self.inventario.buscar_por_id(id_producto)
                if producto is None:
                    continue
                subtotal_item = float(producto.precio) * cantidad
                subtotal += subtotal_item
                detalle.append({"id": producto.id, "nombre": producto.nombre,
                                "precio": producto.precio, "cantidad": cantidad,
                                "subtotal": subtotal_item})

            codigo_cupon = (mensaje or {}).get("cupon", "")
            ok, descuento, motivo = (
                self.gestor_cupones.consumir(codigo_cupon, subtotal)
                if codigo_cupon else (True, 0.0, "")
            )
            if not ok:
                self._enviar(conexion, {"type": T_ERROR, "mensaje": motivo})
                return
            envio = despacho.calcular(subtotal)
            subtotal_neto = subtotal - descuento
            iva = (subtotal_neto + envio) * 0.19
            total_final = subtotal_neto + iva + envio
            venta = self._guardar_venta(usuario, detalle, subtotal, envio, despacho,
                                        run=(mensaje or {}).get("run", ""),
                                        cupon=codigo_cupon, descuento=descuento)
            if venta is None:
                self._enviar(conexion, {"type": T_ERROR,
                                        "mensaje": "No se pudo registrar la venta"})
                return
            pedido = self.gestor_pedidos.crear_desde_venta(venta)
            self.carritos.pop(usuario, None)
            self.carritos_timestamps.pop(usuario, None)

        self._enviar(conexion, {"type": T_PAGO_OK, "total": total_final,
                                "subtotal": subtotal, "descuento": descuento,
                                "envio": envio, "iva": iva,
                                "id_pedido": pedido["id_pedido"],
                                "estado": pedido["estado"]})
        self._enviar(conexion, {"type": T_CARRITO_ESTADO, "items": []})
        self._difundir_pedidos(usuario)
        self.eventos.put({"type": T_PEDIDOS,
                          "pedidos": self.gestor_pedidos.todos()})
        if codigo_cupon:
            self.difundir_cupones()
        self._difundir_carritos()

    def _procesar_pregunta(self, conexion, mensaje):
        """
        el cliente pregunta al asistente. la llamada a gemini se hace solo
        aca, en el admin: la api key no viaja a las cajas cliente y el
        catalogo es el stock real de este instante.
        """
        pregunta = str(mensaje.get("pregunta") or "").strip()
        historial = mensaje.get("historial") or []
        with self._lock:
            productos = [p.to_dict() for p in self.inventario.productos]
        try:
            texto, error = consultar_gemini(pregunta, productos, historial)
        except Exception as e:  # paracaidas: consultar_gemini nunca lanza
            texto, error = None, f"Error inesperado del asistente: {e}"
        self._enviar(conexion, {"type": T_RESPUESTA, "pregunta": pregunta,
                                "texto": texto, "error": error})

    def _siguiente_id_venta(self, ventas):
        """Genera ID único: max(id_venta existente) + 1."""
        max_id = 0
        for v in ventas:
            try:
                vid = int(v.get("id_venta", 0) or 0)
            except (ValueError, TypeError, AttributeError):
                vid = 0
            if vid > max_id:
                max_id = vid
        return max_id + 1

    def _guardar_venta(self, usuario, detalle, subtotal, envio, despacho,
                       run=None, cupon=None, descuento=0.0):
        """Escribe la venta en data/ventas.json (la usa el panel del ADMIN)."""
        try:
            from datetime import datetime
            fecha = datetime.now().isoformat(timespec="seconds")
        except Exception:
            fecha = ""
        try:
            subtotal = float(subtotal)
            envio = float(envio or 0)
            descuento = min(max(0.0, float(descuento)), subtotal)
            subtotal_neto = subtotal - descuento
            iva = (subtotal_neto + envio) * 0.19
            total_final = subtotal_neto + envio + iva
            ventas = cargar_json(str(RUTA_VENTAS_JSON), default=[]) or []
            id_venta = self._siguiente_id_venta(ventas)
            despacho_dict = despacho.to_dict() if despacho is not None else Despacho().to_dict()
            venta = {
                "id_venta": id_venta, "cliente": usuario, "run": (run or "").strip(),
                "fecha": fecha, "items": detalle, "subtotal": subtotal,
                "cupon": cupon or None, "descuento": descuento,
                "subtotal_neto": subtotal_neto, "envio": envio,
                "despacho": despacho_dict, "iva": iva, "total": total_final,
            }
            ventas.append(venta)
            guardar_json(str(RUTA_VENTAS_JSON), ventas)
            return venta
        except Exception:
            return None   # que un problema de disco no tumbe la venta

    def _procesar_desconexion(self, conexion, usuario):
        """
        El cliente se fue (cerró la app o la ventana). Lo sacamos de la lista
        de conectados y le DEVOLVEMOS el stock que tenía reservado, porque ya
        no está mirando esa pantalla.
        """
        with self._lock:
            liberado, tocados = self._reconciliar(usuario, {}) if usuario else ({}, [])
            self.clientes.pop(conexion, None)

        try:
            conexion.close()
        except OSError:
            pass

        self._difundir_stock(tocados)
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

    def _difundir_stock(self, ids_producto):
        """Difunde el stock actualizado a cada caja conectada."""
        ids = set(ids_producto or [])
        if not ids:
            return
        with self._lock:
            conexiones = list(self.clientes.keys())
            cambios = []
            for id_producto in ids:
                producto = self.inventario.buscar_por_id(id_producto)
                if producto is not None:
                    cambios.append({"type": T_STOCK, "id": producto.id,
                                    "stock": producto.stock})
        for mensaje in cambios:
            for conexion in conexiones:
                self._enviar(conexion, mensaje)

    def difundir_inventario(self):
        """
        Avisa a todos el CATÁLOGO COMPLETO. Se llama desde la ventana del
        ADMIN cuando crea, edita o elimina un producto.
        """
        # Si se editó el precio normal de un producto, una promoción vigente
        # debe seguir teniendo prioridad antes de enviar el catálogo.
        self.gestor_ofertas.aplicar_a_inventario(self.inventario)
        anterior, actual = self._catalogo_anterior, self._catalogo_por_id()
        mensaje = {"type": T_INVENTARIO, "productos": self._catalogo()}
        with self._lock:
            conexiones = list(self.clientes.keys())
        for conexion in conexiones:
            self._enviar(conexion, mensaje)
        # Y a la bandeja, para que la ventana del ADMIN recargue su tabla.
        self.eventos.put(mensaje)
        self._notificar_cambios_catalogo(anterior, actual)
        self._catalogo_anterior = actual
        self._difundir_carritos()

    def aplicar_ofertas_y_difundir(self):
        """Recalcula precios de oferta tras crear o eliminar una promoción."""
        self.gestor_ofertas.aplicar_a_inventario(self.inventario)
        self.difundir_inventario()

    def _notificar_cambios_catalogo(self, anterior, actual):
        with self._lock:
            conexiones = {info.get("usuario"): c for c, info in self.clientes.items() if info.get("usuario")}
        for pid, nuevo in actual.items():
            viejo = anterior.get(pid)
            if viejo is None:
                continue
            if viejo["stock"] <= 0 < nuevo["stock"]:
                aviso = Notificacion("reposicion", f"{nuevo['nombre']} ya está disponible", id_producto=pid)
                for usuario in self.lista_deseos.usuarios_suscritos(pid):
                    with self._lock:
                        pendiente = self.lista_deseos.guardar_aviso(usuario, aviso.to_dict())
                    if usuario in conexiones:
                        self._enviar(conexiones[usuario], pendiente)
            if nuevo["precio"] < viejo["precio"]:
                texto = f"{nuevo['nombre']} bajó de ${viejo['precio']:,.0f} a ${nuevo['precio']:,.0f}"
                aviso = Notificacion("rebaja", texto, id_producto=pid)
                for usuario in self.lista_deseos.usuarios_con_favorito(pid):
                    with self._lock:
                        pendiente = self.lista_deseos.guardar_aviso(usuario, aviso.to_dict())
                    if usuario in conexiones:
                        self._enviar(conexiones[usuario], pendiente)

    def difundir_cupones(self):
        """Actualiza el catálogo de cupones en cada caja conectada."""
        mensaje = {"type": T_CUPONES,
                   "cupones": [c.to_dict() for c in self.gestor_cupones.cupones.values()]}
        with self._lock:
            conexiones = list(self.clientes.keys())
        for conexion in conexiones:
            self._enviar(conexion, mensaje)

    def difundir_tarifas(self):
        mensaje = {"type": T_TARIFAS, "config": self.gestor_tarifas.config}
        with self._lock:
            conexiones = list(self.clientes.keys())
        for conexion in conexiones:
            self._enviar(conexion, mensaje)

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

    # ------------------------------------------------------------------
    # PEDIDOS: creación, avance de estado y difusión
    # ------------------------------------------------------------------
    def avanzar_pedido(self, id_pedido):
        ok, mensaje, pedido = self.gestor_pedidos.avanzar(id_pedido)
        if ok and pedido is not None:
            self._difundir_pedido_estado(pedido)
            self.eventos.put({"type": T_PEDIDO_ESTADO, "pedido": pedido})
        return ok, mensaje, pedido

    def cancelar_pedido(self, id_pedido):
        """
        Cancela un pedido antes de despacharlo y DEVUELVE su stock.

        El pago descuenta el stock pero no lo devuelve; si el ADMIN cancela,
        esas unidades tienen que volver al inventario y las demás cajas deben
        enterarse por T_STOCK. El cliente dueño recibe el nuevo estado por
        T_PEDIDO_ESTADO.
        """
        ok, mensaje, pedido = self.gestor_pedidos.cancelar(id_pedido)
        if not ok or pedido is None:
            return ok, mensaje, pedido

        tocados = []
        with self._lock:
            for item in pedido.get("items") or []:
                if not isinstance(item, dict):
                    continue
                try:
                    id_producto = int(item.get("id"))
                    cantidad = int(item.get("cantidad") or 0)
                except (TypeError, ValueError):
                    continue
                if cantidad > 0 and self.inventario.devolver_stock(id_producto, cantidad):
                    tocados.append(id_producto)

        self._difundir_stock(sorted(set(tocados)))
        self._difundir_pedido_estado(pedido)
        self.eventos.put({"type": T_PEDIDO_ESTADO, "pedido": pedido})
        return ok, mensaje, pedido

    def _difundir_pedidos(self, usuario):
        pedidos = self.gestor_pedidos.de_cliente(usuario)
        mensaje = {"type": T_PEDIDOS, "pedidos": pedidos}
        with self._lock:
            conexiones = [
                conexion for conexion, info in self.clientes.items()
                if info.get("usuario") == usuario
            ]
        for conexion in conexiones:
            self._enviar(conexion, mensaje)

    def _difundir_pedido_estado(self, pedido):
        if not isinstance(pedido, dict):
            return
        mensaje = {"type": T_PEDIDO_ESTADO, "pedido": pedido}
        with self._lock:
            conexiones = [
                conexion for conexion, info in self.clientes.items()
                if info.get("usuario") == pedido.get("cliente")
            ]
        for conexion in conexiones:
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
