# Dinosaurio: generador de especies ficticias

Laboratorio II, Procesamiento de Lenguaje Natural (2026 S02), Universidad Sergio Arboleda.

Flujo: **Modelo de caracteres -> Nombre -> Ollama -> Identidad -> Imagen -> Chat**

## Estado de las fases

| Fase | Descripcion | Estado |
|---|---|---|
| 0 | Estructura del repositorio | Hecha |
| 1 | Generador de nombres (RNN/LSTM/GRU) | Pendiente |
| 2 | AWS Learner Lab y SageMaker | Pendiente |
| 3 | Ollama en SageMaker e identidad | Pendiente |
| 4 | Generacion de imagen (Colab) | Pendiente |
| 5 | Aplicacion web y chat | Pendiente |
| 6 | Despliegue en AWS | Pendiente |
| 7 | Evidencias y entrega | Pendiente |

## Estructura

| Carpeta | Contenido |
|---|---|
| `name_generator/` | Notebook y codigo del modelo de caracteres, `data/dinos.csv`, `artifacts/` (modelo `.pt`, vocabulario) |
| `ollama_setup/` | Instalacion de Ollama con Docker, lifecycle script `on-start`, comparacion de modelos, identidad |
| `image_gen/` | Notebook de Colab y API de generacion de imagen |
| `app/` | Aplicacion web (frontend, backend/proxy) |
| `docs/` | Arquitectura, curvas de perdida, configuraciones de muestreo, analisis |
| `docs/evidencias/` | Graficas y capturas de pantalla |

## Contrato de componentes (se completa en cada fase)

| Componente | Recibe | Devuelve |
|---|---|---|
| Generador de nombres | Parametros de muestreo (temperatura, top-k, top-p) | Nombre (string) |
| Ollama (SageMaker + ngrok #1) | Nombre del dinosaurio / mensajes del chat con la identidad como contexto | Descripcion (identidad) / respuesta del chat |
| Servicio de imagen (Colab + ngrok #2) | Prompt con nombre y rasgos | Imagen (PNG) |
| Aplicacion web | Accion del usuario (cargar, chatear, Nuevo Dinosaurio) | Pagina con nombre, descripcion, imagen y chat |

## Variables de entorno

Copiar `.env.example` a `.env` y completar. El `.env` esta en `.gitignore`. Ninguna credencial, clave ni token debe subirse al repositorio.

## Como ejecutar

Las instrucciones por componente se agregan al terminar cada fase.
