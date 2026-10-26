# Evidencias: generador de nombres

## Arquitectura y configuraciones evaluadas
| configuracion | arquitectura | capas | estado_oculto | epocas | funcion_perdida | optimizador | parametros | mejor_val | mejor_epoca |
|---|---|---|---|---|---|---|---|---|---|
| A_GRU_1x128 | GRU | 1 | 128 | 60 | CrossEntropy (ignore_index=<PAD>) | Adam | 66877 | 1.5793 | 13 |
| B_LSTM_2x256 | LSTM | 2 | 256 | 60 | CrossEntropy (ignore_index=<PAD>) | Adam | 865373 | 1.5713 | 13 |

Modelo seleccionado: **B_LSTM_2x256** (menor perdida de validacion: 1.5713).
Vocabulario: 29 tokens (a-z + <PAD>, <SOS>, <EOS>). T = 24. Nombres unicos tras la limpieza: 1532
(1379 entrenamiento / 153 validacion). <PAD> excluido de la perdida con `ignore_index`.

Curvas de perdida: `docs/evidencias/curvas_perdida.png`.

## Configuraciones de muestreo
| muestreo | temperatura | top_k | top_p | %_nuevos | %_unicos | long_media | %_sufijo_tipico | ejemplos_nuevos |
|---|---|---|---|---|---|---|---|---|
| T=0.5 | 0.5 | nan | nan | 85.7 | 92.3 | 11.6 | 87.3 | angungsaurus, placroceratops, boryphosaurus, sphiselosaurus, alacanthosaurus |
| T=1.0 | 1.0 | nan | nan | 98.3 | 100.0 | 12.0 | 65.0 | zunandssaurus, nanotolosaurus, ornathorlentosaurus, faninshousaurus, micropateryx |
| T=1.3 | 1.3 | nan | nan | 100.0 | 100.0 | 12.3 | 47.3 | zunandssaurus, nmerhonosaurus, ornathkilengx, phipelosuchus, coacstenyx |
| T=1.0 + top-k=5 | 1.0 | 5.0 | nan | 96.7 | 95.3 | 11.7 | 73.7 | angunsaurus, anganosaurus, parosaurus, tarchysphus, argosauros |
| T=1.0 + top-p=0.9 | 1.0 | nan | 0.9 | 97.0 | 99.3 | 12.0 | 81.0 | zunandrosaurus, marhenosaurus, ornathoraptor, phiaelosaurus, aoacanthus |
| T=1.3 + top-p=0.9 | 1.3 | nan | 0.9 | 99.0 | 100.0 | 12.0 | 62.3 | zunandssaurus, nanotolosaurus, ornathoraptor, phipelosuchus, coacstenyx |

## Diez nombres generados (ninguno esta en el conjunto de entrenamiento)
| # | nombre | muestreo |
|---|---|---|
| 1 | calalosaurus | T=0.5 |
| 2 | calhadopis | T=1.3 |
| 3 | calastomis | T=1.0 + top-k=5 |
| 4 | calalobans | T=1.3 + top-p=0.9 |
| 5 | junangosaurus | T=0.5 |
| 6 | junansianophelion | T=1.0 |
| 7 | dracramosaurus | T=1.3 |
| 8 | stetramosaurus | T=1.0 + top-k=5 |
| 9 | junansianophelia | T=1.0 + top-p=0.9 |
| 10 | chuanghengosaurus | T=0.5 |

**Nombre seleccionado:** Calalosaurus (muestreo T=0.5).

## Analisis (valores medidos sobre 300 nombres por configuracion)
- Mayor porcentaje de nombres nuevos: **T=1.3** (100.0 %). Menor: **T=0.5** (85.7 %).
- Mayor diversidad (porcentaje de nombres unicos): **T=1.0** (100.0 %).
- Con temperatura baja el modelo tiende a repetir patrones frecuentes y a reproducir nombres del conjunto de entrenamiento;
  con temperatura alta aumenta la novedad, pero pueden aparecer secuencias menos pronunciables.
- Top-k y top-p recortan la cola de caracteres improbables y permiten usar temperaturas altas manteniendo nombres mas plausibles.

## Interpretacion propia (completar)
- Que configuracion de entrenamiento rindio mejor y por que (compare curvas, sobreajuste, tamanos).
- Que muestreo da el mejor equilibrio entre novedad y verosimilitud segun los nombres obtenidos.
