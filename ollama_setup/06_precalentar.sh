#!/usr/bin/env bash
# Deja los modelos listos ANTES de usar la app: lee cada archivo de modelo a la cache de RAM (lectura secuencial) y lo carga en
# Ollama con las mismas opciones que la app. Sin argumentos precarga mistral:7b y qwen2.5:3b (si esta instalado).
#   bash ollama_setup/06_precalentar.sh                    # los dos por defecto
#   bash ollama_setup/06_precalentar.sh mistral:7b         # solo uno
set -uo pipefail
DATA="${OLLAMA_DATA:-/home/ec2-user/SageMaker/ollama}"
MODELS=("$@"); [ ${#MODELS[@]} -eq 0 ] && MODELS=(mistral:7b qwen2.5:3b)

echo "== precalentar ${MODELS[*]} ($(date -u +%H:%M:%S) UTC) =="
for i in $(seq 1 90); do                      # espera hasta 3 min a que Ollama arranque (util al llamarlo desde el on-start)
  curl -fs http://localhost:11434/api/version >/dev/null && break
  [ "$i" -eq 90 ] && { echo "Ollama no responde. Ejecute: bash ollama_setup/04_reiniciar_ollama.sh"; exit 1; }
  sleep 2
done

for MODEL in "${MODELS[@]}"; do
  BLOB="$(MODEL="$MODEL" DATA="$DATA" python3 - << 'PY'
import json, os
from pathlib import Path
name, _, tag = os.environ["MODEL"].partition(":")
man = Path(os.environ["DATA"]) / "models/manifests/registry.ollama.ai/library" / name / (tag or "latest")
try:
    for l in json.loads(man.read_text())["layers"]:
        if l["mediaType"].endswith("image.model"):
            print(Path(os.environ["DATA"]) / "models/blobs" / l["digest"].replace(":", "-"))
except FileNotFoundError:
    pass
PY
)"
  if [ -z "$BLOB" ] || [ ! -f "$BLOB" ]; then echo "-- $MODEL: no esta instalado, se omite"; continue; fi
  echo ">> $MODEL: leyendo $(du -h "$BLOB" | cut -f1) a la cache de RAM..."
  S=$(date +%s); cat "$BLOB" > /dev/null; echo "   leido en $(( $(date +%s) - S )) s"
  S=$(date +%s)
  curl -s --max-time 900 http://localhost:11434/api/generate \
    -d "{\"model\":\"$MODEL\",\"keep_alive\":-1,\"options\":{\"num_ctx\":2048}}" >/dev/null
  echo "   cargado en Ollama en $(( $(date +%s) - S )) s"
done
sudo docker exec ollama ollama ps 2>/dev/null || true
echo "Modelos listos: ya puede abrir la app."
