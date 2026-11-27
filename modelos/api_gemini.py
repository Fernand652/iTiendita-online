"""
api_gemini.py
modulo del asistente de la tienda (hito: consultar al asistente).
manda la pregunta del cliente a la api de gemini junto con el catalogo
real de la tienda y devuelve la respuesta para mostrarla en el chat.

La API key se puede dejar mas abajo o pasar por variable de entorno:
    PowerShell: $env:GEMINI_API_KEY = "AQ...."
    CMD:        set GEMINI_API_KEY=AQ....
Asi se puede renovar la key sin editar el codigo ni subirla a git.
"""

import os
import json
import urllib.request
import urllib.error

# 1) variable de entorno (recomendado) 2) key de respaldo en el archivo
API_KEY = (os.environ.get("GEMINI_API_KEY")
           or os.environ.get("GOOGLE_API_KEY")
           or "AQ.Ab8RN6Lq7uLPv_GJbdDx_zGa86V71nZVa2Mm-5Z0NvI7zAXv1A")
MODELO = os.environ.get("GEMINI_MODELO") or "gemini-3-flash-preview"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
URL = f"{BASE_URL}/{MODELO}:generateContent"


def armar_catalogo(productos):
    # convierte los productos en lineas de texto para mandarselas a gemini.
    # Se muestran TODOS, incluso los que tienen stock 0: el asistente puede
    # nombrarlos, pero el carrito no los reserva (lo bloquea el servidor).
    lineas = []
    for p in productos or []:
        if isinstance(p, dict):
            nombre = p.get("nombre")
            precio = p.get("precio")
            stock = p.get("stock")
            categoria = p.get("categoria")
            descripcion = p.get("descripcion")
        else:
            nombre = p.nombre
            precio = p.precio
            stock = p.stock
            categoria = getattr(p, "categoria", None)
            descripcion = getattr(p, "descripcion", None)
        linea = f"- {nombre} | ${precio} | stock: {stock}"
        if categoria:
            linea += f" | {categoria}"
        if descripcion:
            linea += f" | {descripcion}"
        lineas.append(linea)
    return "\n".join(lineas) or "(sin productos)"


def armar_instruccion(productos):
    # contexto (instruccion de sistema): tienda + catalogo vigente
    return (
        "Eres el asistente de RetroVault, una tienda de videojuegos y consolas retro. "
        "Responde breve y amable y solo sobre los productos de la tienda. "
        "Usa SOLO este catalogo (nombre, categoria, precio, stock y descripcion). "
        "Puedes mostrar productos con stock 0, pero si el cliente quiere agregar "
        "uno, avisa de que no hay existencias.\n"
        + armar_catalogo(productos)
    )


def _detalle_error(cuerpo):
    # lee el mensaje de error de google para saber si fue la key, el modelo, etc.
    # nunca devuelve la key (va en un header, no en el cuerpo del error)
    try:
        error = json.loads(cuerpo.decode("utf-8", "replace")).get("error") or {}
    except Exception:
        return ""
    partes = []
    if error.get("message"):
        partes.append(error["message"])
    for detalle in error.get("details") or []:
        if isinstance(detalle, dict) and detalle.get("reason"):
            partes.append(detalle["reason"])
    return " | ".join(partes)


def _mensaje_key(detalle):
    # 401/403 = la key no sirve: hay que generar una nueva en AI Studio
    return (
        "API key invalida o sin permisos. Genera una key nueva en Google AI Studio "
        "y actualiza GEMINI_API_KEY (o modelos/api_gemini.py) en el ADMIN. "
        + detalle
    ).strip()


