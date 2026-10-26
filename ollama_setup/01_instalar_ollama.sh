#!/usr/bin/env bash
# Instala Ollama con Docker en el notebook de SageMaker y descarga 3 modelos candidatos (4-8 GB).
# Ejecutar en la terminal de JupyterLab:
#   cd /home/ec2-user/SageMaker/Dinosaurio && bash ollama_setup/01_instalar_ollama.sh
# Es seguro repetirlo: si algo se corta, vuelva a ejecutarlo y continua donde quedo.
set -euo pipefail

MODELS=("llama3.1:8b" "qwen2.5:7b" "mistral:7b")
PERSIST=/home/ec2-user/SageMaker
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$REPO/docs/evidencias/ollama_instalacion.txt"
mkdir -p "$PERSIST/ollama" "$(dirname "$LOG")"

echo ">> 1/4 Comprobando que Docker guarda sus datos en el disco persistente..."
ROOT="$(sudo docker info --format '{{.DockerRootDir}}')"
echo "   Docker Root Dir: $ROOT"
if [[ "$ROOT" != "$PERSIST"* ]]; then
  echo "ERROR: Docker no usa el disco persistente (data-root). Revise la Fase 2 (lifecycle on-start)"
  echo "       o ejecute: sudo bash $REPO/ollama_setup/lifecycle_on_start.sh"
  exit 1
fi
df -h "$PERSIST" | tail -1

echo ">> 2/4 Levantando el contenedor de Ollama (CPU)..."
if sudo docker ps -a --format '{{.Names}}' | grep -qx ollama; then
  sudo docker start ollama >/dev/null || true
  echo "   El contenedor ya existia; iniciado."
else
  sudo docker run -d --name ollama --restart unless-stopped \
    -p 11434:11434 -v "$PERSIST/ollama:/root/.ollama" ollama/ollama:latest >/dev/null
  echo "   Contenedor creado."
fi

echo -n "   Esperando a que la API responda"
for i in $(seq 1 60); do
  if curl -fs http://localhost:11434/api/version >/dev/null; then echo " OK"; break; fi
  echo -n "."; sleep 2
  if [ "$i" -eq 60 ]; then echo; echo "ERROR: Ollama no respondio. Revise: sudo docker logs ollama"; exit 1; fi
done

echo ">> 3/4 Descargando modelos (varios GB; puede tardar 10-25 minutos en total)..."
for m in "${MODELS[@]}"; do
  echo "--- $m ---"
  sudo docker exec ollama ollama pull "$m"
done

echo ">> 4/4 Resumen (se guarda en docs/evidencias/ollama_instalacion.txt)"
{
  echo "Fecha (UTC): $(date -u)"
  echo "Version de Ollama: $(curl -s http://localhost:11434/api/version)"
  echo "Imagen: $(sudo docker inspect --format '{{.Config.Image}} {{.Image}}' ollama)"
  echo "Docker Root Dir: $ROOT"
  echo
  sudo docker exec ollama ollama list
} | tee "$LOG"
echo
echo "Listo. Siguiente paso: abrir ollama_setup/02_ollama_identidad.ipynb"
