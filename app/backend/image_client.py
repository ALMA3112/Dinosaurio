"""Cliente de la API de imagenes (Colab + ngrok #2). Contrato en docs/fase4_imagen.md."""
import json
import urllib.error
import urllib.request

HEADERS = {"Content-Type": "application/json", "ngrok-skip-browser-warning": "true"}


class ImageError(RuntimeError):
    pass


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
        raise ImageError(f"La API de imágenes respondió HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}")
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
