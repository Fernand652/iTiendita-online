"""
cliente.py
============================
El CLIENTE. Corre DENTRO del proceso del cliente (vistas/main_cliente.py).

Usa el mismo enfoque que el material de sockets que pasó el profe: socket
crudo, sendall() para escribir y recv(4096) + un buffer recortado por \n para
leer. Los \n son los finales de mensaje, porque recv() puede traer medio
mensaje o varios juntos.

Qué hace, en palabras simples:

  1. Abre un socket y se conecta al servidor del ADMIN. Si no hay nadie
     escuchando, avisa "no se pudo conectar" (con timeout, para que la ventana
     no se quede congelada esperando).

  2. Al conectarse manda un mensaje T_REGISTRO diciendo quién es.

  3. Se queda ESCUCHANDO en un hilo aparte. Cada cosa que manda el servidor
     (el catálogo, un cambio de stock, la confirmación de un pago) queda en una
     bandeja (self.cola).

  4. La ventana del cliente lee esa bandeja con root.after(100, ...) y
     actualiza los widgets. La ventana JAMÁS espera al socket.

Ídem que en servidor.py: los hilos no tocan la ventana, solo la bandeja.
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
        T_ERROR, T_DESCONECTADO,
        empaquetar, extraer_mensajes, carrito_a_mensaje, normalizar_items,
        items_a_lista,
    )
except ImportError:  # ejecución directa dentro de red/
    from protocolo import (
        HOST, PUERTO, TAMANO_BUFFER,
        T_REGISTRO, T_CARRITO, T_QUITAR, T_VACIAR, T_PAGO,
        T_INVENTARIO, T_STOCK, T_CARRITO_ESTADO, T_PAGO_OK,
        T_ERROR, T_DESCONECTADO,
        empaquetar, extraer_mensajes, carrito_a_mensaje, normalizar_items,
        items_a_lista,
    )


class ConexionServidor(threading.Thread):
    """
    Conexión del CLIENTE con el SERVIDOR.

    Uso típico:

        conexion = ConexionServidor(HOST, PUERTO)
        if conexion.conectar():
            conexion.registrarse("ana", "normal")
        # ... en la ventana, cada 100 ms:
        while True:
            mensaje = conexion.sacar_mensaje()
            if mensaje is None: break
            ...  # actualizar la pantalla
    """

    def __init__(self, host=HOST, puerto=PUERTO):
        super().__init__(daemon=True)
        self.host = host
        self.puerto = puerto

        self._socket = None

        self.cola = queue.Queue()   # bandeja: mensaje -> ventana
        self.error = None           # texto del último error de conexión
        self.conectado = False
        self.usuario = ""           # se completa al registrarse()

    # ------------------------------------------------------------------
    # CONEXIÓN
    # ------------------------------------------------------------------
    def conectar(self, timeout=3):
        """
        Intenta conectarse al servidor. Retorna True/False.

        El timeout es IMPORTANTÍSIMO: si el ADMIN no está prendido, la
        conexión se queda esperando para siempre y la ventana se congela. Con
        timeout falla rápido y podemos mostrar un mensaje.
        """
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(timeout)
            self._socket.connect((self.host, self.puerto))
            # A partir de ahora la conexión es persistente, sin timeout.
            self._socket.settimeout(None)
            self.conectado = True
            self.error = None
            return True
        except OSError as e:
            self.error = (
                f"No se pudo conectar con el servidor ({self.host}:{self.puerto}).\n"
                f"¿El ADMIN está prendido? Detalle: {e}"
            )
            self.conectado = False
            return False

    def registrarse(self, usuario, rol="normal"):
        """Se presenta ante el servidor. El servidor le manda el catálogo."""
        self.usuario = usuario
        return self.enviar({"type": T_REGISTRO, "usuario": usuario, "rol": rol})

    # ------------------------------------------------------------------
    # OPERACIONES DEL CARRITO (las 5 que hoy hace RetroVaultApp en local)
    # ------------------------------------------------------------------
    def enviar_carrito(self, items):
        """
        Manda el carrito completo.

        items: [{"id": 1, "cantidad": 2}, ...]
        """
        return self.enviar(carrito_a_mensaje(self.usuario, items))

    def quitar_producto(self, id_producto, cantidad=1):
        """Saca unidades de un producto del carrito (el stock vuelve)."""
        return self.enviar({"type": T_QUITAR, "usuario": self.usuario,
                            "id": int(id_producto), "cantidad": int(cantidad)})

    def vaciar_carrito(self):
        """Pide vaciar el carrito entero."""
        return self.enviar({"type": T_VACIAR, "usuario": self.usuario})

    def pagar(self):
        """Confirma la compra de lo que hay en el carrito."""
        return self.enviar({"type": T_PAGO, "usuario": self.usuario})

    # ------------------------------------------------------------------
    # ENVÍO
    # ------------------------------------------------------------------
    def enviar(self, mensaje):
        """Manda un dict cualquiera. Nunca lanza excepciones."""
        if not self.conectado or self._socket is None:
            return False
        try:
            self._socket.sendall(empaquetar(mensaje))
            return True
        except (OSError, AttributeError):
            self.conectado = False
            return False

    # ------------------------------------------------------------------
    # ESCUCHA (cuerpo del hilo)
    # ------------------------------------------------------------------
    def run(self):
        """
        Lee todo lo que manda el servidor y lo deja en la bandeja.

        Acá está el detalle que hace el profe en su material: recv(4096)
        devuelve bytes pelados, no mensajes. Puede llegar la mitad de un
        mensaje, o tres mensajes completos de un tirón. Por eso vamos
        guardando lo que sobra en un buffer y vamos cortando por los \n.
        """
        if self._socket is None:
            return
        buffer = ""
        try:
            while True:
                datos = self._socket.recv(TAMANO_BUFFER)
                if not datos:
                    break  # el servidor cerró la conexión

                mensajes, buffer = extraer_mensajes(buffer, datos)
                for mensaje in mensajes:
                    self.cola.put(mensaje)
        except (OSError, ValueError):
            pass
        finally:
            self.conectado = False
            # Aviso para que la ventana muestre "se perdió la conexión".
            self.cola.put({"type": T_DESCONECTADO})

    # ------------------------------------------------------------------
    # BANDEJA
    # ------------------------------------------------------------------
    def sacar_mensaje(self):
        """
        Saca UN mensaje de la bandeja, o None si está vacía.
        La ventana la llama en un bucle con root.after().
        """
        try:
            return self.cola.get_nowait()
        except queue.Empty:
            return None

    def cerrar(self):
        """Cierra la conexión con el servidor."""
        self.conectado = False
        try:
            if self._socket is not None:
                self._socket.close()
        except OSError:
            pass


if __name__ == "__main__":
    # Prueba rápida: hay que tener el servidor corriendo en otra terminal
    # (py red/servidor.py) antes de correr esto.
    import time

    print(f"Intentando conectar a {HOST}:{PUERTO} ...")
    conexion = ConexionServidor()

    if not conexion.conectar():
        print("FALLO:", conexion.error)
        print("-> Prendé el servidor primero:  py red/servidor.py")
    else:
        conexion.start()
        conexion.registrarse("cliente_prueba", "normal")
        print("Conectado. Esperando mensajes del servidor (5s)...")

        fin = time.time() + 5
        while time.time() < fin:
            mensaje = conexion.sacar_mensaje()
            if mensaje is not None:
                tipo = mensaje.get("type")
                if tipo == T_INVENTARIO:
                    print(f"  -> Catalogo con {len(mensaje.get('productos', []))} productos")
                    conexion.enviar_carrito([{"id": 1, "cantidad": 2}])
                else:
                    print("  ->", mensaje)
            time.sleep(0.1)

        conexion.cerrar()
        print("Prueba terminada.")