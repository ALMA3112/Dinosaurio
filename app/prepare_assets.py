"""Reune en app/assets/ los resultados de las fases anteriores que necesita la aplicacion.

Uso (desde la raiz del repo):  python app/prepare_assets.py
Copia: vocabulario, nombres de entrenamiento, info del modelo, identidad e imagen del dinosaurio inicial.
El archivo char_model.npz lo genera name_generator/export_numpy.py (necesita PyTorch).
"""
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
A = REPO / "app" / "assets"
A.mkdir(parents=True, exist_ok=True)


def need(path):
    if not path.exists():
        sys.exit(f"Falta {path.relative_to(REPO)}. Revise que las fases anteriores esten completas y con git pull.")
    return path


shutil.copy(need(REPO / "name_generator/artifacts/vocab.json"), A / "vocab.json")
shutil.copy(need(REPO / "name_generator/artifacts/training_names.json"), A / "training_names.json")
shutil.copy(need(REPO / "docs/modelo_seleccionado.json"), A / "model_info.json")

sel = json.loads(need(REPO / "name_generator/artifacts/nombre_seleccionado.json").read_text(encoding="utf-8"))
ident = json.loads(need(REPO / "ollama_setup/identidad_dinosaurio.json").read_text(encoding="utf-8"))
meta_img = json.loads(need(REPO / "image_gen/imagen_dinosaurio.json").read_text(encoding="utf-8"))
img_src = need(REPO / meta_img["archivo"])
shutil.copy(img_src, A / img_src.name)

inicial = {
    "nombre": ident["nombre"],
    "campos": {k: ident[k] for k in ("apariencia", "habitat", "alimentacion", "comportamiento", "caracteristica_distintiva")},
    "descripcion": ident["descripcion"],
    "modelo_ollama": ident["modelo_ollama"],
    "imagen_url": f"/assets/{img_src.name}",
    "prompt_imagen": meta_img["prompt"],
    "modelo_imagen": meta_img["modelo"],
    "seed": meta_img["seed"],
    "muestreo_nombre": sel.get("sampling"),
    "modelo_caracteres_nombre": sel.get("model"),
}
(A / "dinosaurio_inicial.json").write_text(json.dumps(inicial, indent=2, ensure_ascii=False), encoding="utf-8")

print("Assets copiados a app/assets/:", sorted(p.name for p in A.iterdir()))
for f in ("char_model.npz", "char_model_meta.json"):
    if not (A / f).exists():
        print(f"AVISO: falta app/assets/{f}. Ejecute name_generator/export_numpy.py (necesita PyTorch; ver docs/fase5_app.md).")
