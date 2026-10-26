#!/usr/bin/env bash
# Expone Ollama (puerto 11434) con un tunel de ngrok. Usar la cuenta de ngrok #1.
#   bash ollama_setup/03_exponer_ngrok.sh          -> crea el tunel y muestra la URL publica
#   bash ollama_setup/03_exponer_ngrok.sh stop     -> cierra el tunel
# El authtoken se pide por pantalla (no se muestra, no se guarda en ningun archivo).
set -euo pipefail

if [ "${1:-}" = "stop" ]; then
  sudo docker rm -f ngrok-ollama >/dev/null 2>&1 && echo "Tunel cerrado." || echo "No habia tunel."
  exit 0
fi

if [ -z "${NGROK_AUTHTOKEN:-}" ]; then
  read -r -s -p "Pegue el authtoken de ngrok (cuenta #1) y pulse Enter: " NGROK_AUTHTOKEN
  echo
fi

curl -fs http://localhost:11434/api/version >/dev/null || { echo "ERROR: Ollama no responde en el puerto 11434."; exit 1; }

sudo docker rm -f ngrok-ollama >/dev/null 2>&1 || true
sudo docker run -d --name ngrok-ollama --network host -e NGROK_AUTHTOKEN="$NGROK_AUTHTOKEN" \
  ngrok/ngrok:latest http 11434 --host-header="localhost:11434" >/dev/null
unset NGROK_AUTHTOKEN

URL=""
for i in $(seq 1 15); do
  sleep 2
  URL="$(curl -s http://127.0.0.1:4040/api/tunnels | python3 -c "import sys,json
try:
    t=json.load(sys.stdin)['tunnels']; print(t[0]['public_url'] if t else '')
except Exception:
    print('')")"
  [ -n "$URL" ] && break
done

if [ -z "$URL" ]; then
  echo "ERROR: no se obtuvo la URL. Ultimas lineas del log de ngrok:"
  sudo docker logs --tail 15 ngrok-ollama
  exit 1
fi

echo "URL publica de Ollama: $URL"
echo -n "Prueba desde fuera: "
curl -s -H "ngrok-skip-browser-warning: true" "$URL/api/version" || true
echo
echo "Use esta URL como OLLAMA_URL en su archivo .env (NO la suba a GitHub)."
echo "Cualquiera con la URL puede usar su Ollama: ciérrela con 'bash ollama_setup/03_exponer_ngrok.sh stop' cuando no la use."
echo "La URL cambia cada vez que se reinicia el tunel."
