#!/usr/bin/env bash
# Recrea el contenedor de Ollama con ajustes para CPU y precarga el modelo. Los modelos YA descargados no se vuelven
# a bajar (viven en /home/ec2-user/SageMaker/ollama). El tunel de ngrok NO se afecta (usa el puerto 11434 del host).
#   OLLAMA_KEEP_ALIVE=-1        el modelo se queda en memoria (cargarlo desde este disco tarda minutos)
#   OLLAMA_CONTEXT_LENGTH=2048  mismo contexto que usa la app: si cambia entre peticiones, Ollama RECARGA el modelo
#   OLLAMA_MAX_LOADED_MODELS=2  permite modelo de identidad + modelo de chat distintos sin descargarse entre si
#   OLLAMA_NUM_PARALLEL=1       una peticion a la vez (la CPU no da para mas)
# Uso (terminal de SageMaker):   bash ollama_setup/04_reiniciar_ollama.sh            # usa mistral:7b
#                                bash ollama_setup/04_reiniciar_ollama.sh qwen2.5:7b
set -euo pipefail
MODEL="${1:-mistral:7b}"
PERSIST=/home/ec2-user/SageMaker

echo ">> Recreando el contenedor de Ollama..."
sudo docker rm -f ollama >/dev/null 2>&1 || true
sudo docker run -d --name ollama --restart unless-stopped -p 11434:11434 \
  -v "$PERSIST/ollama:/root/.ollama" \
  -e OLLAMA_KEEP_ALIVE=-1 -e OLLAMA_CONTEXT_LENGTH=2048 \
  -e OLLAMA_MAX_LOADED_MODELS=2 -e OLLAMA_NUM_PARALLEL=1 \
  ollama/ollama:latest >/dev/null

echo -n ">> Esperando a la API"
for i in $(seq 1 60); do
  curl -fs http://localhost:11434/api/version >/dev/null && { echo " OK"; break; }
  echo -n "."; sleep 2
  [ "$i" -eq 60 ] && { echo; echo "ERROR: Ollama no arranco. Revise: sudo docker logs --tail 50 ollama"; exit 1; }
done

echo ">> Memoria libre antes de cargar:"; free -h | head -2
echo ">> Cargando $MODEL en memoria (la primera vez puede tardar varios minutos por la velocidad del disco)..."
START=$(date +%s)
curl -s --max-time 900 http://localhost:11434/api/generate \
  -d "{\"model\":\"$MODEL\",\"keep_alive\":-1,\"options\":{\"num_ctx\":2048}}" >/dev/null
echo "Carga terminada en $(( $(date +%s) - START )) segundos."
echo ">> Modelos cargados ahora:"; sudo docker exec ollama ollama ps
echo
echo "Listo: el modelo queda en memoria y las peticiones de la app ya no lo recargan."
echo "Para medir velocidades:  python3 ollama_setup/05_medir_velocidad.py"
