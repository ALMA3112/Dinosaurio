"""Empaqueta la aplicacion para AWS Lambda  ->  build/dinosaurio_lambda.zip

Uso (desde la raiz del repo, con internet para bajar NumPy para Linux):
    python app/build_lambda.py
Opciones:  --sin-numpy   (solo para pruebas: no descarga NumPy)

El zip contiene: el backend, el cliente de Ollama, el frontend, los assets (modelo de nombres en NumPy, imagen, vocabulario)
y NumPy compilado para Lambda (Linux x86_64, Python 3.12). La carpeta build/ no se sube a GitHub.
"""
import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "build"
PKG = OUT / "pkg"
ZIP = OUT / "dinosaurio_lambda.zip"
REQUERIDOS = ["char_model.npz", "char_model_meta.json", "vocab.json", "training_names.json",
              "model_info.json", "dinosaurio_inicial.json"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-numpy", action="store_true")
    args = ap.parse_args()

    assets = REPO / "app" / "assets"
    faltan = [f for f in REQUERIDOS if not (assets / f).exists()]
    if not list(assets.glob("*.png")):
        faltan.append("(imagen .png del dinosaurio)")
    if faltan:
        sys.exit("Faltan assets en app/assets: " + ", ".join(faltan) +
                 "\nEjecute python app/prepare_assets.py y la exportacion a NumPy (ver docs/fase5_app.md).")

    shutil.rmtree(OUT, ignore_errors=True)
    PKG.mkdir(parents=True)
    for f in ("core.py", "image_client.py", "name_numpy.py", "lambda_function.py"):
        shutil.copy(REPO / "app" / "backend" / f, PKG / f)
    shutil.copy(REPO / "ollama_setup" / "ollama_client.py", PKG / "ollama_client.py")
    shutil.copytree(REPO / "app" / "frontend", PKG / "frontend")
    shutil.copytree(assets, PKG / "assets")

    if not args.sin_numpy:
        print("Descargando NumPy para Lambda (Linux x86_64, Python 3.12)...")
        cmd = [sys.executable, "-m", "pip", "install", "numpy", "--target", str(PKG), "--implementation", "cp",
               "--python-version", "3.12", "--only-binary=:all:", "--upgrade", "--quiet"]
        for plat in ("manylinux2014_x86_64", "manylinux_2_17_x86_64", "manylinux_2_28_x86_64"):
            cmd += ["--platform", plat]
        subprocess.run(cmd, check=True)
        for d in list(PKG.rglob("__pycache__")) + [p for p in PKG.rglob("tests") if "numpy" in p.parts]:
            shutil.rmtree(d, ignore_errors=True)

    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(PKG.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(PKG))
    mb = ZIP.stat().st_size / 1e6
    print(f"Creado {ZIP.relative_to(REPO)}  ({mb:.1f} MB)")
    if mb > 50:
        print("AVISO: pasa de 50 MB; en la consola de Lambda suba el zip a S3 y use 'Upload from > Amazon S3 location'.")


if __name__ == "__main__":
    main()
