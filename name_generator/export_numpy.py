"""Exporta el modelo de caracteres entrenado (PyTorch) a NumPy para usarlo en la app sin PyTorch.

Requiere torch y numpy. Ejecutar UNA vez, desde la raiz del repositorio (por ejemplo en Colab):
    !git clone https://github.com/ALMA3112/Dinosaurio.git && cd Dinosaurio && python name_generator/export_numpy.py

Genera en app/assets/: char_model.npz, char_model_meta.json y verifica que NumPy y PyTorch dan los mismos logits.
Tambien crea ../export_assets.zip (junto a la carpeta del repo) para descargarlo desde Colab.
"""
import json
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
ART = REPO / "name_generator" / "artifacts"
OUT = REPO / "app" / "assets"
sys.path.insert(0, str(REPO / "name_generator"))
sys.path.insert(0, str(REPO / "app" / "backend"))
from name_model import CharRNN  # noqa: E402
from name_numpy import NumpyCharRNN  # noqa: E402

OUT.mkdir(parents=True, exist_ok=True)
ckpt = torch.load(ART / "char_model.pt", map_location="cpu", weights_only=True)
mk, sd = ckpt["model_kwargs"], ckpt["state_dict"]

arrays = {"emb": sd["embedding.weight"].numpy(), "fc_w": sd["fc.weight"].numpy(), "fc_b": sd["fc.bias"].numpy()}
for l in range(mk["num_layers"]):
    arrays[f"w_ih_{l}"] = sd[f"rnn.weight_ih_l{l}"].numpy()
    arrays[f"w_hh_{l}"] = sd[f"rnn.weight_hh_l{l}"].numpy()
    arrays[f"b_ih_{l}"] = sd[f"rnn.bias_ih_l{l}"].numpy()
    arrays[f"b_hh_{l}"] = sd[f"rnn.bias_hh_l{l}"].numpy()
np.savez(OUT / "char_model.npz", **arrays)

meta = {"rnn_type": mk["rnn_type"].upper(), "hidden_size": mk["hidden_size"], "num_layers": mk["num_layers"],
        "vocab_size": mk["vocab_size"], "emb_dim": mk["emb_dim"], "pad_id": mk["pad_id"]}
(OUT / "char_model_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

# --- verificacion: mismos logits en PyTorch y NumPy
model = CharRNN(**mk)
model.load_state_dict(sd)
model.eval()
np_model = NumpyCharRNN(OUT / "char_model.npz", meta)
rng = np.random.default_rng(0)
worst = 0.0
for _ in range(5):
    ids = rng.integers(3, mk["vocab_size"], size=12)
    with torch.no_grad():
        ref, _ = model(torch.tensor(ids[None, :], dtype=torch.long))
    diff = np.abs(ref[0].numpy() - np_model.logits_sequence(ids)).max()
    worst = max(worst, float(diff))
print(f"Modelo {meta['rnn_type']} {meta['num_layers']}x{meta['hidden_size']}  |  diferencia maxima PyTorch vs NumPy: {worst:.2e}")
assert worst < 1e-4, "NumPy y PyTorch NO coinciden: no use estos pesos"
print("OK: la inferencia en NumPy coincide con PyTorch.")

zpath = REPO.parent / "export_assets.zip"
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(OUT / "char_model.npz", "app/assets/char_model.npz")
    z.write(OUT / "char_model_meta.json", "app/assets/char_model_meta.json")
print("Paquete para descargar:", zpath)
