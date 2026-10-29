"""Cliente de la API de imagenes (Colab + ngrok #2). Contrato en docs/fase4_imagen.md."""
import json
import re
import urllib.error
import urllib.request

HEADERS = {"Content-Type": "application/json", "ngrok-skip-browser-warning": "true"}


class ImageError(RuntimeError):
    pass


def resumir_error_http(code, body):
    """Convierte la respuesta de error (a veces una pagina HTML de ngrok) en una frase util."""
    body = body or ""
    m = re.search(r"ERR_NGROK_(\d+)", body)
    if m:
        causas = {"3200": "el túnel de ngrok está apagado o la URL es vieja (reinicie el túnel y actualice el .env)",
                  "8012": "ngrok funciona pero no logra conectar con el servicio local (¿Ollama o la API de imágenes caída?)",
                  "108": "la cuenta de ngrok ya tiene otra sesión abierta (use una cuenta distinta para cada túnel)"}
        return f"HTTP {code} de ngrok (ERR_NGROK_{m.group(1)}): " + causas.get(m.group(1), "revise el túnel de ngrok")
    texto = re.sub(r"<[^>]+>", " ", body)
    texto = re.sub(r"\s+", " ", texto).strip()[:200]
    if code == 503:
        return (f"HTTP 503 (servicio no disponible): {texto or 'sin detalle'}. Suele ser la API de imágenes ocupada "
                "o un proxy del sistema; espere un minuto y reintente.")
    return f"HTTP {code}: {texto or 'sin detalle'}"


def _request(url, path, payload=None, timeout=600):
    if not url:
        raise ImageError("IMAGE_API_URL no está configurada.")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url.rstrip("/") + path, data=data, headers=HEADERS,
                                 method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise ImageError(f"API de imágenes en {path}: " + resumir_error_http(e.code, e.read().decode("utf-8", "ignore")))
    except urllib.error.URLError as e:
        raise ImageError(f"No se pudo conectar con la API de imágenes ({e.reason}). "
                         "¿Sigue corriendo el notebook de Colab y la URL de ngrok es la actual?")


def health(url, timeout=8):
    return _request(url, "/health", timeout=timeout)


def generar(url, prompt, seed=0, size=1024, negative_prompt=None, steps=None, timeout=600):
    payload = {"prompt": prompt, "seed": int(seed), "size": int(size)}
    if steps:
        payload["steps"] = int(steps)
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    r = _request(url, "/generate", payload, timeout=timeout)
    if "image_base64" not in r:
        raise ImageError(f"Respuesta inesperada de la API de imágenes: {str(r)[:200]}")
    return r
