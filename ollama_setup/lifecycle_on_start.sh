#!/bin/bash
# Lifecycle script "on-start" del notebook de SageMaker (corre como root cada vez que el notebook inicia).
# Objetivo: que Docker guarde imagenes y contenedores en el disco persistente
#           /home/ec2-user/SageMaker, para que no se pierdan al detener/iniciar el notebook.
# Limite de SageMaker: un on-start debe terminar en menos de 5 minutos -> aqui NO se descargan imagenes ni modelos.
set -e

PERSIST=/home/ec2-user/SageMaker
exec > >(tee -a "$PERSIST/onstart.log") 2>&1
echo "=== on-start $(date -u) ==="

mkdir -p "$PERSIST/docker" "$PERSIST/ollama"

# data-root de Docker dentro del disco persistente (se conserva cualquier otra opcion de daemon.json)
mkdir -p /etc/docker
python3 - << 'PY'
import json, os
p = "/etc/docker/daemon.json"
cfg = json.load(open(p)) if os.path.exists(p) and os.path.getsize(p) > 0 else {}
cfg["data-root"] = "/home/ec2-user/SageMaker/docker"
json.dump(cfg, open(p, "w"), indent=2)
PY

# el usuario del notebook puede usar docker sin sudo (efectivo en terminales nuevas)
usermod -aG docker ec2-user || true

# reiniciar Docker para aplicar el data-root
systemctl restart docker 2>/dev/null || service docker restart
sleep 3

# si el contenedor de Ollama ya existe (Fase 3), volver a levantarlo
docker start ollama 2>/dev/null || echo "contenedor ollama aun no existe (se crea en la Fase 3)"

echo "Docker Root Dir: $(docker info 2>/dev/null | grep 'Docker Root Dir')"
echo "=== on-start terminado ==="
