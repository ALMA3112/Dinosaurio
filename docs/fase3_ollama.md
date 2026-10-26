# Fase 3: Ollama en SageMaker e identidad del dinosaurio

Ollama corre en Docker dentro del notebook de SageMaker (ml.m5.xlarge, CPU), sin proveedor externo.
Todo lo pesado vive en el disco persistente: imagenes de Docker en `/home/ec2-user/SageMaker/docker`
(data-root, Fase 2) y modelos en `/home/ec2-user/SageMaker/ollama`.

## Componentes
| Archivo | Que hace |
|---|---|
| `ollama_setup/01_instalar_ollama.sh` | Verifica data-root, levanta el contenedor `ollama` y descarga 3 modelos candidatos: `llama3.1:8b`, `qwen2.5:7b`, `mistral:7b` |
| `ollama_setup/02_ollama_identidad.ipynb` | Prueba los modelos, compara, registra nombre/version del elegido y guarda la identidad |
| `ollama_setup/ollama_client.py` | Cliente de Ollama y generador de identidad (lo reutiliza la app en las Fases 5-6) |
| `ollama_setup/03_exponer_ngrok.sh` | Tunel ngrok (cuenta #1) hacia el puerto 11434 |
| `ollama_setup/identidad_dinosaurio.json` | Resultado: identidad del dinosaurio (entrada de las fases 4 y 5) |
| `docs/modelo_ollama.json` | Nombre, digest, tamano y cuantizacion del modelo elegido, version de Ollama |
| `docs/comparacion_modelos_ollama.md` | Comparacion de los 3 modelos y justificacion |

## Contrato de comunicacion
| Llamada | Recibe | Devuelve |
|---|---|---|
| `POST {OLLAMA_URL}/api/generate` | modelo, prompt con el nombre del dinosaurio, `format: json` | JSON con apariencia, habitat, alimentacion, comportamiento, caracteristica_distintiva |
| `POST {OLLAMA_URL}/api/chat` | modelo, mensajes y la identidad como mensaje `system` | respuesta del dinosaurio |
| `GET {OLLAMA_URL}/api/version`, `/api/tags` | nada | version de Ollama / modelos instalados |

`OLLAMA_URL` es `http://localhost:11434` dentro de SageMaker y la URL de ngrok desde fuera (se lee del `.env`, nunca va en el codigo).

## Evidencias
- [ ] `docs/evidencias/ollama_instalacion.txt` (la genera el script 01)
- [ ] `docs/evidencias/ollama_comparacion.json` (la genera el notebook)
- [ ] `docs/comparacion_modelos_ollama.md` con la justificacion completada
