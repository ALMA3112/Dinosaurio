# Dinosaurio: generador de especies ficticias

Laboratorio II, Procesamiento de Lenguaje Natural (2026 S02), Universidad Sergio Arboleda.

- **Sitio web:** https://pz2a2qva266mwer62txyef2hde0joebi.lambda-url.us-east-1.on.aws
- **Repositorio:** https://github.com/ALMA3112/Dinosaurio

Flujo: **Modelo de caracteres → Nombre → Ollama → Identidad → Imagen → Chat**

> El sitio depende de dos servicios que se encienden aparte (Ollama en SageMaker e imágenes en Colab); ver
> [`docs/arranque_sesion.md`](docs/arranque_sesion.md). Si están apagados, la página carga pero los indicadores salen en rojo.

## Arquitectura

```
Navegador → Function URL (AWS Lambda: página + API) ─┬→ Ollama en SageMaker (Docker, ngrok #1)  → identidad, chat
                                                      └→ API de imágenes en Colab (SDXL, ngrok #2) → imagen
                         └ modelo de caracteres (NumPy, dentro de la Lambda) → nombre
```

| Componente | Carpeta | Tecnología |
|---|---|---|
| Generador de nombres | `name_generator/` | Modelo de caracteres LSTM de 2 capas × 256 (PyTorch), exportado a NumPy para la app |
| Identidad y chat | `ollama_setup/` | Ollama en Docker sobre SageMaker `ml.m5.xlarge`: `mistral:7b` (identidad) y `qwen2.5:3b` (chat) |
| Imagen | `image_gen/` | Stable Diffusion XL base 1.0 (diffusers) en Colab, API Flask expuesta con ngrok |
| Aplicación web | `app/` | Frontend en HTML/JS y backend en Python; despliegue en AWS Lambda con Function URL |
| Documentación y evidencias | `docs/` | Ver abajo |

## Evidencias del generador de nombres (sección 7 de la guía)
- Arquitectura, configuraciones y entrenamiento: [`docs/configuraciones_entrenamiento.csv`](docs/configuraciones_entrenamiento.csv), [`docs/modelo_seleccionado.json`](docs/modelo_seleccionado.json)
- Curvas de pérdida (entrenamiento y validación): [`docs/evidencias/curvas_perdida.png`](docs/evidencias/curvas_perdida.png)
- Configuraciones de muestreo: [`docs/comparacion_muestreo.csv`](docs/comparacion_muestreo.csv)
- Diez nombres generados y análisis: [`docs/nombres_generados.csv`](docs/nombres_generados.csv), [`docs/analisis_nombres.md`](docs/analisis_nombres.md)

## Otras evidencias
- SageMaker y persistencia: [`docs/fase2_sagemaker.md`](docs/fase2_sagemaker.md), `docs/evidencias/entorno_sagemaker.txt`
- Ollama (comparación de modelos y versión): [`docs/comparacion_modelos_ollama.md`](docs/comparacion_modelos_ollama.md), [`docs/modelo_ollama.json`](docs/modelo_ollama.json)
- Imagen: [`docs/fase4_imagen.md`](docs/fase4_imagen.md), `image_gen/imagen_dinosaurio.json`
- Aplicación y contrato de cada componente: [`docs/fase5_app.md`](docs/fase5_app.md)
- Despliegue en AWS: [`docs/fase6_despliegue.md`](docs/fase6_despliegue.md)

## Cómo identificar y ejecutar cada componente

| Componente | Cómo ejecutarlo |
|---|---|
| Generador de nombres | Abrir `name_generator/01_generador_nombres.ipynb` en Google Colab y ejecutar todo. Descarga `dinos.csv` y deja el modelo y las evidencias en `name_generator/artifacts/` y `docs/` |
| Ollama en SageMaker | En un notebook `ml.m5.xlarge` con el lifecycle `ollama_setup/lifecycle_on_start.sh`: `bash ollama_setup/01_instalar_ollama.sh`, luego el notebook `ollama_setup/02_ollama_identidad.ipynb`. Túnel: `bash ollama_setup/03_exponer_ngrok.sh` |
| Imagen | Abrir `image_gen/01_imagen_colab.ipynb` en Colab con GPU T4 y ejecutar hasta la celda de la API |
| Aplicación en local | Copiar `.env.example` a `.env`, `pip install numpy`, `python app/diagnostico.py` y `python app/backend/dev_server.py` (http://localhost:8000) |
| Despliegue en AWS | `python app/build_lambda.py` y seguir `docs/fase6_despliegue.md` |

Las instrucciones de arranque de cada sesión están en [`docs/arranque_sesion.md`](docs/arranque_sesion.md).

## Variables de entorno
Se copian de `.env.example` a `.env` (local) o se configuran en la Lambda: `OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_CHAT_MODEL`,
`IMAGE_API_URL`, `IMAGE_SIZE`, `IMAGE_STEPS`. Los authtokens de ngrok no se guardan en el repositorio: se escriben en el momento
(script de SageMaker) o en los Secretos de Colab.

## Seguridad
El repositorio no contiene credenciales, claves de acceso ni tokens. `.env` está en `.gitignore`. Revisión automática:
`python app/verificar_entrega.py`.

## Limitaciones conocidas
- Ollama corre en CPU: tras un *Start* del notebook hay que esperar a que los modelos carguen (unos minutos) y cada respuesta tarda segundos.
- Las URL públicas dependen de ngrok y Colab; el sitio necesita ambos servicios encendidos.
- Un dinosaurio nuevo tarda entre 1 y 3 minutos (identidad con Mistral e imagen con SDXL).
