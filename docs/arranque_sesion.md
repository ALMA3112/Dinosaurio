# Arranque por sesion (que es automatico y que no)

## Una sola vez (configuracion)
1. **Dominios fijos de ngrok** (uno por cuenta; el plan gratuito incluye un "dev domain" asignado, en el panel de ngrok > Domains):
   - Cuenta #1 (Ollama): `bash ollama_setup/03_exponer_ngrok.sh permanente TU-DOMINIO-1.ngrok-free.dev`
   - Cuenta #2 (imagenes): secreto `NGROK_DOMAIN_IMAGE` en Colab con TU-DOMINIO-2.ngrok-free.dev
   - En el `.env` (o en las variables de la Lambda) quedan `OLLAMA_URL=https://TU-DOMINIO-1...` e `IMAGE_API_URL=https://TU-DOMINIO-2...` para siempre.
2. **Lifecycle on-start** (SageMaker > Lifecycle configurations > `dinosaurio-on-start` > Edit): pegar `ollama_setup/lifecycle_on_start.sh`.
   A partir de ahi, cada *Start* del notebook levanta Docker, Ollama y precarga el modelo en segundo plano.

## En cada sesion
| Paso | Donde | Automatico |
|---|---|---|
| Start Lab | AWS Academy | No (manual) |
| Start del notebook de SageMaker | consola de SageMaker | No (manual, 3-5 min) |
| Docker + contenedor de Ollama | SageMaker | Si (lifecycle on-start) |
| Precarga de mistral en memoria | SageMaker | Si (segundo plano, 1-4 min) |
| Tunel de ngrok #1 | SageMaker | Si (modo permanente, URL fija) |
| Notebook de Colab (API de imagenes) | Google Colab | No (Ejecutar todo; URL fija con dominio) |
| App (local: `python app/backend/dev_server.py`) | tu equipo | No (un comando) |

Comprobar antes de usar la app: `python app/diagnostico.py` (todo en OK).

## Antes de la sustentacion
Encender SageMaker y Colab ~15 minutos antes, ejecutar `python app/diagnostico.py` y probar *Nuevo Dinosaurio* una vez.
Detener el notebook de SageMaker (*Stop*) al terminar: una m5.xlarge encendida consume credito del Learner Lab.
