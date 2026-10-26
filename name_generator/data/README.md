# Datos

`dinos.csv` (columna `name`) se genera con `python name_generator/download_data.py`.

Fuente: lista publica de ~1536 nombres de dinosaurios usada en el curso Sequence Models
(deeplearning.ai), tomada del repositorio ArkaSarkar19/Character-level-language-model-Dinosaurus-Island.
El profesor no entrego un dinos.csv; esta es la alternativa publica equivalente.

Limpieza prevista en el preprocesamiento: quitar duplicados, filas que no son nombres
(p. ej. "Skeleton"), nombres pegados sin separador y caracteres fuera de a-z.
