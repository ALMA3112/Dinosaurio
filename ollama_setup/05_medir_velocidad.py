"""Mide donde esta el cuello de botella de Ollama en SageMaker: disco, CPU o recargas del modelo.

Uso (terminal de SageMaker, desde la raiz del repo):
    python3 ollama_setup/05_medir_velocidad.py            # modelo mistral:7b
    python3 ollama_setup/05_medir_velocidad.py qwen2.5:7b
Descarga el modelo de memoria, vacia la cache de disco y mide: lectura en frio del modelo, carga en frio y generacion.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

MODEL = sys.argv[1] if len(sys.argv) > 1 else "mistral:7b"
DATA = Path(os.environ.get("OLLAMA_DATA", "/home/ec2-user/SageMaker/ollama"))
URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")


def call(path, payload, timeout=900):
    req = urllib.request.Request(URL + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    d["wall"] = time.time() - t0
    return d


def blob_del_modelo():
    name, _, tag = MODEL.partition(":")
    man = DATA / "models/manifests/registry.ollama.ai/library" / name / (tag or "latest")
    for layer in json.loads(man.read_text())["layers"]:
        if layer["mediaType"].endswith("image.model"):
            return DATA / "models/blobs" / layer["digest"].replace(":", "-")
    raise SystemExit("No encontre el archivo del modelo en " + str(man))


def vaciar_cache():
    r = subprocess.run("sync; echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null", shell=True)
    if r.returncode != 0:
        print("   (aviso: no se pudo vaciar la cache de disco; las medidas de lectura pueden salir optimistas)")


print(f"== Medicion de velocidad con {MODEL} ==\n")
print("1. CPU y memoria")
cpu = next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), "?")
flags = open("/proc/cpuinfo").read()
print(f"   {os.cpu_count()} CPU virtuales | {cpu}")
print("   AVX2:", "si" if " avx2" in flags else "NO (Ollama sera muy lento)")
mem = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo")}
print(f"   RAM total {mem['MemTotal']/1e6:.1f} GB | disponible {mem['MemAvailable']/1e6:.1f} GB | swap usado {(mem['SwapTotal']-mem['SwapFree'])/1e6:.1f} GB")

print("\n2. Descargando el modelo de memoria y vaciando la cache de disco...")
call("/api/generate", {"model": MODEL, "keep_alive": 0}, timeout=60)
time.sleep(2)
vaciar_cache()

print("\n3. Lectura en frio del archivo del modelo (velocidad real del disco)")
blob = blob_del_modelo()
size = blob.stat().st_size
t0, leido = time.time(), 0
with open(blob, "rb", buffering=0) as f:
    while True:
        chunk = f.read(4 * 1024 * 1024)
        if not chunk:
            break
        leido += len(chunk)
dt = time.time() - t0
mbs = leido / 1e6 / dt
print(f"   {size/1e9:.2f} GB en {dt:.0f} s  =  {mbs:.0f} MB/s")
vaciar_cache()

print("\n4. Ollama: carga en frio (con las mismas opciones que la app) y generacion")
opts = {"num_ctx": 2048, "num_predict": 40, "temperature": 0.3}
prompt = "Describe en español, en dos frases, un dinosaurio inventado que vive cerca de un lago."
cold = call("/api/generate", {"model": MODEL, "prompt": prompt, "stream": False, "keep_alive": -1, "options": opts})
warm = call("/api/generate", {"model": MODEL, "prompt": prompt, "stream": False, "keep_alive": -1, "options": opts})


def resumen(nombre, d):
    pe, ev = d.get("prompt_eval_count", 0), d.get("eval_count", 0)
    pt, et = d.get("prompt_eval_duration", 1) / 1e9, d.get("eval_duration", 1) / 1e9
    print(f"   {nombre}: total {d['wall']:.1f} s | carga {d.get('load_duration', 0)/1e9:.1f} s | "
          f"lectura del prompt {pe/pt:.0f} tok/s | generacion {ev/et:.1f} tok/s ({ev} tokens)")
    return ev / et, d.get("load_duration", 0) / 1e9


resumen("En frio ", cold)
gen, _ = resumen("En caliente", warm)

print("\n== Conclusion ==")
if mbs < 60:
    print(f"* El DISCO es lento ({mbs:.0f} MB/s): cargar el modelo tarda ~{size/1e6/mbs:.0f} s. Solucion: no dejar que se descargue")
    print("  (keep_alive=-1, ya configurado), usar 06_precalentar.sh tras cada inicio, o un modelo mas pequeño (qwen2.5:3b).")
else:
    print(f"* El disco rinde bien ({mbs:.0f} MB/s).")
if gen < 2.5:
    print(f"* La CPU genera solo {gen:.1f} tokens/s: las respuestas largas tardaran. Solucion: modelo mas pequeño para el chat")
    print("  (OLLAMA_CHAT_MODEL=qwen2.5:3b) y respuestas cortas.")
else:
    print(f"* La generacion en caliente es aceptable ({gen:.1f} tokens/s).")
print("* Una vez cargado, la espera de cada mensaje es lectura del prompt + generacion; la carga solo ocurre al inicio.")
