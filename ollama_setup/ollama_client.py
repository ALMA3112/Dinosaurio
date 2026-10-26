"""Cliente minimo de Ollama (solo libreria estandar) y generador de la identidad del dinosaurio.

Se usa en el notebook de la Fase 3 y lo reutiliza el backend de la aplicacion (Fases 5-6).
La URL se lee de la variable de entorno OLLAMA_URL (por defecto, Ollama local en el mismo equipo).
"""
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
HEADERS = {"Content-Type": "application/json", "ngrok-skip-browser-warning": "true"}

CAMPOS = ["apariencia", "habitat", "alimentacion", "comportamiento", "caracteristica_distintiva"]
ETIQUETAS = {
    "apariencia": "Apariencia",
    "habitat": "Hábitat",
    "alimentacion": "Alimentación",
    "comportamiento": "Comportamiento",
    "caracteristica_distintiva": "Característica distintiva",
}

SYSTEM_IDENTIDAD = (
    "Eres un paleontólogo y escritor de fichas de especies ficticias. "
    "Respondes siempre en español, con rasgos coherentes entre sí."
)


class OllamaError(RuntimeError):
    pass


def _request(path, payload=None, url=None, timeout=900):
    base = (url or OLLAMA_URL).rstrip("/")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(base + path, data=data, headers=HEADERS,
                                 method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise OllamaError(f"Ollama respondió HTTP {e.code} en {path}: {e.read().decode('utf-8', 'ignore')[:300]}")
    except urllib.error.URLError as e:
        raise OllamaError(f"No se pudo conectar con Ollama en {base} ({e.reason}). "
                          "¿Está corriendo el contenedor? Ejecute ollama_setup/01_instalar_ollama.sh")


def version(url=None):
    return _request("/api/version", url=url, timeout=30)["version"]


def list_models(url=None):
    return _request("/api/tags", url=url, timeout=30).get("models", [])


def info_modelo(modelo, url=None):
    """Detalles del modelo (familia, tamaño de parámetros, cuantización) y su digest."""
    show = _request("/api/show", {"model": modelo}, url=url, timeout=60)
    det = show.get("details", {})
    digest = next((m.get("digest", "") for m in list_models(url) if m.get("name") == modelo), "")
    return {
        "modelo": modelo,
        "digest": digest,
        "family": det.get("family"),
        "parameter_size": det.get("parameter_size"),
        "quantization_level": det.get("quantization_level"),
    }


def generate(modelo, prompt, system=None, fmt=None, temperature=0.7, num_predict=500,
             seed=None, keep_alive="2m", url=None):
    options = {"temperature": temperature, "num_predict": num_predict, "num_ctx": 2048}
    if seed is not None:
        options["seed"] = seed
    payload = {"model": modelo, "prompt": prompt, "stream": False, "keep_alive": keep_alive, "options": options}
    if system:
        payload["system"] = system
    if fmt:
        payload["format"] = fmt
    t0 = time.time()
    r = _request("/api/generate", payload, url=url)
    r["wall_s"] = time.time() - t0
    return r


def chat(modelo, messages, system=None, temperature=0.7, num_predict=350, keep_alive="10m", url=None):
    """Conversacion (Fase 5). `system` lleva la identidad del dinosaurio como contexto."""
    msgs = ([{"role": "system", "content": system}] if system else []) + list(messages)
    payload = {"model": modelo, "messages": msgs, "stream": False, "keep_alive": keep_alive,
               "options": {"temperature": temperature, "num_predict": num_predict, "num_ctx": 2048}}
    return _request("/api/chat", payload, url=url)["message"]["content"]


# ---------------------------------------------------------------- identidad del dinosaurio
def build_identity_prompt(nombre):
    return (
        f'Se ha creado una nueva especie de dinosaurio ficticia llamada "{nombre}".\n'
        "Inventa su identidad. Los nombres reales de dinosaurios combinan raíces griegas; por ejemplo:\n"
        "- -saurus significa lagarto (Brachiosaurus: lagarto con brazos grandes)\n"
        "- -raptor significa ladrón o cazador veloz (Velociraptor: ladrón veloz)\n"
        "- -odon significa diente (Iguanodon: diente de iguana)\n"
        "- -venator significa cazador (Afrovenator: cazador africano)\n"
        f'Usa el comienzo y el final de "{nombre}" como inspiración para sus rasgos.\n'
        "Reglas: los rasgos deben ser coherentes entre sí (la dieta debe coincidir con su dentadura y su tamaño; "
        "el hábitat con su apariencia y su comportamiento). No menciones que es ficticia.\n"
        "Responde SOLO con un objeto JSON con estas cinco claves, cada valor de 2 a 3 frases en español:\n"
        '{"apariencia": "...", "habitat": "...", "alimentacion": "...", '
        '"comportamiento": "...", "caracteristica_distintiva": "..."}'
    )


def _norm(texto):
    t = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower().strip().replace(" ", "_")


def parse_campos(texto):
    """Devuelve el dict con los 5 campos si el JSON es válido y completo; si no, None."""
    m = re.search(r"\{.*\}", texto or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(d, dict):
        return None
    d = {_norm(k): v for k, v in d.items()}
    campos = {}
    for k in CAMPOS:
        v = d.get(k)
        if isinstance(v, (list, tuple)):
            v = " ".join(map(str, v))
        elif isinstance(v, dict):
            v = " ".join(map(str, v.values()))
        if not isinstance(v, str) or len(v.strip()) < 20:
            return None
        campos[k] = v.strip()
    return campos


def armar_descripcion(campos):
    return "\n".join(f"{ETIQUETAS[k]}: {campos[k]}" for k in CAMPOS)


def _metrics(r):
    ev, dur = r.get("eval_count", 0), r.get("eval_duration", 0)
    return {
        "eval_count": ev,
        "tokens_s": (ev / (dur / 1e9)) if dur else 0.0,
        "load_s": r.get("load_duration", 0) / 1e9,
        "wall_s": r.get("wall_s", 0.0),
    }


def generar_identidad(nombre, modelo, temperature=0.7, seed=42, max_intentos=3, url=None):
    """Pide a Ollama la identidad del dinosaurio. Reintenta si el JSON llega incompleto."""
    prompt = build_identity_prompt(nombre)
    total, ultimo = 0.0, {}
    for i in range(1, max_intentos + 1):
        r = generate(modelo, prompt, system=SYSTEM_IDENTIDAD, fmt="json", temperature=temperature,
                     num_predict=600, seed=seed + i - 1, url=url)
        total += r.get("wall_s", 0.0)
        ultimo = r
        campos = parse_campos(r.get("response", ""))
        if campos:
            return {"ok": True, "modelo": modelo, "campos": campos, "descripcion": armar_descripcion(campos),
                    "raw": r.get("response", ""), "intentos": i, "metrics": _metrics(r), "total_s": total}
    return {"ok": False, "modelo": modelo, "campos": {}, "descripcion": ultimo.get("response", "").strip(),
            "raw": ultimo.get("response", ""), "intentos": max_intentos, "metrics": _metrics(ultimo), "total_s": total}
