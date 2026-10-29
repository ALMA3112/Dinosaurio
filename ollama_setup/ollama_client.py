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

# IMPORTANTE: Ollama RECARGA el modelo (200+ s en este disco) si dos peticiones usan opciones de ejecucion distintas
# (num_ctx, etc.). Por eso TODAS las peticiones (generate, chat, precarga, pruebas) usan exactamente estas opciones.
RUNNER_OPTIONS = {"num_ctx": 2048}
KEEP_ALIVE = -1          # un numero negativo = el modelo se queda en memoria (no se descarga por inactividad)

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
        return (f"HTTP 503 (servicio no disponible): {texto or 'sin detalle'}. Suele ser Ollama ocupado o cargando "
                "el modelo, o un proxy del sistema; espere un minuto y reintente.")
    return f"HTTP {code}: {texto or 'sin detalle'}"


def _request(path, payload=None, url=None, timeout=900):
    base = (url or OLLAMA_URL).rstrip("/")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(base + path, data=data, headers=HEADERS,
                                 method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise OllamaError(f"Ollama en {path}: " + resumir_error_http(e.code, e.read().decode("utf-8", "ignore")))
    except urllib.error.URLError as e:
        raise OllamaError(f"No se pudo conectar con Ollama en {base} ({e.reason}). "
                          "¿Está corriendo el contenedor? Ejecute ollama_setup/01_instalar_ollama.sh")


def version(url=None, timeout=30):
    return _request("/api/version", url=url, timeout=timeout)["version"]


def list_models(url=None, timeout=30):
    return _request("/api/tags", url=url, timeout=timeout).get("models", [])


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
             seed=None, keep_alive=KEEP_ALIVE, url=None):
    options = {"temperature": temperature, "num_predict": num_predict, **RUNNER_OPTIONS}
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


def chat(modelo, messages, system=None, temperature=0.6, num_predict=250, keep_alive=KEEP_ALIVE, url=None):
    """Conversacion (Fase 5). `system` lleva la identidad del dinosaurio como contexto."""
    msgs = ([{"role": "system", "content": system}] if system else []) + list(messages)
    payload = {"model": modelo, "messages": msgs, "stream": False, "keep_alive": keep_alive,
               "options": {"temperature": temperature, "num_predict": num_predict, **RUNNER_OPTIONS}}
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


# ---------------------------------------------------------------- prompt de imagen (Fase 5)
SYSTEM_PROMPT_IMAGEN = ("You write short English prompts for a text-to-image model (Stable Diffusion XL). "
                        "Output ONLY the prompt, on a single line, without quotes or explanations.")
PROMPT_IMAGEN_FINAL = "highly detailed paleoart, natural lighting"


def build_image_prompt_request(nombre, campos):
    return (
        f"Dinosaur name: {nombre}\n"
        "Spanish description of the animal:\n"
        f"- Apariencia: {campos.get('apariencia', '')}\n"
        f"- Hábitat: {campos.get('habitat', '')}\n"
        f"- Característica distintiva: {campos.get('caracteristica_distintiva', '')}\n\n"
        f"Write ONE English prompt of at most 40 words that starts with the name \"{nombre}\", then says it is a dinosaur, "
        "then \"full body side view\", then its main VISIBLE traits (body shape, tail, skin or feathers, crest, claws, teeth, "
        "limbs), then its habitat, and ends with \"" + PROMPT_IMAGEN_FINAL + "\". "
        "Describe only what can be seen: no behavior, no diet, no names of other animals."
    )


def limpiar_prompt_imagen(texto, nombre, max_chars=300):
    """Deja el prompt en una linea, sin comillas, con el nombre al inicio y dentro del limite de CLIP (77 tokens)."""
    t = (texto or "").strip().splitlines()[0] if (texto or "").strip() else ""
    t = t.strip(" \"'`*")
    t = re.sub(r"^(prompt|output)\s*:\s*", "", t, flags=re.I).strip(" \"'`*")
    if not t:
        return f"{nombre}, a dinosaur, full body side view, {PROMPT_IMAGEN_FINAL}"
    if nombre.lower() not in t.lower():
        t = f"{nombre}, {t}"
    if len(t) > max_chars:
        cut = t[:max_chars]
        t = cut[: cut.rfind(",")] if "," in cut else cut
        t = f"{t}, {PROMPT_IMAGEN_FINAL}"
    return t


