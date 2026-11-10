"""
api_gemini.py
modulo del asistente de la tienda (hito: consultar al asistente).
manda la pregunta del cliente a la api de gemini junto con el catalogo
real de la tienda y devuelve la respuesta para mostrarla en el chat.
"""

import urllib.request
import json

API_KEY = "AQ.Ab8RN6JTCg7mMVgXM4-kghXd5ffa3G5hM1FaxfGc4B7Xr6hWcg"
MODELO = "gemini-2.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1/models/{MODELO}:generateContent?key={API_KEY}"


def armar_catalogo(productos):
    # convierte los productos en lineas de texto para mandarselas a gemini
    lineas = []
    for p in productos or []:
        if isinstance(p, dict):
            nombre = p.get("nombre")
            precio = p.get("precio")
            stock = p.get("stock")
            categoria = p.get("categoria")
        else:
            nombre = p.nombre
            precio = p.precio
            stock = p.stock
            categoria = getattr(p, "categoria", None)
        linea = f"- {nombre} | ${precio} | stock: {stock}"
        if categoria:
            linea += f" | {categoria}"
        lineas.append(linea)
    return "\n".join(lineas) or "(sin productos)"


def consultar_gemini(pregunta, productos, historial=None):
    # manda la pregunta del cliente a gemini con el catalogo de la tienda.
    # devuelve siempre (respuesta, error): uno de los dos es None
    if not str(pregunta or "").strip():
        return None, "Escribe una pregunta primero."

    mensaje = (
        "Eres el asistente de la tienda RetroVault. Responde en español, "
        "breve y amable, usando SOLO este catálogo:\n"
        + armar_catalogo(productos)
        + "\n\nPregunta del cliente: "
        + str(pregunta)
    )

    # el historial va antes de la pregunta nueva para que gemini tenga
    # contexto de la conversacion (p.ej. "y el mas barato de esos?")
    contenido = []
    for turno in historial or []:
        texto = "".join(p.get("text", "") for p in turno.get("parts", []))
        if turno.get("role") in ("user", "model") and texto:
            contenido.append({"role": turno["role"], "parts": [{"text": texto}]})
    contenido.append({"role": "user", "parts": [{"text": mensaje}]})

    datos = json.dumps({
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
        print(f"Error: {e.code}")
        print(e.read().decode("utf-8"))
        return None, f"Gemini rechazó la consulta (error {e.code})."
    except Exception as e:
        return None, f"No se pudo conectar con Gemini (¿hay internet?): {e}"


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
