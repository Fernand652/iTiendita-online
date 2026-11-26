"""
api_gemini.py
modulo del asistente de la tienda (hito: consultar al asistente).
manda la pregunta del cliente a la api de gemini junto con el catalogo
real de la tienda y devuelve la respuesta para mostrarla en el chat.
"""

import urllib.request
import json

API_KEY = "AQ.Ab8RN6IXe2zdfe8Mpq6nohtzU3A7cGoLlCzCNsi0XhzhwfTqGQ"
MODELO = "gemini-3.1-flash-lite"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"


def armar_catalogo(productos):
    # convierte los productos en lineas de texto para mandarselas a gemini
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
        "Usa SOLO este catalogo (nombre, categoria, precio, stock y descripcion):\n"
        + armar_catalogo(productos)
    )


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

    req = urllib.request.Request(URL, data=datos,
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
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
        if e.code in (400, 401, 403):
            return None, "API key invalida o sin permisos. Revisa modelos/api_gemini.py en el ADMIN."
        if e.code == 429:
            return None, "Limite de solicitudes excedido. Espera un momento y vuelve a intentar."
        return None, f"Gemini rechazo la consulta (error {e.code})."
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            return None, "Tiempo de espera agotado al consultar Gemini. Intenta otra vez."
        return None, f"No se pudo conectar con Gemini: {e.reason}"
    except TimeoutError:
        return None, "Tiempo de espera agotado al consultar Gemini. Intenta otra vez."
    except Exception as e:
        return None, f"No se pudo conectar con Gemini: {e}"


if __name__ == "__main__":
    # prueba: primero lista los modelos disponibles y despues hace una
    # consulta de ejemplo del asistente con productos demo
    url = f"https://generativelanguage.googleapis.com/v1/models?key={API_KEY}"

    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            modelos = json.loads(response.read().decode("utf-8"))
            print("--- Modelos disponibles en tu proyecto ---")
            for modelo in modelos.get("models", []):
                print(f"- {modelo['name']}")
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code}")
        print(e.read().decode("utf-8"))

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
