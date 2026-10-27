"""Servidor local de desarrollo (solo biblioteca estandar + numpy).

Uso:  python app/backend/dev_server.py          ->  http://localhost:8000
Lee las variables del archivo .env de la raiz del repositorio (OLLAMA_URL, OLLAMA_MODEL, IMAGE_API_URL, IMAGE_SIZE).
"""
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env(HERE.parent.parent / ".env")
import core  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def _run(self, method):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        r = core.route(method, self.path, body)
        self.send_response(r["status"])
        for k, v in r["headers"].items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(r["body"])))
        self.end_headers()
        self.wfile.write(r["body"])

    def do_GET(self):
        self._run("GET")

    def do_POST(self):
        self._run("POST")

    def do_OPTIONS(self):
        self._run("OPTIONS")

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    c = core.config()
    print(f"Ollama: {c['ollama_url']} (modelo {c['ollama_model']})")
    print(f"Imágenes: {c['image_url'] or 'NO CONFIGURADA'} (tamaño {c['image_size']})")
    print(f"Abra http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
