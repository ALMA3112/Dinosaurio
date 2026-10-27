"""Inferencia del modelo de caracteres con NumPy (sin PyTorch).

Reproduce CharRNN (RNN / LSTM / GRU) de name_generator/name_model.py a partir de los pesos exportados con
name_generator/export_numpy.py. Asi el generador de nombres corre en AWS Lambda sin instalar PyTorch.
El muestreo (temperatura, top-k, top-p) replica sample_name() del modelo original.
"""
import json
from pathlib import Path

import numpy as np


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


class NumpyCharRNN:
    def __init__(self, npz_path, meta):
        d = np.load(npz_path)
        self.rnn_type = meta["rnn_type"].upper()
        self.H = int(meta["hidden_size"])
        self.L = int(meta["num_layers"])
        self.emb = d["emb"].astype(np.float64)
        self.fc_w = d["fc_w"].astype(np.float64)
        self.fc_b = d["fc_b"].astype(np.float64)
        self.layers = [{k: d[f"{k}_{l}"].astype(np.float64) for k in ("w_ih", "w_hh", "b_ih", "b_hh")}
                       for l in range(self.L)]

    def init_state(self):
        return [(np.zeros(self.H), np.zeros(self.H)) for _ in range(self.L)]

    def step(self, idx, state):
        """Un paso: devuelve (logits, nuevo_estado)."""
        x = self.emb[idx]
        H = self.H
        new = []
        for p, (h, c) in zip(self.layers, state):
            gi = p["w_ih"] @ x + p["b_ih"]
            gh = p["w_hh"] @ h + p["b_hh"]
            if self.rnn_type == "GRU":                         # orden de PyTorch: r, z, n
                r = _sigmoid(gi[:H] + gh[:H])
                z = _sigmoid(gi[H:2 * H] + gh[H:2 * H])
                n = np.tanh(gi[2 * H:] + r * gh[2 * H:])
                h = (1.0 - z) * n + z * h
            elif self.rnn_type == "LSTM":                      # orden de PyTorch: i, f, g, o
                g = gi + gh
                i, f, gg, o = g[:H], g[H:2 * H], g[2 * H:3 * H], g[3 * H:]
                c = _sigmoid(f) * c + _sigmoid(i) * np.tanh(gg)
                h = _sigmoid(o) * np.tanh(c)
            else:                                              # RNN con tanh
                h = np.tanh(gi + gh)
            new.append((h, c))
            x = h
        return self.fc_w @ x + self.fc_b, new

    def logits_sequence(self, ids):
        """Logits para cada posicion de una secuencia (usado para verificar contra PyTorch)."""
        state, out = self.init_state(), []
        for i in ids:
            lg, state = self.step(int(i), state)
            out.append(lg)
        return np.stack(out)


def load_model(assets_dir):
    d = Path(assets_dir)
    meta = json.loads((d / "char_model_meta.json").read_text(encoding="utf-8"))
    vocab = json.loads((d / "vocab.json").read_text(encoding="utf-8"))
    known = set(json.loads((d / "training_names.json").read_text(encoding="utf-8")))
    return NumpyCharRNN(d / "char_model.npz", meta), vocab, known


def _filter_logits(logits, top_k=None, top_p=None):
    logits = logits.copy()
    if top_k:
        k = min(int(top_k), logits.size)
        kth = np.sort(logits)[::-1][k - 1]
        logits[logits < kth] = -np.inf
    if top_p is not None and top_p < 1.0:
        idx = np.argsort(-logits)
        s = logits[idx]
        pr = np.exp(s - s.max())
        pr /= pr.sum()
        cum = np.cumsum(pr)
        s[(cum - pr) >= top_p] = -np.inf          # conjunto minimo cuya probabilidad acumulada alcanza p
        out = np.full_like(logits, -np.inf)
        out[idx] = s
        logits = out
    return logits


def sample_name(model, vocab, rng, temperature=1.0, top_k=None, top_p=None, min_len=3, max_len=None):
    itos = vocab["itos"]
    pad, sos, eos = vocab["pad_id"], vocab["sos_id"], vocab["eos_id"]
    max_len = max_len or vocab["max_len"]
    state, idx, out = model.init_state(), sos, []
    for step in range(max_len):
        logits, state = model.step(idx, state)
        logits[pad] = -np.inf
        logits[sos] = -np.inf
        if step < min_len:
            logits[eos] = -np.inf                  # evita nombres demasiado cortos
        logits = logits / max(float(temperature), 1e-6)
        logits = _filter_logits(logits, top_k, top_p)
        p = np.exp(logits - logits.max())
        p /= p.sum()
        idx = int(rng.choice(len(p), p=p))
        if idx == eos:
            break
        out.append(itos[idx])
    return "".join(out)


def generate_novel(model, vocab, known, rng, n=1, min_len=5, max_tries=500, **sampling):
    found, seen = [], set()
    for _ in range(max_tries):
        name = sample_name(model, vocab, rng, **sampling)
        if len(name) >= min_len and name not in known and name not in seen:
            found.append(name)
            seen.add(name)
            if len(found) == n:
                break
    return found