def generar_prompt_imagen(nombre, campos, modelo, temperature=0.3, url=None):
    r = generate(modelo, build_image_prompt_request(nombre, campos), system=SYSTEM_PROMPT_IMAGEN,
                 temperature=temperature, num_predict=110, seed=11, url=url)
    return limpiar_prompt_imagen(r.get("response", ""), nombre)


# ---------------------------------------------------------------- version rapida para la app (Fase 5)
def build_identity_prompt_app(nombre):
    """Identidad breve + prompt de imagen en una sola llamada (menos tokens = mas rapido)."""
    return (
        f'Se ha creado una nueva especie de dinosaurio ficticia llamada "{nombre}".\n'
        "Inventa su identidad. Los nombres reales combinan raíces griegas (-saurus lagarto, -raptor ladrón veloz, "
        f'-odon diente, -venator cazador); usa el comienzo y el final de "{nombre}" como inspiración.\n'
        "Reglas: rasgos coherentes entre sí (dieta acorde a dentadura y tamaño; hábitat acorde a apariencia y "
        "comportamiento). No menciones que es ficticia. Sé breve.\n"
        "Responde SOLO con un objeto JSON con estas seis claves. Las cinco primeras en español, cada valor de 1 a 2 "
        "frases (máximo 30 palabras):\n"
        '{"apariencia": "...", "habitat": "...", "alimentacion": "...", "comportamiento": "...", '
        '"caracteristica_distintiva": "...", "prompt_imagen": "..."}\n'
        f'"prompt_imagen" va en inglés, máximo 40 palabras: empieza con "{nombre}", luego "a dinosaur", '
        '"full body side view", sus rasgos VISIBLES (forma del cuerpo, cola, piel o plumas, cresta, garras, dientes), '
        'su hábitat, y termina con "' + PROMPT_IMAGEN_FINAL + '". Sin comportamiento ni dieta.'
    )


def _prompt_de_json(texto):
    m = re.search(r"\{.*\}", texto or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(d, dict):
        return None
    v = {_norm(k): x for k, x in d.items()}.get("prompt_imagen")
    return v.strip() if isinstance(v, str) and len(v.strip()) >= 15 else None


def generar_identidad_app(nombre, modelo, temperature=0.7, seed=42, max_intentos=3, url=None):
    prompt = build_identity_prompt_app(nombre)
    total, ultimo = 0.0, {}
    for i in range(1, max_intentos + 1):
        r = generate(modelo, prompt, system=SYSTEM_IDENTIDAD, fmt="json", temperature=temperature,
                     num_predict=450, seed=seed + i - 1, url=url)
        total += r.get("wall_s", 0.0)
        ultimo = r
        campos = parse_campos(r.get("response", ""))
        if campos:
            p = _prompt_de_json(r["response"])
            return {"ok": True, "modelo": modelo, "campos": campos, "descripcion": armar_descripcion(campos),
                    "prompt_imagen": limpiar_prompt_imagen(p, nombre) if p else None,
                    "intentos": i, "metrics": _metrics(r), "total_s": total}
    return {"ok": False, "modelo": modelo, "campos": {}, "descripcion": "", "prompt_imagen": None,
            "intentos": max_intentos, "metrics": _metrics(ultimo), "total_s": total}


def precargar(modelo, keep_alive=KEEP_ALIVE, url=None):
    """Carga el modelo en memoria sin generar texto (evita la espera de la primera respuesta)."""
    return _request("/api/generate", {"model": modelo, "keep_alive": keep_alive, "options": dict(RUNNER_OPTIONS)},
                    url=url, timeout=300)
