"""Logica del backend (independiente del servidor): enrutador de la API y servicio de archivos estaticos.

Lo usan dev_server.py (desarrollo local) y lambda_function.py (AWS Lambda). Contrato completo en docs/fase5_app.md.

Variables de entorno: OLLAMA_URL, OLLAMA_MODEL, IMAGE_API_URL, IMAGE_SIZE.
"""
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next((b for b in (HERE, HERE.parent) if (b / "assets").exists()), HERE.parent)
ASSETS = ROOT / "assets"
FRONT = ROOT / "frontend"
for _p in (HERE, ROOT.parent / "ollama_setup", ROOT / "ollama_setup"):
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

import image_client as ic  # noqa: E402
import name_numpy as nn  # noqa: E402
import ollama_client as oc  # noqa: E402

CORS = {"Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type, ngrok-skip-browser-warning",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS"}
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

DEFAULT_SAMPLING = {"temperature": 1.0, "top_k": None, "top_p": 0.9}
MAX_HISTORY = 6
MAX_MSG_CHARS = 600
MAX_DESC_CHARS = 3000


class BadRequest(ValueError):
    pass


def config():
    return {
        "ollama_url": os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        "ollama_model": os.environ.get("OLLAMA_MODEL", "mistral:7b"),
        "chat_model": os.environ.get("OLLAMA_CHAT_MODEL") or os.environ.get("OLLAMA_MODEL", "mistral:7b"),
        "image_url": os.environ.get("IMAGE_API_URL", ""),
        "image_size": int(os.environ.get("IMAGE_SIZE", "768")),
        "image_steps": int(os.environ.get("IMAGE_STEPS", "22")),
    }


# ------------------------------------------------------------------ modelo de caracteres
_MODEL = None


def get_model():
    global _MODEL
    if _MODEL is None:
        model, vocab, known = nn.load_model(ASSETS)
        info_path = ASSETS / "model_info.json"
        info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}
        _MODEL = (model, vocab, known, info)
    return _MODEL


def resumen_modelo(info):
    c = info.get("config", {})
    return {
        "configuracion": c.get("name"), "arquitectura": c.get("arch"), "capas": c.get("num_layers"),
        "estado_oculto": c.get("hidden_size"), "embedding": c.get("emb_dim"), "dropout": c.get("dropout"),
        "epocas": c.get("epochs"), "optimizador": c.get("optimizer"), "funcion_perdida": c.get("loss"),
        "parametros": info.get("parametros"), "mejor_epoca": info.get("mejor_epoca"),
        "mejor_perdida_validacion": info.get("mejor_val"), "vocabulario": info.get("vocab_size"),
        "longitud_maxima_T": info.get("T"),
    }


def clean_name(raw):
    nombre = re.sub(r"[^A-Za-z]", "", str(raw or ""))
    if not 3 <= len(nombre) <= 30:
        raise BadRequest("Nombre inválido (3 a 30 letras).")
    return nombre.capitalize()


