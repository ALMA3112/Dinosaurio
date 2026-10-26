# Ollama: comparación de modelos e identidad del dinosaurio

Instancia: SageMaker ml.m5.xlarge (CPU, 16 GB RAM). Ollama 0.40.11 en Docker.
Dinosaurio: **Calalosaurus**. Mismo prompt, temperatura 0.7, semilla 42.

## Modelos descargados
| modelo | tamano_GB | digest |
|---|---|---|
| mistral:7b | 4.37 | 6577803aa9a0 |
| qwen2.5:7b | 4.68 | 845dbda0ea48 |
| llama3.1:8b | 4.92 | 46e0c10c039e |

## Resultados
| modelo | json_valido | intentos | campos_ok | palabras | tokens_por_s | tiempo_total_s |
|---|---|---|---|---|---|---|
| mistral:7b | True | 1 | 5 | 250 | 2.9 | 238 |
| qwen2.5:7b | True | 1 | 5 | 206 | 3.2 | 172 |
| llama3.1:8b | True | 1 | 5 | 221 | 2.8 | 208 |

## Modelo elegido
**mistral:7b** (digest `6577803aa9a0`, 7.2B, cuantización Q4_K_M).

### Justificación (completar con sus palabras)
- Coherencia entre los rasgos de las tres descripciones:
- Calidad del español:
- Velocidad en CPU (tokens por segundo):

## Identidad generada
Apariencia: El Calalosaurus posee una apariencia imponente, con un cuerpo alargado y una cola larga y robusta. Su espalda presenta una cresta dorsal prominente, similar a las colas de las mariposas. Sus patas delanteras tienen dedos con garras afiladas y largas, mientras que las patas traseras son más cortas y más fuertes para soportar su peso.
Hábitat: El Calalosaurus se encuentra en los bosques húmedos y densos de la época del Cretácico Superior. Su hábitat está lleno de árboles altos y estrechos que le proporcionan abundante cobertura para esconderse de los depredadores. También vive cerca de corrientes de agua y lagos, donde se alimenta de las especies acuáticas.
Alimentación: Se alimenta principalmente de las especies acuáticas encontradas en sus hábitats, como los peces y las tortugas marinas. También come plantas acuáticas y algunas especies terrestres como los pterosaurios. Su dentadura curva y afilada le permite cortar y tragar a sus presas sin dificultad.
Comportamiento: El Calalosaurus es un depredador solitario y territorial. A diferencia de otros dinosaurios, suelen vivir cerca de las aguas. A menudo se esconden en el sotobosque y atacan a sus presas cuando estas se acercan. También se han observado comportamientos agresivos entre los machos durante la temporada de apareamiento, luchando por el control de los territorios.
Característica distintiva: La característica distintiva del Calalosaurus es su cresta dorsal, que le proporciona una apariencia imponente y le permite intimidar a sus rivales. Además, su dentadura y su hábitat le permiten ser un depredador eficiente en su medio ambiente.
