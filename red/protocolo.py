"""
protocolo.py
============================
El "idioma" que hablan el SERVIDOR (que corre en la máquina del ADMIN) y los
CLIENTES.

Idea central (la más importante de todo lo que hace el proyecto funcionar):

    Cada mensaje es un DICCIONARIO de Python que se convierte a texto JSON y
    se manda por el socket. Al final del texto se agrega un salto de línea
    (\n), que es el "punto" de la frase. El otro lado lee bytes con recv(),
    los va guardando en un BUFFER, y cada vez que encuentra un \n corta la
    frase y la convierte en diccionario.

    MENSAJE = una línea de texto JSON terminada en \n

Es EXACTAMENTE el formato del material de sockets que pasó el profe
(Client/Server_ProgProyV2.py), incluida la clave "type".

Conexión:
    - HOST = la IP de la computadora donde corre el ADMIN (el servidor).
    - PUERTO = 65433 (el mismo del profe)

Para probar en el mismo computador también sirve 127.0.0.1. Si cada
integrante prueba por su parte, alcanza con cambiar HOST por la IP de la
máquina donde se levantó el ADMIN (en Windows: ipconfig).
"""

import json

# ==============================================================================
# DIRECCIÓN Y PUERTO
# ==============================================================================
HOST = "127.0.0.1"
PUERTO = 65433

CODIFICACION = "utf-8"
TAMANO_BUFFER = 4096

# ==============================================================================
# TIPOS DE MENSAJE
# Son solo palabras claves: el "type" dice qué hacer con el mensaje.
# ==============================================================================

# --- Los que manda el CLIENTE al SERVIDOR ---
T_REGISTRO = "registro"
# "Acabo de conectarme, soy este usuario"
# {type, usuario, rol}

T_CARRITO = "carrito"
# "Este es mi carrito tal como lo tengo ahora" (modelo optimista)
# El servidor compara con lo que él tiene reservado y corrige si no puede.
# {type, usuario, items: [{id, cantidad}, ...]}

T_QUITAR = "quitar"
# "Sacá N unidades de este producto de mi carrito" (el stock vuelve)
# {type, usuario, id, cantidad}

T_VACIAR = "vaciar"
# "Vaciá mi carrito entero" {type, usuario}

T_PAGO = "pago"
# "Confirmo la compra de lo que tengo en el carrito"
# {type, usuario}

# --- Los que manda el SERVIDOR ---
T_INVENTARIO = "inventario"
# "Este es el catálogo completo, con el stock REAL"
# {type, productos: [{id, nombre, precio, stock, categoria, imagen}, ...]}

T_STOCK = "stock"
# "El stock real de este producto cambió a este número"
# {type, id, stock}

T_CARRITO_ESTADO = "carrito_estado"
# "Tu carrito realmente quedó así" (el servidor corrige al cliente)
# {type, items: [{id, cantidad}, ...]}

T_PAGO_OK = "pago_ok"
# "Compra registrada" {type, total}

T_CARRITOS = "carritos"
# Solo para el ADMIN: "así están todos los carritos ahora mismo"
# {type, carritos: {usuario: [{id, cantidad}, ...]}, conectados: [usuarios]}

T_ERROR = "error"
# {type, mensaje: "texto para mostrarle al usuario"}

T_DESCONECTADO = "desconectado"
# Aviso interno del cliente cuando se cae la conexión.


# ==============================================================================
# EMPAQUETADO / DESEMPAQUETADO
# Son puras y fáciles de testear por separado (ver tests/test_red.py).
# ==============================================================================

def empaquetar(mensaje):
    """
    Convierte un dict en la línea de bytes que viaja por el socket.

    dict -> texto JSON -> bytes + b"\n"
    """
    texto = json.dumps(mensaje, ensure_ascii=False)
    return (texto + "\n").encode(CODIFICACION)


def desempaquetar(linea):
    """
    Convierte una línea del socket de vuelta en un dict.

    bytes o texto -> dict
    Retorna None si la línea llegó corrupta, para que el programa no se caiga.
    """
    if isinstance(linea, str):
        linea = linea.encode(CODIFICACION)
    try:
        return json.loads(linea.decode(CODIFICACION))
    except (UnicodeDecodeError, ValueError):
        return None


def extraer_mensajes(buffer, datos):
    """
    Recorta del buffer todas las líneas completas que llegaron.

    Recibe los bytes que trajo recv() y devuelve (mensajes, buffer_restante).

    OJO, esto es importante: recv(4096) NO garantiza que llegue un mensaje
    entero. Puede llegar la mitad de un mensaje, o tres mensajes de golpe. Por
    eso guardamos lo que sobra en el buffer y lo pegamos con lo que venga
    después. Los \n son los separadores de frase.
    """
    if isinstance(datos, bytes):
        buffer += datos.decode(CODIFICACION)
    else:
        buffer += datos

    mensajes = []
    while "\n" in buffer:
        linea, buffer = buffer.split("\n", 1)
        if not linea.strip():
            continue
        mensaje = desempaquetar(linea)
        if isinstance(mensaje, dict):
            mensajes.append(mensaje)

    return mensajes, buffer


def carrito_a_mensaje(usuario, items):
    """
    Atajo: arma el mensaje T_CARRITO a partir del carrito de un cliente.

    items es una lista de {'id': int, 'cantidad': int}. NO son objetos
    Producto, porque por el socket solo viajan datos simples (JSON).
    """
    return {
        "type": T_CARRITO,
        "usuario": usuario,
        "items": [
            {"id": int(item["id"]), "cantidad": int(item["cantidad"])}
            for item in items
        ],
    }


def items_a_mensaje(items):
    """Invierte carrito_a_mensaje: [{"id":..,"cantidad":..}] -> mensaje T_CARRITO."""
    return {"type": T_CARRITO, "items": list(items)}


def normalizar_items(items):
    """
    Limpia la lista de items que llega por el socket:
      - descarta cantidades <= 0
      - si viene el mismo producto dos veces, las suma
      - ignora datos basura (ids que no son números)

    Entrada : [{"id": 1, "cantidad": 2}, ...]
    Salida  : {1: 2, 5: 1}   (id -> cantidad)
    """
    pedido = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        try:
            id_producto = int(item.get("id"))
            cantidad = int(item.get("cantidad", 0))
        except (TypeError, ValueError):
            continue
        if cantidad <= 0:
            continue
        pedido[id_producto] = pedido.get(id_producto, 0) + cantidad
    return pedido


def items_a_lista(pedido):
    """{id: cantidad} -> [{"id": .., "cantidad": ..}] (para viajar por JSON)."""
    return [{"id": pid, "cantidad": cant} for pid, cant in sorted(pedido.items())]


if __name__ == "__main__":
    # Prueba rápida sin sockets: ida y vuelta de un mensaje.
    original = {"type": T_CARRITO, "usuario": "ana",
                "items": [{"id": 1, "cantidad": 2}]}
    bytes_viaje = empaquetar(original)
    recovered = desempaquetar(bytes_viaje)
    print("Original   :", original)
    print("En el socket:", bytes_viaje)
    print("Recibido   :", recovered)
    print("¿Igual?    :", recovered == original)