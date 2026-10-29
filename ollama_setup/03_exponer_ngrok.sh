#!/usr/bin/env bash
# Expone Ollama (puerto 11434) con un tunel de ngrok. Usar la cuenta de ngrok #1.
#   bash ollama_setup/03_exponer_ngrok.sh                       -> tunel temporal (hay que repetirlo tras cada Start)
#   bash ollama_setup/03_exponer_ngrok.sh permanente DOMINIO    -> tunel que VUELVE SOLO tras cada Start del notebook,
#                                                                 con URL fija: https://DOMINIO
#   bash ollama_setup/03_exponer_ngrok.sh stop                  -> cierra el tunel
# DOMINIO es el "dev domain" gratuito de su cuenta de ngrok (panel de ngrok > Domains), por ejemplo
#   mocker-ambition-quirk.ngrok-free.dev
# El authtoken se pide por pantalla (no se muestra ni se escribe en ningun archivo del repo). En modo permanente el contenedor
# lo conserva en su configuracion, que vive en el disco persistente de SageMaker (no la comparta ni suba ese disco).
set -euo pipefail

if [ "${1:-}" = "stop" ]; then
  sudo docker rm -f ngrok-ollama >/dev/null 2>&1 && echo "Tunel cerrado." || echo "No habia tunel."
  exit 0
fi

MODO="temporal"; DOMINIO=""
if [ "${1:-}" = "permanente" ]; then
  MODO="permanente"; DOMINIO="${2:-}"
  DOMINIO="${DOMINIO#https://}"; DOMINIO="${DOMINIO%/}"
  [ -n "$DOMINIO" ] || { echo "Falta el dominio. Ej: bash ollama_setup/03_exponer_ngrok.sh permanente mocker-ambition-quirk.ngrok-free.dev"; exit 1; }
fi

if [ -z "${NGROK_AUTHTOKEN:-}" ]; then
  read -r -s -p "Pegue el authtoken de ngrok (cuenta #1) y pulse Enter: " NGROK_AUTHTOKEN
  echo
fi

curl -fs http://localhost:11434/api/version >/dev/null || { echo "ERROR: Ollama no responde en el puerto 11434."; exit 1; }

sudo docker rm -f ngrok-ollama >/dev/null 2>&1 || true
ARGS=(http 11434 --host-header="localhost:11434")
[ -n "$DOMINIO" ] && ARGS+=(--url "https://$DOMINIO")
POLITICA=()
[ "$MODO" = "permanente" ] && POLITICA=(--restart unless-stopped)

sudo docker run -d --name ngrok-ollama --network host "${POLITICA[@]}" -e NGROK_AUTHTOKEN="$NGROK_AUTHTOKEN" \
  ngrok/ngrok:latest "${ARGS[@]}" >/dev/null
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

echo "URL publica de Ollama: $URL   (modo $MODO)"
echo -n "Prueba desde fuera: "
curl -s -H "ngrok-skip-browser-warning: true" "$URL/api/version" || true
echo
echo "Use esta URL como OLLAMA_URL en su .env (NO la suba a GitHub)."
if [ "$MODO" = "permanente" ]; then
  echo "La URL es fija y el tunel se reinicia solo con el notebook: no hay que repetir este paso."
else
  echo "La URL puede cambiar cuando se reinicia el tunel. Para dejarla fija: bash ollama_setup/03_exponer_ngrok.sh permanente TU-DOMINIO"
fi
echo "Cualquiera con la URL puede usar su Ollama: ciérrela con 'bash ollama_setup/03_exponer_ngrok.sh stop' si no la necesita."
