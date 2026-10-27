"""Pruebas del backend sin servicios reales: Ollama e imagenes simulados y un modelo NumPy con pesos aleatorios.

Uso:  python app/tests/test_backend.py      (solo necesita numpy)
"""
import base64
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "ollama_setup"))

PNG_1PX = base64.b64encode(bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63fcffff3f0300"
    "06fe02fe5f3d1b9f0000000049454e44ae426082")).decode()
GOOD = {"apariencia": "Mide cinco metros, tiene una larga cola y una cresta azul sobre la espalda.",
        "habitat": "Vive en bosques húmedos y claros cercanos a ríos de aguas lentas.",
        "alimentacion": "Es carnívoro y caza reptiles pequeños con sus dientes afilados y curvos.",
        "comportamiento": "Caza en solitario al amanecer y descansa en zonas altas durante el calor.",
        "caracteristica_distintiva": "Una cresta azul en la cabeza que cambia de brillo con su ánimo."}
LOG = []


class FakeHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/api/version":
            self._send({"version": "0.0-test"})
        elif self.path == "/api/tags":
            self._send({"models": [{"name": "mistral:7b", "size": 4e9, "digest": "a" * 64}]})
        elif self.path == "/health":
            self._send({"status": "ok", "model": "fake-sdxl"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        LOG.append((self.path, body))
        if self.path == "/api/generate":
            if body.get("format") == "json":
                self._send({"response": json.dumps(GOOD), "eval_count": 100, "eval_duration": int(2e10)})
            else:
                self._send({"response": '"Prompt: Zorvasaurus, a dinosaur, full body side view, blue crest, '
                                        'highly detailed paleoart, natural lighting"'})
        elif self.path == "/api/chat":
            self._send({"message": {"role": "assistant", "content": "¡Rugido amistoso! Soy un dinosaurio."}})
        elif self.path == "/generate":
            self._send({"image_base64": PNG_1PX, "mime": "image/png", "seconds": 1.5})


def make_assets(d, rnn_type, L=2, H=8, V=29):
    rng = np.random.default_rng(0)
    g = {"RNN": 1, "LSTM": 4, "GRU": 3}[rnn_type]
    arr = {"emb": rng.normal(size=(V, 6)), "fc_w": rng.normal(size=(V, H)), "fc_b": rng.normal(size=V)}
    for l in range(L):
        i = 6 if l == 0 else H
        arr[f"w_ih_{l}"] = rng.normal(size=(g * H, i)) * .5
        arr[f"w_hh_{l}"] = rng.normal(size=(g * H, H)) * .5
        arr[f"b_ih_{l}"] = rng.normal(size=g * H) * .1
        arr[f"b_hh_{l}"] = rng.normal(size=g * H) * .1
    np.savez(d / "char_model.npz", **arr)
    (d / "char_model_meta.json").write_text(json.dumps(
        {"rnn_type": rnn_type, "hidden_size": H, "num_layers": L, "vocab_size": V, "emb_dim": 6, "pad_id": 0}))
    itos = ["<PAD>", "<SOS>", "<EOS>"] + [chr(97 + i) for i in range(26)]
    (d / "vocab.json").write_text(json.dumps({"itos": itos, "pad_id": 0, "sos_id": 1, "eos_id": 2, "max_len": 24}))
    (d / "training_names.json").write_text(json.dumps(["aardonyx", "tyrannosaurus"]))
    (d / "model_info.json").write_text(json.dumps({"config": {"name": "T_" + rnn_type, "arch": rnn_type,
                                                              "num_layers": L, "hidden_size": H}, "parametros": 123,
                                                  "mejor_val": 1.9, "mejor_epoca": 10, "vocab_size": V, "T": 24}))
    (d / "dinosaurio_inicial.json").write_text(json.dumps({"nombre": "Calalosaurus", "campos": GOOD,
                                                           "descripcion": "x" * 50, "imagen_url": "/assets/c.png"}))
    (d / "c.png").write_bytes(base64.b64decode(PNG_1PX))


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), FakeHandler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{cls.srv.server_port}"
        os.environ.update(OLLAMA_URL=url, IMAGE_API_URL=url, OLLAMA_MODEL="mistral:7b", IMAGE_SIZE="512")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.assets = Path(cls.tmp.name)
        make_assets(cls.assets, "LSTM")
        import core
        cls.core = core
        core.ASSETS = cls.assets
        core.FRONT = Path(__file__).resolve().parent.parent / "frontend"

    def call(self, m, p, body=None):
        r = self.core.route(m, p, json.dumps(body).encode() if body is not None else b"")
        return r["status"], (json.loads(r["body"]) if r["headers"]["Content-Type"].startswith("application/json")
                             else r["body"])

    def test_nombre_todas_las_arquitecturas(self):
        import name_numpy as nn
        for t in ("RNN", "LSTM", "GRU"):
            with tempfile.TemporaryDirectory() as d:
                make_assets(Path(d), t)
                model, vocab, known = nn.load_model(d)
                rng = np.random.default_rng(1)
                names = {nn.sample_name(model, vocab, rng, 1.0, None, 0.9) for _ in range(30)}
                self.assertTrue(all(n.isalpha() and 3 <= len(n) <= 24 for n in names), (t, names))
                self.assertEqual(model.logits_sequence([1, 5, 6, 7]).shape, (4, 29))

    def test_top_k_y_top_p(self):
        import name_numpy as nn
        lg = np.log(np.array([.5, .3, .1, .06, .04]))
        self.assertEqual(np.isfinite(nn._filter_logits(lg, top_k=2)).sum(), 2)
        self.assertEqual(np.isfinite(nn._filter_logits(lg, top_p=.85)).sum(), 3)
        self.assertEqual(np.isfinite(nn._filter_logits(lg, top_p=.55)).sum(), 2)

    def test_endpoint_nombre_es_nuevo(self):
        s, d = self.call("POST", "/api/nombre", {"excluir": ["x"]})
        self.assertEqual(s, 200)
        self.assertTrue(d["nombre"][0].isupper() and d["nombre"].lower() not in ("aardonyx", "tyrannosaurus"))
        self.assertEqual(d["modelo_caracteres"]["arquitectura"], "LSTM")

    def test_identidad(self):
        s, d = self.call("POST", "/api/identidad", {"nombre": "Zorvasaurus"})
        self.assertEqual(s, 200)
        self.assertEqual(set(d["campos"]), set(GOOD))
        self.assertIn("Apariencia:", d["descripcion"])

    def test_imagen_prompt_y_png(self):
        s, d = self.call("POST", "/api/imagen", {"nombre": "Zorvasaurus", "campos": GOOD})
        self.assertEqual(s, 200)
        self.assertTrue(d["prompt"].startswith("Zorvasaurus"), d["prompt"])
        self.assertNotIn('"', d["prompt"])
        self.assertEqual(d["image_base64"], PNG_1PX)
        img_call = [b for p, b in LOG if p == "/generate"][-1]
        self.assertEqual(img_call["size"], 512)

    def test_chat_imagen_solo_cuando_corresponde(self):
        base = {"nombre": "Zorvasaurus", "descripcion": "Apariencia: " + "x" * 60}
        s, d = self.call("POST", "/api/chat", {**base, "intro": True})
        self.assertTrue(d["show_image"])
        s, d = self.call("POST", "/api/chat", {**base, "messages": [{"role": "user", "content": "¿Qué comes?"}]})
        self.assertFalse(d["show_image"])
        for frase in ("Descríbete por favor", "¿Cómo eres?", "muéstrame una foto", "Preséntate", "¿Quién eres?"):
            s, d = self.call("POST", "/api/chat", {**base, "messages": [{"role": "user", "content": frase}]})
            self.assertTrue(d["show_image"], frase)
        sistema = [b for p, b in LOG if p == "/api/chat"][-1]["messages"][0]
        self.assertEqual(sistema["role"], "system")
        self.assertIn(base["descripcion"], sistema["content"])      # la identidad viaja como contexto en cada chat

    def test_errores(self):
        self.assertEqual(self.call("POST", "/api/chat", {"nombre": "Zorvasaurus"})[0], 400)
        self.assertEqual(self.call("POST", "/api/identidad", {"nombre": "1"})[0], 400)
        self.assertEqual(self.call("POST", "/api/imagen", {"nombre": "Zorvasaurus"})[0], 400)
        self.assertEqual(self.call("GET", "/api/no-existe")[0], 404)
        self.assertEqual(self.call("GET", "/assets/../char_model.npz")[0], 404)
        self.assertEqual(self.call("GET", "/assets/vocab.json")[0], 404)     # solo se sirven imagenes
        os.environ["IMAGE_API_URL"] = "http://127.0.0.1:9"
        try:
            self.assertEqual(self.call("POST", "/api/imagen", {"nombre": "Zorvasaurus", "campos": GOOD})[0], 502)
        finally:
            os.environ["IMAGE_API_URL"] = os.environ["OLLAMA_URL"]

    def test_estado_inicial_y_estaticos(self):
        s, d = self.call("GET", "/api/estado")
        self.assertTrue(d["ollama"]["ok"] and d["ollama"]["modelo_instalado"] and d["imagen"]["ok"])
        s, d = self.call("GET", "/api/dinosaurio-inicial")
        self.assertEqual(d["nombre"], "Calalosaurus")
        s, b = self.call("GET", "/assets/c.png")
        self.assertEqual((s, b[:4]), (200, b"\x89PNG"))
        s, b = self.call("GET", "/")
        self.assertEqual(s, 200)
        self.assertIn(b"Nuevo Dinosaurio", b)

    def test_lambda_adaptador(self):
        import lambda_function as lf
        r = lf.handler({"requestContext": {"http": {"method": "GET"}}, "rawPath": "/assets/c.png"}, None)
        self.assertTrue(r["isBase64Encoded"])
        r = lf.handler({"requestContext": {"http": {"method": "POST"}}, "rawPath": "/api/nombre", "body": "{}"}, None)
        self.assertEqual(r["statusCode"], 200)
        self.assertIn("nombre", json.loads(r["body"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
