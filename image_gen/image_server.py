"""Generacion de imagenes (SDXL por defecto, amused como alternativa rapida) y API Flask para la aplicacion web.

Se usa en el notebook de Colab (Fase 4) y en la integracion (Fase 5).
Contrato de la API:
  GET  /health    -> {"status": "ok", "model": ..., "model_key": ..., "device": ...}
  POST /generate  <- {"prompt": str, "negative_prompt"?: str, "seed"?: int, "steps"?: int, "guidance"?: float, "size"?: int}
                  -> {"image_base64": str (PNG), "mime": "image/png", "width", "height", "seed", "steps", "prompt", "seconds"}
"""
import base64
import io
import threading
import time
import urllib.request

MODELS = {
    # Calidad alta, cabe en una T4 (fp16, ~7 GB de VRAM). ~30-50 s por imagen de 1024x1024.
    "sdxl": dict(id="stabilityai/stable-diffusion-xl-base-1.0", steps=30, guidance=7.0, size=1024, max_size=1024),
    # Muy rapido (~3 s) pero de calidad baja: queda como alternativa.
    "amused": dict(id="amused/amused-512", steps=12, guidance=10.0, size=512, max_size=512),
}
DEFAULT_MODEL = "sdxl"
DEFAULT_NEGATIVE = ("cartoon, anime, 3d render, blurry, lowres, deformed, extra limbs, extra heads, "
                    "text, watermark, human")


def load_pipeline(model_key=DEFAULT_MODEL):
    import torch

    cfg = MODELS[model_key]
    if model_key == "sdxl":
        from diffusers import AutoencoderKL, DPMSolverMultistepScheduler, StableDiffusionXLPipeline

        if not torch.cuda.is_available():
            raise RuntimeError("SDXL necesita GPU. Active la GPU T4 en Colab.")
        vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
        pipe = StableDiffusionXLPipeline.from_pretrained(
            cfg["id"], vae=vae, torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)
        pipe = pipe.to("cuda")
    else:
        from diffusers import AmusedPipeline

        if torch.cuda.is_available():
            pipe = AmusedPipeline.from_pretrained(cfg["id"], variant="fp16", torch_dtype=torch.float16)
            pipe.vqvae.to(torch.float32)      # el vqvae produce NaN en fp16 (recomendacion del autor)
            pipe = pipe.to("cuda")
        else:
            pipe = AmusedPipeline.from_pretrained(cfg["id"]).to("cpu")
    pipe.dino_model_key = model_key
    return pipe


def _cfg(pipe):
    return MODELS[getattr(pipe, "dino_model_key", DEFAULT_MODEL)]


def generate_image(pipe, prompt, negative_prompt=DEFAULT_NEGATIVE, seed=0, steps=None, guidance=None, size=None):
    import torch

    cfg = _cfg(pipe)
    steps = int(steps or cfg["steps"])
    guidance = float(cfg["guidance"] if guidance is None else guidance)
    size = int(size or cfg["size"])
    gen = torch.Generator(device=pipe.device.type).manual_seed(int(seed))
    out = pipe(prompt, negative_prompt=negative_prompt, num_inference_steps=steps,
               guidance_scale=guidance, generator=gen, height=size, width=size)
    return out.images[0]


def image_to_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def create_app(pipe):
    from flask import Flask, jsonify, request

    app = Flask(__name__)
    lock = threading.Lock()                    # una generacion a la vez en la GPU
    key = getattr(pipe, "dino_model_key", DEFAULT_MODEL)
    cfg = MODELS[key]

    @app.after_request
    def cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, ngrok-skip-browser-warning"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return resp

    @app.get("/health")
    def health():
        return jsonify(status="ok", model=cfg["id"], model_key=key, device=str(pipe.device))

    @app.route("/generate", methods=["POST", "OPTIONS"])
    def generate():
        if request.method == "OPTIONS":
            return ("", 204)
        data = request.get_json(silent=True) or {}
        prompt = str(data.get("prompt", "")).strip()
        if not prompt:
            return jsonify(error="Falta 'prompt'"), 400
        if len(prompt) > 600:
            return jsonify(error="El prompt es demasiado largo (maximo 600 caracteres)"), 400
        try:
            seed = int(data.get("seed", 0))
            steps = max(1, min(50, int(data.get("steps", cfg["steps"]))))
            guidance = float(data.get("guidance", cfg["guidance"]))
            size = int(data.get("size", cfg["size"]))
            size = max(256, min(cfg["max_size"], (size // 64) * 64))   # multiplo de 64 dentro del limite del modelo
            negative = str(data.get("negative_prompt", DEFAULT_NEGATIVE))
            t0 = time.time()
            with lock:
                img = generate_image(pipe, prompt, negative, seed, steps, guidance, size)
            return jsonify(image_base64=image_to_b64(img), mime="image/png", width=img.width, height=img.height,
                           seed=seed, steps=steps, prompt=prompt, seconds=round(time.time() - t0, 2))
        except Exception as e:                  # noqa: BLE001
            return jsonify(error=f"{type(e).__name__}: {e}"), 500

    return app


def start_server(app, port=5000):
    """Arranca Flask en un hilo y espera a que /health responda."""
    t = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port, use_reloader=False, threaded=True),
                         daemon=True)
    t.start()
    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            return t
        except Exception:                       # noqa: BLE001
            time.sleep(1)
    raise RuntimeError("El servidor Flask no arranco")


def start_tunnel(port, authtoken, domain=None):
    """Abre el tunel de ngrok (cuenta #2) y devuelve la URL publica https.

    Con `domain` (el "dev domain" gratuito de la cuenta, p. ej. algo.ngrok-free.dev) la URL es SIEMPRE la misma.
    """
    from pyngrok import ngrok

    ngrok.set_auth_token(authtoken)
    opts = {"domain": domain.replace("https://", "").strip("/ ")} if domain else {}
    url = ngrok.connect(port, "http", **opts).public_url
    return url.replace("http://", "https://")
