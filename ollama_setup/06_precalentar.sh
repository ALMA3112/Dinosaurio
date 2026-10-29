#!/usr/bin/env bash
# Deja el modelo listo ANTES de usar la app: lee el archivo del modelo en la cache de RAM (lectura secuencial, mas rapida
# que cargarlo a saltos desde el disco) y lo carga en Ollama con las mismas opciones que la app. Ejecutar tras cada Start.
#   bash ollama_setup/06_precalentar.sh [modelo]
set -euo pipefail
MODEL="${1:-mistral:7b}"
DATA="${OLLAMA_DATA:-/home/ec2-user/SageMaker/ollama}"
echo "== precalentar $MODEL ($(date -u +%H:%M:%S) UTC) =="
for i in $(seq 1 90); do                      # espera hasta 3 min a que Ollama arranque (util al llamarlo desde el on-start)
  curl -fs http://localhost:11434/api/version >/dev/null && break
  [ "$i" -eq 90 ] && { echo "Ollama no responde. Ejecute: bash ollama_setup/04_reiniciar_ollama.sh"; exit 1; }
  sleep 2
done

BLOB="$(MODEL="$MODEL" DATA="$DATA" python3 - << 'PY'
import json, os
from pathlib import Path
name, _, tag = os.environ["MODEL"].partition(":")
man = Path(os.environ["DATA"]) / "models/manifests/registry.ollama.ai/library" / name / (tag or "latest")
for l in json.loads(man.read_text())["layers"]:
    if l["mediaType"].endswith("image.model"):
        print(Path(os.environ["DATA"]) / "models/blobs" / l["digest"].replace(":", "-"))
PY
)"
[ -f "$BLOB" ] || { echo "No encontre el archivo del modelo $MODEL"; exit 1; }

echo ">> 1/2 Leyendo $(du -h "$BLOB" | cut -f1) del modelo a la cache de RAM..."
S=$(date +%s); cat "$BLOB" > /dev/null; echo "   listo en $(( $(date +%s) - S )) s"

echo ">> 2/2 Cargando $MODEL en Ollama..."
S=$(date +%s)
curl -s --max-time 900 http://localhost:11434/api/generate \
  -d "{\"model\":\"$MODEL\",\"keep_alive\":-1,\"options\":{\"num_ctx\":2048}}" >/dev/null
echo "   listo en $(( $(date +%s) - S )) s"
sudo docker exec ollama ollama ps
echo "Modelo listo: ya puede abrir la app."
