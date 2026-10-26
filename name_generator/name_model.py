"""Modelo de caracteres (RNN/LSTM/GRU) para generar nombres de dinosaurios.

Se usa tanto en el notebook de entrenamiento como en la aplicacion web (Fase 5).
"""
import json
from pathlib import Path

import torch
import torch.nn as nn


class CharRNN(nn.Module):
    def __init__(self, vocab_size, emb_dim=32, hidden_size=128, num_layers=1,
                 rnn_type="GRU", dropout=0.0, pad_id=0):
        super().__init__()
        self.rnn_type = rnn_type.upper()
        self.embedding = nn.Embedding(vocab_size, emb_dim, padding_idx=pad_id)
        rnn_cls = {"RNN": nn.RNN, "LSTM": nn.LSTM, "GRU": nn.GRU}[self.rnn_type]
        self.rnn = rnn_cls(emb_dim, hidden_size, num_layers=num_layers, batch_first=True,
                           dropout=dropout if num_layers > 1 else 0.0)
        self.drop = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, vocab_size)

    def forward(self, x, h=None):
        out, h = self.rnn(self.embedding(x), h)
        return self.fc(self.drop(out)), h


def _filter_logits(logits, top_k=None, top_p=None):
    """Aplica top-k y/o top-p a un vector de logits (1D)."""
    logits = logits.clone()
    if top_k is not None and top_k > 0:
        k = min(int(top_k), logits.size(-1))
        kth = torch.topk(logits, k).values[-1]
        logits[logits < kth] = float("-inf")
    if top_p is not None and top_p < 1.0:
        sorted_logits, sorted_idx = torch.sort(logits, descending=True)
        probs = torch.softmax(sorted_logits, dim=-1)
        cum = torch.cumsum(probs, dim=-1)
        remove = (cum - probs) >= top_p      # conserva el conjunto minimo cuya prob. acumulada alcanza p
        sorted_logits[remove] = float("-inf")
        logits = torch.full_like(logits, float("-inf")).scatter(0, sorted_idx, sorted_logits)
    return logits


@torch.no_grad()
def sample_name(model, vocab, temperature=1.0, top_k=None, top_p=None, min_len=3, max_len=None):
    """Genera un nombre de forma autoregresiva: cada caracter producido alimenta el siguiente paso."""
    model.eval()
    device = next(model.parameters()).device
    itos = vocab["itos"]
    pad, sos, eos = vocab["pad_id"], vocab["sos_id"], vocab["eos_id"]
    max_len = max_len or vocab["max_len"]

    x = torch.tensor([[sos]], device=device)
    h, out = None, []
    for step in range(max_len):
        logits, h = model(x, h)
        logits = logits[0, -1].float().clone()
        logits[pad] = float("-inf")
        logits[sos] = float("-inf")
        if step < min_len:
            logits[eos] = float("-inf")       # evita nombres demasiado cortos
        logits = logits / max(float(temperature), 1e-6)
        logits = _filter_logits(logits, top_k, top_p)
        probs = torch.softmax(logits, dim=-1)
        idx = torch.multinomial(probs, 1).item()
        if idx == eos:
            break
        out.append(itos[idx])
        x = torch.tensor([[idx]], device=device)
    return "".join(out)


def generate_novel(model, vocab, known, n=1, min_len=5, max_tries=1000, **sampling):
    """Devuelve hasta n nombres unicos que NO estan en `known` (conjunto de entrenamiento)."""
    found, seen = [], set()
    for _ in range(max_tries):
        name = sample_name(model, vocab, **sampling)
        if len(name) >= min_len and name not in known and name not in seen:
            found.append(name)
            seen.add(name)
            if len(found) == n:
                break
    return found


def load_model(artifacts_dir="name_generator/artifacts", device="cpu"):
    """Carga el modelo ya entrenado (sin reentrenar). Devuelve (model, vocab, known_names)."""
    d = Path(artifacts_dir)
    vocab = json.loads((d / "vocab.json").read_text(encoding="utf-8"))
    ckpt = torch.load(d / "char_model.pt", map_location=device, weights_only=True)
    model = CharRNN(**ckpt["model_kwargs"]).to(device)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    known = set(json.loads((d / "training_names.json").read_text(encoding="utf-8")))
    return model, vocab, known
