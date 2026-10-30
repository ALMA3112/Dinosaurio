"""Revisa el repositorio contra los requisitos de la guia antes de entregar.

Uso (desde la raiz del repo):  python app/verificar_entrega.py
Comprueba: archivos requeridos, evidencias, textos pendientes de completar, secretos y archivos pesados.
Solo biblioteca estandar. Necesita git instalado.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
fallos, avisos = [], []

REQUERIDOS = {
    "Entregable": ["README.md"],
    "Generador de nombres (secciones 2 y 7)": [
        "name_generator/01_generador_nombres.ipynb", "name_generator/name_model.py",
        "name_generator/artifacts/char_model.pt", "name_generator/artifacts/vocab.json",
        "docs/analisis_nombres.md", "docs/configuraciones_entrenamiento.csv", "docs/comparacion_muestreo.csv",
        "docs/nombres_generados.csv", "docs/evidencias/curvas_perdida.png"],
    "SageMaker y Ollama (seccion 3)": [
        "ollama_setup/01_instalar_ollama.sh", "ollama_setup/lifecycle_on_start.sh",
        "ollama_setup/02_ollama_identidad.ipynb", "ollama_setup/ollama_client.py",
        "ollama_setup/identidad_dinosaurio.json", "docs/modelo_ollama.json", "docs/comparacion_modelos_ollama.md",
        "docs/fase2_sagemaker.md", "docs/evidencias/entorno_sagemaker.txt"],
    "Imagen (seccion 4)": [
        "image_gen/01_imagen_colab.ipynb", "image_gen/image_server.py", "image_gen/imagen_dinosaurio.json"],
    "Aplicacion (secciones 5 y 6)": [
        "app/frontend/index.html", "app/backend/core.py", "app/backend/lambda_function.py",
        "app/build_lambda.py", "app/assets/dinosaurio_inicial.json", "app/assets/char_model.npz",
        "docs/fase5_app.md", "docs/fase6_despliegue.md", ".env.example"],
}
PENDIENTES = {  # texto que deja la plantilla y debe reemplazarse por su analisis
    "docs/analisis_nombres.md": ["## Interpretacion propia (completar)"],
    "docs/comparacion_modelos_ollama.md": ["### Justificación (completar con sus palabras)"],
}
SECRETOS = [
    (r"NGROK_AUTHTOKEN\s*=\s*[A-Za-z0-9_]{15,}", "authtoken de ngrok"),
    (r"ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}", "token de GitHub"),
    (r"AKIA[A-Z0-9]{16}", "clave de acceso de AWS"),
    (r"aws_secret_access_key\s*=", "secreto de AWS"),
    (r"hf_[A-Za-z0-9]{30,}", "token de Hugging Face"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "clave privada"),
]


def git(*args):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return r.stdout


tracked = [f for f in git("ls-files").splitlines() if f]
if not tracked:
    sys.exit("No encuentro archivos versionados: ejecute este script dentro del repositorio (git).")

print("== 1. Archivos requeridos ==")
for grupo, archivos in REQUERIDOS.items():
    falta = [a for a in archivos if a not in tracked]
    print(f"[{'OK ' if not falta else 'FALTA'}] {grupo}")
    for a in falta:
        print("        sin versionar / ausente:", a)
        fallos.append(a)
if not any(f.startswith("image_gen/imagenes/") and f.endswith(".png") for f in tracked):
    print("[FALTA] imagen del dinosaurio en image_gen/imagenes/*.png"); fallos.append("image_gen/imagenes/*.png")
evid = [f for f in tracked if f.startswith("docs/evidencias/app_") and f.endswith(".png")]
print(f"[{'OK ' if evid else 'AVISO'}] capturas de la app en docs/evidencias/app_*.png ({len(evid)})")
if not evid:
    avisos.append("capturas de la aplicacion (docs/evidencias/app_*.png)")

print("\n== 2. Textos pendientes de completar ==")
for archivo, marcas in PENDIENTES.items():
    p = REPO / archivo
    if not p.exists():
        continue
    txt = p.read_text(encoding="utf-8")
    for m in marcas:
        if m in txt:
            seccion = txt.split(m, 1)[1]
            lineas = [l.strip("-• ").strip() for l in seccion.splitlines() if l.strip().startswith("-")]
            vacia = not lineas or all(l.endswith(":") for l in lineas)
            print(f"[{'PENDIENTE' if vacia else 'OK '}] {archivo}: {m.strip('# ')}")
            if vacia:
                fallos.append(f"completar {archivo}")
readme = (REPO / "README.md").read_text(encoding="utf-8") if (REPO / "README.md").exists() else ""
tiene_url = bool(re.search(r"https://[a-z0-9]+\.lambda-url\.[a-z0-9-]+\.on\.aws", readme))
print(f"[{'OK ' if tiene_url else 'FALTA'}] README con el enlace del sitio web desplegado")
if not tiene_url:
    fallos.append("enlace del sitio en README")
print(f"[{'OK ' if 'REEMPLAZAR' not in readme else 'FALTA'}] README sin marcas REEMPLAZAR")
if "REEMPLAZAR" in readme:
    fallos.append("README con REEMPLAZAR")

print("\n== 3. Secretos y archivos sensibles ==")
sens = [f for f in tracked if re.search(r"(^|/)\.env$|\.pem$|\.key$|credentials", f)]
print(f"[{'OK ' if not sens else 'FALLA'}] sin .env / .pem / credenciales versionados")
fallos += [f"archivo sensible versionado: {f}" for f in sens]
hallazgos = []
for f in tracked:
    p = REPO / f
    if not p.is_file() or p.stat().st_size > 3_000_000 or p.suffix in (".png", ".pt", ".npz", ".zip", ".pyc"):
        continue
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    for patron, nombre in SECRETOS:
        if re.search(patron, txt):
            hallazgos.append(f"{f}: {nombre}")
print(f"[{'OK ' if not hallazgos else 'FALLA'}] sin tokens ni claves en el contenido")
for h in hallazgos:
    print("        ", h)
    fallos.append(h)
hist = git("log", "-p", "--all", "-G", r"NGROK_AUTHTOKEN\s*=\s*[A-Za-z0-9_]{15,}|ghp_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16}")
print(f"[{'OK ' if not hist.strip() else 'FALLA'}] historial de git limpio de secretos")
if hist.strip():
    fallos.append("secreto en el historial de git (revoque el token y limpie el historial)")

print("\n== 4. Archivos pesados ==")
grandes = [(f, (REPO / f).stat().st_size / 1e6) for f in tracked if (REPO / f).is_file() and (REPO / f).stat().st_size > 50e6]
print(f"[{'OK ' if not grandes else 'AVISO'}] ningun archivo versionado supera 50 MB")
for f, mb in grandes:
    avisos.append(f"{f} pesa {mb:.0f} MB")

print("\n== Resultado ==")
for a in avisos:
    print("AVISO:", a)
if fallos:
    print(f"{len(fallos)} punto(s) por resolver antes de entregar:")
    for f in fallos:
        print("  -", f)
    sys.exit(1)
print("Todo en orden. Revise manualmente la lista de la seccion 9 de la guia sobre el sitio desplegado.")
