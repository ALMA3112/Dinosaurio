# Fase 6: Despliegue en AWS (Lambda + Function URL)

La aplicacion completa (pagina web + API) corre en **una funcion AWS Lambda** y se publica con una **Function URL** https.
Un solo origen: la pagina y la API comparten URL, sin S3 publico ni CORS.

```
Navegador -> Function URL (Lambda: frontend + /api/...) -> Ollama (SageMaker, ngrok #1)
                                                        -> API de imagenes (Colab, ngrok #2)
```
- El modelo de caracteres (NumPy) viaja dentro del zip: el nombre se genera en la propia Lambda, sin reentrenar.
- Las URLs de Ollama e imagenes se configuran como **variables de entorno** de la Lambda (nunca en el codigo).
- El generador de imagenes permanece en Colab (permitido por la guia).

## 1. Empaquetar (en tu equipo, con internet)
```bash
echo "build/" >> .gitignore          # una sola vez: el zip no se sube a GitHub
python app/build_lambda.py
```
Crea `build/dinosaurio_lambda.zip` (~25-40 MB; incluye NumPy para Linux x86_64 / Python 3.12).

## 2. Crear la funcion (consola de AWS > Lambda, region del Learner Lab)
1. *Create function* > *Author from scratch*: nombre `dinosaurio-app`, runtime **Python 3.12**, arquitectura **x86_64**.
2. *Change default execution role* > *Use an existing role* > **LabRole**. Crear.
3. Pestana *Code* > *Upload from* > *.zip file* > `build/dinosaurio_lambda.zip` > Save.
   (Si el zip pasa de 50 MB: subirlo a S3 y usar *Amazon S3 location*.)
4. *Runtime settings* > Edit > Handler: **`lambda_function.handler`**.
5. *Configuration* > *General configuration* > Edit: Memory **512 MB**, Timeout **15 min 0 s**.
6. *Configuration* > *Environment variables* > Edit:

| Clave | Valor |
|---|---|
| `OLLAMA_URL` | `https://TU-DOMINIO-1.ngrok-free.dev` (sin `/` final) |
| `OLLAMA_MODEL` | `mistral:7b` |
| `IMAGE_API_URL` | `https://TU-DOMINIO-2.ngrok-free.dev` |
| `IMAGE_SIZE` | `768` |
| `IMAGE_STEPS` | `22` |

## 3. Publicar la URL
*Configuration* > *Function URL* > *Create function URL*: Auth type **NONE** > Save. Copiar la URL
(`https://xxxx.lambda-url.<region>.on.aws/`). Esa es el **enlace del sitio web** de la entrega.

## 4. Probar
Abrir la URL: debe cargar el dinosaurio guardado con los dos indicadores en verde (Ollama e Imagenes encendidos).
Repetir la lista de verificacion de `docs/fase5_app.md` sobre el sitio desplegado (chat, imagen al describirse, Nuevo Dinosaurio).

## 5. Si algo falla
| Sintoma | Causa probable | Que hacer |
|---|---|---|
| `403 Forbidden` al abrir la URL | Falta el permiso publico de la Function URL | *Configuration* > *Permissions* > *Resource-based policy*: debe existir un permiso `lambda:InvokeFunctionUrl` con principal `*` y `FunctionUrlAuthType = NONE` (la consola lo crea al elegir Auth NONE; si el Learner Lab lo bloquea, captura el error y avisame) |
| Pagina carga pero indicadores en rojo | URL de ngrok mal escrita o servicios apagados | Revisar variables de entorno y encender SageMaker/Colab; `python app/diagnostico.py` en local |
| `Internal Server Error` | Falta un asset o error de codigo | *Monitor* > *View CloudWatch logs*; revisar que `app/assets` estaba completo al empaquetar |
| `Task timed out` | Ollama o la imagen tardaron mas de 15 min | Ver `docs/arranque_sesion.md`; precalentar el modelo |
| `Unable to import module ... numpy` | NumPy de otra plataforma | Volver a ejecutar `python app/build_lambda.py` (sin `--sin-numpy`) y subir el zip nuevo |

## 6. Actualizar despues de cambios
Volver a ejecutar `python app/build_lambda.py` y subir el zip nuevo (*Upload from*). Si solo cambian las URLs de ngrok,
basta editar las variables de entorno (con dominios fijos de ngrok no cambian).

## Nota de seguridad
La Function URL es publica (cualquiera con el enlace puede usar el chat, que consume tu Ollama). Es aceptable para el laboratorio;
no compartas el enlace fuera de la entrega y detén SageMaker/Colab al terminar.
