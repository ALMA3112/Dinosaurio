#!/usr/bin/env bash
# Foto del estado de Ollama en SageMaker para diagnosticar lentitud. Pegue TODA la salida si necesita ayuda.
#   bash ollama_setup/07_estado.sh
echo "== 1. Modelos cargados en memoria (si esta vacio, el primer mensaje espera la carga) =="
sudo docker exec ollama ollama ps 2>&1
echo
echo "== 2. ¿Sigue el precalentamiento? =="
pgrep -fa 06_precalentar || echo "no (ya termino, o no corrio)"
echo
echo "== 3. Ultimas lineas de onstart.log =="
tail -8 /home/ec2-user/SageMaker/onstart.log 2>&1
echo
echo "== 4. Carga de CPU y memoria =="
uptime; free -h | head -2
echo
echo "== 5. Procesos que mas CPU usan (¿algo mas ocupa la maquina?) =="
ps -eo pid,pcpu,pmem,etime,comm --sort=-pcpu | head -6
echo
echo "== 6. Ultimas peticiones que recibio Ollama (codigo, duracion, ruta) =="
sudo docker logs --since 30m ollama 2>&1 | grep -E "GIN" | tail -12 || true
echo
echo "== 7. Contenedores =="
sudo docker ps --format '{{.Names}}  {{.Status}}'
echo
echo "== 8. Modelos instalados =="
sudo docker exec ollama ollama list 2>&1
