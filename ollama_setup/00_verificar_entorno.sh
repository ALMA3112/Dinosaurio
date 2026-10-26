#!/usr/bin/env bash
# Evidencia del entorno del notebook de SageMaker. Ejecutar en la terminal del notebook:
#   bash /home/ec2-user/SageMaker/Dinosaurio/ollama_setup/00_verificar_entorno.sh
# Guarda la salida en docs/evidencias/entorno_sagemaker.txt
set -u
OUT=/home/ec2-user/SageMaker/Dinosaurio/docs/evidencias/entorno_sagemaker.txt
mkdir -p "$(dirname "$OUT")"
{
  echo "== Fecha =="; date -u
  echo "== SO =="; head -3 /etc/os-release
  echo "== CPU (nproc) =="; nproc
  echo "== RAM =="; free -h | head -2
  echo "== Disco persistente =="; df -h /home/ec2-user/SageMaker
  echo "== Docker =="; docker --version 2>&1
  echo "Docker Root Dir (debe ser /home/ec2-user/SageMaker/docker):"
  sudo docker info 2>/dev/null | grep -E "Docker Root Dir|Storage Driver" || echo "docker daemon no disponible"
  echo "== Lifecycle on-start =="; tail -5 /home/ec2-user/SageMaker/onstart.log 2>/dev/null || echo "sin onstart.log (lifecycle no adjunto o no ejecutado)"
  echo "== Marcador de persistencia =="; cat /home/ec2-user/SageMaker/persistencia_ok.txt 2>/dev/null || echo "no existe"
  echo "== Python =="; python3 --version
  echo "== Internet saliente =="; curl -sS -m 8 -o /dev/null -w "ollama.com HTTP %{http_code}\n" https://ollama.com || echo "sin salida a internet"
} | tee "$OUT"
