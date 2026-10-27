# Fase 5: Aplicacion web e integracion

Flujo: **Modelo de caracteres -> Nombre -> Ollama -> Identidad -> Imagen -> Chat**

## Arquitectura
```
Navegador (app/frontend/index.html)
   |  mismo origen: /api/...
   v
Backend (app/backend/core.py)  <- dev_server.py (local)  |  lambda_function.py (AWS, Fase 6)
   |-- Modelo de caracteres (NumPy, pesos en app/assets)         -> nombre
   |-- Ollama en SageMaker  (OLLAMA_URL, tunel ngrok #1)         -> identidad, prompt de imagen, chat
   '-- API de imagenes en Colab (IMAGE_API_URL, tunel ngrok #2)  -> imagen PNG (SDXL)
```
- El modelo de caracteres NO se reentrena: la app carga los pesos entrenados (exportados a NumPy, verificados contra PyTorch)
  y "Nuevo Dinosaurio" solo vuelve a muestrear.
- La imagen se genera **una sola vez por dinosaurio**; el navegador la conserva y la reutiliza en la tarjeta y en el chat.
- El primer dinosaurio que se muestra es el guardado de las fases 1-4 (nombre, identidad e imagen reales); cada clic en
  *Nuevo Dinosaurio* repite todo el recorrido en vivo.

## Contrato de la API del backend
| Endpoint | Recibe | Devuelve |
|---|---|---|
| `GET /api/estado` | nada | `{modelo_ollama, ollama:{ok,version,modelo_instalado}, imagen:{ok,modelo}}` |
| `GET /api/modelo` | nada | resumen del modelo de caracteres (arquitectura, capas, estado oculto, parametros, perdida de validacion, vocabulario, T) |
| `GET /api/dinosaurio-inicial` | nada | `{nombre, campos, descripcion, imagen_url, ...}` del dinosaurio guardado |
| `POST /api/nombre` | `{excluir?: [nombres], temperature?, top_k?, top_p?}` (por defecto T=1.0, top-p=0.9) | `{nombre, muestreo, modelo_caracteres}` (nombre que no esta en el conjunto de entrenamiento) |
| `POST /api/identidad` | `{nombre}` | `{nombre, campos:{apariencia,habitat,alimentacion,comportamiento,caracteristica_distintiva}, descripcion, modelo_ollama}` |
| `POST /api/imagen` | `{nombre, campos}` | `{image_base64, mime, prompt, seed, size}`; internamente Ollama redacta un prompt corto en ingles y se llama a la API de imagenes |
| `POST /api/chat` | `{nombre, descripcion, messages:[{role,content}], intro?}` | `{reply, show_image}` |

Errores: `400` datos invalidos, `502` Ollama o la API de imagenes no responden, `500` otro error. Cuerpo: `{"error": "..."}`.

### Chat
- La identidad (`descripcion`) viaja como mensaje `system` en **cada** llamada a Ollama, con la regla de no contradecirla.
- Se envian como maximo los ultimos 8 mensajes (limite de contexto de 2048 tokens).
- `show_image` es `true` cuando el dinosaurio se presenta (`intro`) o el usuario pide que se describa o se presente
  (descripcion, apariencia, "como eres", "quien eres", foto, imagen, preséntate...). Es una regla determinista, no depende del LLM.
  El frontend entonces muestra la imagen ya guardada dentro del mensaje.

## Componentes externos (contrato)
| Componente | Variable | Que recibe / devuelve |
|---|---|---|
| Ollama | `OLLAMA_URL`, `OLLAMA_MODEL` | `/api/generate`, `/api/chat`, `/api/version`, `/api/tags` (ver `docs/fase3_ollama.md`) |
| API de imagenes | `IMAGE_API_URL`, `IMAGE_SIZE` | `GET /health`, `POST /generate` (ver `docs/fase4_imagen.md`) |

Las URLs de ngrok cambian en cada sesion: se actualizan en `.env` (local) o en las variables de entorno de la Lambda (Fase 6).
Nunca se escriben en el codigo.

## Como ejecutar en local
1. `pip install numpy`
2. Exportar el modelo a NumPy (una vez, necesita PyTorch; en Colab):
   ```
   !git clone https://github.com/ALMA3112/Dinosaurio.git
   %cd Dinosaurio
   !python name_generator/export_numpy.py
   from google.colab import files; files.download('/content/export_assets.zip')
   ```
   Debe terminar con `OK: la inferencia en NumPy coincide con PyTorch.` Descomprimir el zip en la raiz del repo.
3. `python app/prepare_assets.py` (copia vocabulario, info del modelo, identidad e imagen a `app/assets/`)
4. `python app/tests/test_backend.py` (pruebas del backend con servicios simulados)
5. Encender SageMaker + `bash ollama_setup/03_exponer_ngrok.sh` (URL de Ollama) y el notebook de Colab (URL de imagenes);
   copiar `.env.example` a `.env` y poner las dos URLs.
6. `python app/backend/dev_server.py` y abrir http://localhost:8000

## Tiempos esperados (CPU para Ollama, T4 para imagen)
Nombre: instantaneo. Identidad: 1-3 min. Prompt de imagen: ~20 s. Imagen SDXL: ~40 s. Presentacion: ~30 s. Cada mensaje de chat: ~15-40 s.

## Verificacion (seccion 9 de la guia)
- [ ] Los nombres nuevos no estan en `dinos.csv` (el backend los filtra contra `training_names.json`)
- [ ] La identidad es coherente (revisar la descripcion en pantalla)
- [ ] La imagen corresponde a los rasgos
- [ ] El chat conserva la identidad (preguntar por su dieta, su hábitat...)
- [ ] La imagen aparece al presentarse o al pedir "descríbete"
- [ ] *Nuevo Dinosaurio* no reentrena (solo muestrea y repite identidad e imagen)