# ------------------------------------------------------------------ chat
def _norm(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


_IMG_PATTERNS = re.compile(
    r"descri|apariencia|aspecto|como eres|como luces|como te ves|como es tu|imagen|foto|muestrate|"
    r"ensenate|dejame verte|presentate|quien eres|que eres|hablame de ti|cuentame de ti|cuentame sobre ti")


def quiere_ver_imagen(texto):
    """True si el usuario pide que el dinosaurio se presente o describa (entonces el mensaje lleva la imagen)."""
    return bool(_IMG_PATTERNS.search(_norm(texto)))


def build_chat_system(nombre, descripcion):
    return (
        f"Eres {nombre}, un dinosaurio ficticio que conversa con un visitante de la Isla de los Dinosaurios.\n"
        "Esta es tu identidad. Es un hecho: nunca la contradigas, solo puedes ampliarla con detalles compatibles.\n\n"
        f"{descripcion}\n\n"
        "Reglas: habla en primera persona y en español, con carácter de dinosaurio, curioso y amable; responde en "
        "2 o 3 frases cortas (máximo 60 palabras); no digas que eres una IA; si te preguntan algo que tu identidad "
        "no cubre, inventa un detalle coherente con ella; si te piden algo ajeno a tu mundo, responde brevemente "
        "desde tu vida de dinosaurio."
    )


INTRO_INSTRUCCION = ("Un visitante acaba de llegar. Preséntate en 2 frases cortas: tu nombre, cómo eres y dónde vives.")


# ------------------------------------------------------------------ endpoints
def api_estado(_data=None):
    c = config()
    out = {"modelo_ollama": c["ollama_model"]}
    try:
        modelos = [m["name"] for m in oc.list_models(c["ollama_url"], timeout=8)]
        out["ollama"] = {"ok": True, "version": oc.version(c["ollama_url"], timeout=8),
                         "modelo_instalado": c["ollama_model"] in modelos and c["chat_model"] in modelos}
    except Exception as e:  # noqa: BLE001
        out["ollama"] = {"ok": False, "error": str(e)[:200]}
    try:
        h = ic.health(c["image_url"])
        out["imagen"] = {"ok": True, "modelo": h.get("model")}
    except Exception as e:  # noqa: BLE001
        out["imagen"] = {"ok": False, "error": str(e)[:200]}
    return out


def api_modelo(_data=None):
    *_, info = get_model()
    return resumen_modelo(info)


def api_dinosaurio_inicial(_data=None):
    p = ASSETS / "dinosaurio_inicial.json"
    if not p.exists():
        raise FileNotFoundError("Falta app/assets/dinosaurio_inicial.json. Ejecute: python app/prepare_assets.py")
    d = json.loads(p.read_text(encoding="utf-8"))
    d["modelo_caracteres"] = api_modelo()
    return d


def api_nombre(data):
    model, vocab, known, info = get_model()
    t = min(2.0, max(0.2, float(data.get("temperature", DEFAULT_SAMPLING["temperature"]))))
    top_k = data.get("top_k", DEFAULT_SAMPLING["top_k"])
    top_p = data.get("top_p", DEFAULT_SAMPLING["top_p"])
    excluir = {re.sub(r"[^a-z]", "", str(n).lower()) for n in (data.get("excluir") or [])}
    names = nn.generate_novel(model, vocab, known | excluir, np.random.default_rng(), n=1,
                              temperature=t, top_k=top_k, top_p=top_p)
    if not names:
        raise RuntimeError("No se pudo generar un nombre nuevo; intente de nuevo.")
    return {"nombre": names[0].capitalize(), "es_nuevo": True,
            "muestreo": {"temperature": t, "top_k": top_k, "top_p": top_p},
            "modelo_caracteres": resumen_modelo(info)}


def api_identidad(data):
    c = config()
    nombre = clean_name(data.get("nombre"))
    seed = int.from_bytes(os.urandom(2), "big")
    res = oc.generar_identidad_app(nombre, c["ollama_model"], seed=seed, url=c["ollama_url"])
    if not res["ok"]:
        raise oc.OllamaError("Ollama no devolvió una identidad válida; intente de nuevo.")
    return {"nombre": nombre, "campos": res["campos"], "descripcion": res["descripcion"],
            "prompt_imagen": res["prompt_imagen"], "modelo_ollama": c["ollama_model"],
            "intentos": res["intentos"], "segundos": round(res["total_s"], 1)}


def api_imagen(data):
    c = config()
    nombre = clean_name(data.get("nombre"))
    campos = data.get("campos")
    if not isinstance(campos, dict) or not campos.get("apariencia"):
        raise BadRequest("Falta 'campos' con la identidad del dinosaurio.")
    campos = {k: str(v)[:800] for k, v in campos.items()}
    dado = str(data.get("prompt_imagen") or "").strip()
    if len(dado) >= 15:
        prompt = oc.limpiar_prompt_imagen(dado, nombre)          # ya viene redactado por la misma llamada de identidad
    else:                                                          # respaldo: pedir el prompt a Ollama (una llamada extra)
        prompt = oc.generar_prompt_imagen(nombre, campos, c["ollama_model"], url=c["ollama_url"])
    seed = int(data.get("seed", int.from_bytes(os.urandom(2), "big")))
    r = ic.generar(c["image_url"], prompt, seed=seed, size=c["image_size"], steps=c["image_steps"])
    return {"image_base64": r["image_base64"], "mime": r.get("mime", "image/png"), "prompt": prompt, "seed": seed,
            "size": c["image_size"], "steps": c["image_steps"], "segundos_imagen": r.get("seconds")}


def api_chat(data):
    c = config()
    nombre = clean_name(data.get("nombre"))
    descripcion = str(data.get("descripcion", "")).strip()[:MAX_DESC_CHARS]
    if len(descripcion) < 40:
        raise BadRequest("Falta la identidad ('descripcion') del dinosaurio.")
    intro = bool(data.get("intro"))
    msgs = []
    for m in (data.get("messages") or [])[-MAX_HISTORY:]:
        role = "assistant" if m.get("role") == "assistant" else "user"
        msgs.append({"role": role, "content": str(m.get("content", ""))[:MAX_MSG_CHARS]})
    if intro:
        msgs = [{"role": "user", "content": INTRO_INSTRUCCION}]
        show_image = True
    else:
        if not msgs or msgs[-1]["role"] != "user":
            raise BadRequest("El último mensaje debe ser del usuario.")
        show_image = quiere_ver_imagen(msgs[-1]["content"])
    reply = oc.chat(c["chat_model"], msgs, system=build_chat_system(nombre, descripcion),
                    num_predict=90 if intro else 130, url=c["ollama_url"])
    return {"reply": reply.strip(), "show_image": show_image}


def api_calentar(_data=None):
    """Precarga en memoria el/los modelos de Ollama para que la primera respuesta no espere la carga."""
    c = config()
    for m in {c["ollama_model"], c["chat_model"]}:
        oc.precargar(m, url=c["ollama_url"])
    return {"ok": True}


POST_ROUTES = {"/api/nombre": api_nombre, "/api/identidad": api_identidad, "/api/imagen": api_imagen,
               "/api/chat": api_chat, "/api/calentar": api_calentar}
GET_ROUTES = {"/api/estado": api_estado, "/api/modelo": api_modelo, "/api/dinosaurio-inicial": api_dinosaurio_inicial}


# ------------------------------------------------------------------ enrutador
def _json(status, obj):
    return {"status": status, "body": json.dumps(obj, ensure_ascii=False).encode("utf-8"),
            "headers": {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", **CORS}}


def _file(path, ctype):
    return {"status": 200, "body": path.read_bytes(), "headers": {"Content-Type": ctype, **CORS}}


def route(method, path, body=b""):
    """Devuelve {"status": int, "headers": dict, "body": bytes}."""
    path = (path or "/").split("?")[0]
    method = method.upper()
    try:
        if method == "OPTIONS":
            return {"status": 204, "body": b"", "headers": dict(CORS)}
        if method == "GET":
            if path in ("/", "/index.html"):
                return _file(FRONT / "index.html", "text/html; charset=utf-8")
            if path.startswith("/assets/"):
                name = path[len("/assets/"):]
                ext = Path(name).suffix.lower()
                f = ASSETS / name
                if Path(name).name != name or ext not in IMAGE_TYPES or not f.is_file():
                    return _json(404, {"error": "No encontrado"})
                return _file(f, IMAGE_TYPES[ext])
            if path in GET_ROUTES:
                return _json(200, GET_ROUTES[path]())
        elif method == "POST" and path in POST_ROUTES:
            try:
                data = json.loads(body.decode("utf-8")) if body else {}
            except (ValueError, UnicodeDecodeError):
                raise BadRequest("El cuerpo debe ser JSON válido.")
            if not isinstance(data, dict):
                raise BadRequest("El cuerpo debe ser un objeto JSON.")
            return _json(200, POST_ROUTES[path](data))
        return _json(404, {"error": "No encontrado"})
    except (BadRequest, ValueError) as e:
        return _json(400, {"error": str(e)})
    except (oc.OllamaError, ic.ImageError) as e:
        return _json(502, {"error": str(e)})
    except FileNotFoundError as e:
        return _json(500, {"error": str(e)})
    except Exception as e:  # noqa: BLE001
        return _json(500, {"error": f"{type(e).__name__}: {e}"})