def consultar_gemini(pregunta, productos, historial=None):
    # manda la pregunta del cliente a gemini con el catalogo de la tienda.
    # devuelve siempre (respuesta, error): uno de los dos es None
    if not str(pregunta or "").strip():
        return None, "Escribe una pregunta primero."

    # el historial va antes de la pregunta nueva para que gemini tenga
    # contexto de la conversacion (p.ej. "y el mas barato de esos?")
    contenido = []
    for turno in historial or []:
        texto = "".join(p.get("text", "") for p in turno.get("parts", []))
        if turno.get("role") in ("user", "model") and texto:
            contenido.append({"role": turno["role"], "parts": [{"text": texto}]})
    contenido.append({"role": "user", "parts": [{"text": str(pregunta)}]})

    # la tienda y el catalogo van como instruccion de sistema
    datos = json.dumps({
        "systemInstruction": {"parts": [{"text": armar_instruccion(productos)}]},
        "contents": contenido,
        "generationConfig": {"maxOutputTokens": 2000},
    }).encode("utf-8")

    # las keys nuevas de AI Studio (AQ....) van en el header x-goog-api-key
    req = urllib.request.Request(
        URL, data=datos,
        headers={"Content-Type": "application/json", "x-goog-api-key": API_KEY},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            cuerpo = json.loads(response.read().decode("utf-8"))
            candidatos = cuerpo.get("candidates") or []
            if not candidatos:
                return None, "Gemini no devolvió respuesta, prueba a reformular la pregunta."
            partes = (candidatos[0].get("content") or {}).get("parts") or []
            texto = "".join(p.get("text", "") for p in partes).strip()
            if not texto:
                return None, "Gemini respondió vacío, prueba otra vez."
            return texto, None
    except urllib.error.HTTPError as e:
        detalle = _detalle_error(e.read() or b"")
        if e.code in (401, 403):
            return None, _mensaje_key(detalle)
        if e.code == 404:
            return None, f"Modelo '{MODELO}' no encontrado. Revisa GEMINI_MODELO. {detalle}".strip()
        if e.code == 400:
            return None, f"Gemini rechazó la consulta (400). Revisa el modelo y el mensaje. {detalle}".strip()
        if e.code == 429:
            return None, "Límite de solicitudes excedido. Espera un momento y vuelve a intentar."
        return None, f"Gemini rechazó la consulta (error {e.code}). {detalle}".strip()
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            return None, "Tiempo de espera agotado al consultar Gemini. Intenta otra vez."
        return None, f"No se pudo conectar con Gemini: {e.reason}"
    except TimeoutError:
        return None, "Tiempo de espera agotado al consultar Gemini. Intenta otra vez."
    except Exception as e:
        return None, f"No se pudo conectar con Gemini: {e}"


def probar_conexion():
    # diagnostico: dice si la key sirve y que modelos tiene el proyecto.
    # la key NO se imprime nunca.
    req = urllib.request.Request(
        f"{BASE_URL}?pageSize=10",
        headers={"x-goog-api-key": API_KEY},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            modelos = json.loads(response.read().decode("utf-8"))
            print("OK: la API key funciona. Modelos disponibles:")
            for modelo in modelos.get("models", []):
                print(f"- {modelo['name']}")
            return True
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {_detalle_error(e.read() or b'')}")
    except Exception as e:
        print(f"No se pudo conectar con Gemini: {e}")
    return False


if __name__ == "__main__":
    # prueba: primero lista los modelos disponibles y despues hace una
    # consulta de ejemplo del asistente con productos demo
    print(f"Modelo configurado: {MODELO}")
    if probar_conexion():
        respuesta, error = consultar_gemini(
            "¿Qué productos tienen y cuál es el más barato?",
            [
                {"nombre": "Super Nintendo", "precio": 149990, "stock": 4, "categoria": "consolas"},
                {"nombre": "The Legend of Zelda: Ocarina of Time", "precio": 89990, "stock": 12, "categoria": "videojuegos"},
                {"nombre": "Super Mario 64", "precio": 99990, "stock": 0, "categoria": "videojuegos"},
            ],
        )
        print("--- Respuesta del asistente ---")
        if error:
            print(f"Error: {error}")
        else:
            print(respuesta)
