"""Diagnostico: prueba una por una las piezas de las que depende la app y dice cual falla.

Uso (desde la raiz del repo):  python app/diagnostico.py
Solo usa la biblioteca estandar. No imprime ningun token.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_env():
    p = REPO / ".env"
    env = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def http(method, url, payload=None, timeout=30):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", "ngrok-skip-browser-warning": "true"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), time.time() - t0
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}", time.time() - t0


def explain(code, body):
    m = re.search(r"ERR_NGROK_(\d+)", body or "")
    if m:
        c = m.group(1)
        return {"3200": "El túnel de ngrok está APAGADO o la URL es vieja. Reinicie el túnel y actualice el .env.",
                "8012": "ngrok funciona, pero el servicio de atrás (Ollama / API de imágenes) NO responde. Revise que esté corriendo.",
                "108": "La cuenta de ngrok ya tiene otra sesión abierta. Use una cuenta distinta para cada túnel."
                }.get(c, f"Error de ngrok ERR_NGROK_{c}: revise el túnel.")
    if code is None:
        return "Sin conexión (DNS, internet o proxy). Mensaje: " + (body or "")[:150]
    if code == 503:
        return ("503 sin código de ngrok: lo devuelve Ollama (ocupado, cargando el modelo, memoria) o un proxy. "
                "Espere 1-2 minutos y reintente; si persiste, reinicie el contenedor: sudo docker restart ollama")
    if code == 404:
        return "404: la URL no corresponde a un túnel activo (o ruta equivocada)."
    return f"HTTP {code}: " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body or ""))[:160]


def check(nombre, method, url, payload=None, timeout=30, show=None):
    code, body, dt = http(method, url, payload, timeout)
    ok = code == 200
    print(f"[{'OK ' if ok else 'FALLA'}] {nombre}  ({dt:.1f} s)")
    if ok:
        if show:
            print("      ", show(body))
    else:
        print("       →", explain(code, body))
    return ok, body


env = load_env()
print("== 1. Archivo .env ==")
if not env:
    print("[FALLA] No existe .env en la raíz del repo (copie .env.example a .env y complételo).")
for k in ("OLLAMA_URL", "IMAGE_API_URL"):
    v = env.get(k, "")
    problemas = []
    if not v or "REEMPLAZAR" in v:
        problemas.append("sin completar")
    if v.endswith("/"):
        problemas.append("termina en '/' (quítela)")
    if v[:1] in "\"'" or v[-1:] in "\"'":
        problemas.append("tiene comillas (quítelas)")
    if v and not v.startswith("https://") and not v.startswith("http://"):
        problemas.append("debe empezar con https://")
    print(f"[{'OK ' if not problemas else 'FALLA'}] {k} = {v or '(vacía)'} {'← ' + ', '.join(problemas) if problemas else ''}")
print(f"       OLLAMA_MODEL = {env.get('OLLAMA_MODEL', '(por defecto mistral:7b)')}")

print("\n== 2. Proxy del sistema ==")
prox = {k: os.environ[k] for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy")
        if os.environ.get(k)}
if prox:
    print("[AVISO] Hay un proxy configurado; Python lo usa también para ngrok y puede causar errores 503:")
    for k, v in prox.items():
        print(f"        {k}={v}")
    print("        Pruebe:  unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY  y vuelva a ejecutar la app.")
else:
    print("[OK ] Sin proxy.")

print("\n== 3. Ollama (SageMaker + ngrok #1) ==")
ou = env.get("OLLAMA_URL", "").rstrip("/")
model = env.get("OLLAMA_MODEL", "mistral:7b")
if ou and "REEMPLAZAR" not in ou:
    ok, _ = check("GET /api/version", "GET", ou + "/api/version",
                  show=lambda b: "versión " + json.loads(b).get("version", "?"))
    if ok:
        def tags(b):
            nombres = [m["name"] for m in json.loads(b).get("models", [])]
            return ("modelos: " + ", ".join(nombres)) + ("" if model in nombres else f"   ← ¡FALTA {model}!")
        check("GET /api/tags", "GET", ou + "/api/tags", show=tags)
        print("      (probando una generación corta; puede tardar hasta 3 minutos si el modelo debe cargarse...)")
        check("POST /api/generate", "POST", ou + "/api/generate",
              {"model": model, "prompt": "Di hola en una palabra.", "stream": False, "keep_alive": -1,
               "options": {"num_predict": 8, "num_ctx": 2048}},   # mismas opciones que la app: asi no fuerza una recarga
              timeout=240, show=lambda b: "respuesta: " + json.loads(b).get("response", "").strip()[:60])
else:
    print("[SALTADO] OLLAMA_URL sin configurar.")

print("\n== 4. API de imágenes (Colab + ngrok #2) ==")
iu = env.get("IMAGE_API_URL", "").rstrip("/")
if iu and "REEMPLAZAR" not in iu:
    ok, _ = check("GET /health", "GET", iu + "/health", show=lambda b: "modelo: " + str(json.loads(b).get("model")))
    if ok:
        print("      (probando una imagen pequeña real: 512 px, 4 pasos; unos segundos...)")
        def img_info(b):
            d = json.loads(b)
            return f"imagen recibida {d.get('width')}x{d.get('height')} en {d.get('seconds')} s (servidor)"
        ok2, body = check("POST /generate", "POST", iu + "/generate",
                          {"prompt": "a dinosaur, full body side view", "steps": 4, "size": 512, "seed": 1},
                          timeout=300, show=img_info)
        if not ok2:
            print("       Si dice OutOfMemory/CUDA: en Colab, Entorno de ejecución > Reiniciar sesión y volver a ejecutar el notebook.")
            print("       Si dice 404/ERR_NGROK: la URL cambió; copie la nueva IMAGE_API_URL al .env y REINICIE dev_server.py.")
else:
    print("[SALTADO] IMAGE_API_URL sin configurar.")

print("\n== 5. Servidor local de la app (http://localhost:8000) ==")
ok, body = check("GET /api/estado", "GET", "http://localhost:8000/api/estado", timeout=40,
                 show=lambda b: json.dumps(json.loads(b), ensure_ascii=False)[:230])
if not ok:
    print("       (¿Está corriendo?  python app/backend/dev_server.py)")
print("\nPegue esta salida completa si necesita ayuda.")
