# Fase 2: AWS Learner Lab, notebook de SageMaker y persistencia

Objetivo: un notebook de SageMaker (**ml.m5.xlarge**, 4 vCPU, 16 GB RAM, sin GPU) que **conserve todo** al detenerlo e
iniciarlo de nuevo, listo para ejecutar Ollama con Docker en la Fase 3.

## Que se conserva y que no

| Ubicacion | Al hacer Stop -> Start |
|---|---|
| `/home/ec2-user/SageMaker/` (repo, modelos de Ollama, datos de Docker, logs) | **Se conserva** (disco EBS persistente) |
| Cualquier otra ruta (`/usr`, `/etc`, `~/.cache`, paquetes `pip` instalados fuera de ahi, `/etc/docker/daemon.json`) | **Se pierde**; por eso existe el script on-start |
| La instancia si se hace **Delete** | **Se pierde TODO, tambien el disco.** Usar siempre *Stop*, nunca *Delete* |

Regla del proyecto: todo lo importante vive dentro de `/home/ec2-user/SageMaker/`.
- Repositorio: `/home/ec2-user/SageMaker/Dinosaurio`
- `data-root` de Docker: `/home/ec2-user/SageMaker/docker` (fuera del repo, para no versionarlo)
- Modelos de Ollama: `/home/ec2-user/SageMaker/ollama` (fuera del repo)

## Pasos

### 1. Iniciar el laboratorio
AWS Academy -> Learner Lab -> *Start Lab*. Esperar el circulo verde y abrir la consola con *AWS*. Anotar la region
(normalmente `us-east-1`); todos los recursos deben estar en la misma.

### 2. Crear el lifecycle script on-start (ANTES del notebook)
SageMaker -> **Lifecycle configurations** -> pestana *Notebook Instance* -> **Create configuration**.
- Nombre: `dinosaurio-on-start`
- Pestana **Start notebook**: pegar el contenido de `ollama_setup/lifecycle_on_start.sh`
- Pestana *Create notebook*: dejar vacia
- Create configuration

El script mueve el `data-root` de Docker al disco persistente y reinicia Docker cada vez que el notebook arranca.
(Limite de SageMaker: el on-start debe terminar en menos de 5 minutos, por eso no descarga nada.)

### 3. Crear el notebook
SageMaker -> **Notebook instances** -> *Create notebook instance* (no Studio).
- Nombre: `dinosaurio-ollama`
- Tipo de instancia: **ml.m5.xlarge**
- Plataforma: Amazon Linux 2023 (o la mas reciente ofrecida)
- Rol IAM: *Use existing role* -> **LabRole** (Learner Lab no permite crear roles)
- **Volume size: 50 GB** (3 modelos de 4-8 GB + imagenes de Docker; el valor por defecto de 5 GB no alcanza)
- Root access: **Enable**
- Acceso a internet directo: **Enable** (para `docker pull`, `ollama pull` y ngrok)
- *Additional configuration* -> **Lifecycle configuration**: `dinosaurio-on-start`

Si el notebook ya estaba creado: *Stop* -> *Edit* -> adjuntar `dinosaurio-on-start` -> guardar -> *Start*.

### 4. Preparar el espacio persistente
Estado **InService** -> *Open JupyterLab* -> **Terminal**:
```bash
cd /home/ec2-user/SageMaker
git clone https://github.com/ALMA3112/Dinosaurio.git
git config --global user.name "su-nombre"
git config --global user.email "su@correo.com"
```
(`git config --global` vive fuera del disco persistente: hay que repetirlo despues de cada reinicio, o hacerlo con
`git config --local` dentro del repo, que si se conserva.) Nunca guardar tokens de GitHub, ngrok o AWS en archivos del repo.

### 5. Verificar entorno y Docker
```bash
bash /home/ec2-user/SageMaker/Dinosaurio/ollama_setup/00_verificar_entorno.sh
```
Debe mostrar `Docker Root Dir: /home/ec2-user/SageMaker/docker`. Si muestra `/var/lib/docker`, el lifecycle no se adjunto
o fallo: revisar `/home/ec2-user/SageMaker/onstart.log`.

### 6. Prueba de persistencia (obligatoria)
```bash
echo "persistencia ok $(date -u)" > /home/ec2-user/SageMaker/persistencia_ok.txt
```
En la consola: **Stop** del notebook (esperar *Stopped*) -> **Start** (esperar *InService*) -> abrir la terminal:
```bash
cat /home/ec2-user/SageMaker/persistencia_ok.txt                      # el archivo sigue ahi
ls /home/ec2-user/SageMaker/Dinosaurio                                # el repo sigue ahi
tail -3 /home/ec2-user/SageMaker/onstart.log                          # el on-start corrio de nuevo
sudo docker info | grep "Docker Root Dir"                             # /home/ec2-user/SageMaker/docker
bash /home/ec2-user/SageMaker/Dinosaurio/ollama_setup/00_verificar_entorno.sh
```

## Si ml.m5.xlarge no aparece o esta bloqueada
Learner Lab restringe tipos de instancia segun la configuracion del curso. Capturar el mensaje de error, probar
`ml.m5.large` solo como alternativa temporal y avisar al profesor (la guia exige m5.xlarge). Si Learner Lab no deja crear
lifecycle configurations, capturar el error y avisar: sin esa funcion, el `data-root` habria que reaplicarlo a mano
(`bash ollama_setup/lifecycle_on_start.sh` con `sudo`) en cada inicio.

## Limitaciones de Learner Lab
- La sesion del laboratorio es limitada; al terminar, los recursos se detienen. El notebook vuelve con *Start*.
- Hay presupuesto de credito: hacer **Stop** cuando no se use (una m5.xlarge encendida consume credito).
- No se pueden crear roles IAM; se usa `LabRole`.
- Las URL de ngrok cambian entre sesiones: se leen de variables de entorno (`.env`), nunca fijas en el codigo.

## Evidencias en `docs/evidencias/`
- [ ] `sagemaker_notebook_config.png`: creacion (ml.m5.xlarge, LabRole, 50 GB, lifecycle adjunto)
- [ ] `sagemaker_lifecycle.png`: la lifecycle configuration `dinosaurio-on-start`
- [ ] `sagemaker_inservice.png`: notebook InService
- [ ] `entorno_sagemaker.txt`: salida del script **despues** de la prueba Stop -> Start
