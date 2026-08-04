# Entrega 4 - Diseño del análisis y estrategia de modelado

> Este documento continúa de forma incremental el trabajo de las entregas anteriores. La capa gold de referencia es `gold_anuncios`, definida en `03_modelo_datos.md`: una fila por anuncio activo en Fotocasa en la fecha de extracción, con clave primaria `(id_anuncio, fecha_extraccion)`, variable objetivo `precio_oferta` y enriquecimiento opcional de Catastro y OpenStreetMap.

---

## 1. Problema que se busca resolver

**Qué ocurre actualmente y por qué supone un problema**

Cuando una persona busca comprar o vender una vivienda en Madrid, no dispone de una referencia objetiva para evaluar si el precio publicado en un anuncio es razonable dado el inmueble y su entorno. Los portales inmobiliarios muestran los anuncios sin contexto comparativo estructurado: el comprador puede ver otros anuncios similares manualmente, pero no existe una estimación automática que le diga cuánto debería costar ese tipo de inmueble en esa zona con esas características. Esta asimetría favorece al vendedor o a quien tiene más experiencia en el mercado.

**Quién utilizará el resultado y para qué decisión**

El usuario principal es un comprador particular que está evaluando anuncios en Madrid. El resultado le permite responder una pregunta concreta: *¿el precio de este anuncio está por encima o por debajo de lo habitual para un inmueble con estas características en este distrito?* Con esa información puede decidir si continuar negociando, descartar el anuncio o hacer una oferta más informada. Un usuario secundario sería un vendedor que quiere fijar un precio de publicación competitivo.

**Qué resultado concreto consideraría útil el proyecto**

El proyecto se considerará útil si el modelo es capaz de estimar el `precio_oferta` de un anuncio con un error medio absoluto (MAE) inferior al 15% del precio real, y si ese resultado mejora claramente una referencia simple (la media del distrito). En el MVP, el usuario introduce las características del anuncio y obtiene una estimación de precio de oferta junto con el rango habitual para anuncios similares. Queda explícitamente fuera del alcance estimar el precio de cierre de la transacción o el valor de tasación oficial.

---

## 2. Análisis de datos planteado y utilidad esperada

El análisis se estructura en tres momentos del proyecto: antes del modelado (EDA), durante (análisis de features) y después (análisis de errores).

### Preguntas que se quieren responder con los datos

- ¿Cómo se distribuyen los precios de oferta por distrito y tipo de inmueble en Madrid?
- ¿Existe una relación clara y lineal entre superficie y precio, o hay efectos de umbral (por ejemplo, pisos muy grandes con precio por m² menor)?
- ¿Qué variables tienen más correlación con el precio de oferta: las características físicas del inmueble o las variables geoespaciales?
- ¿Hay distritos con comportamiento atípico (precio alto con superficies pequeñas, o precio bajo con buena conectividad)?
- ¿Los anuncios con `catastro_confianza = alta` tienen distribuciones de precio distintas a los que no tienen cruce catastral?
- ¿El precio por m² varía significativamente según el año de construcción del inmueble?

### Análisis planteados

**Análisis descriptivo general:**
Distribución de `precio_oferta` y `precio_por_m2` (histogramas, boxplots). Detección visual de outliers antes y después del filtrado por percentiles. Estadísticos básicos por distrito (media, mediana, desviación estándar, número de anuncios).

**Análisis geográfico:**
Mapa de calor de precio medio por distrito. Comparación del precio por m² entre los 21 distritos, ordenados de mayor a menor. Este análisis alimenta directamente el dashboard del MVP.

**Análisis de correlaciones:**
Matriz de correlación entre las variables numéricas (`superficie_m2`, `habitaciones`, `año_construccion`, `dist_metro_m`, `dist_colegio_m`, `dist_parque_m`, `num_comercios_500m`) y la variable objetivo `precio_oferta`. Identificación de multicolinealidad entre features geoespaciales.

**Análisis por segmentos:**
Comparación de precio medio y precio por m² según `tipo_inmueble` y `antiguedad`. Permite detectar si el modelo necesitará tratar estos segmentos de forma diferenciada.

**Análisis de calidad del enriquecimiento catastral:**
Distribución del campo `catastro_confianza` (proporción de `alta`, `media`, `sin_cruce`). Comparación de precio y superficie entre anuncios con y sin cruce para detectar sesgo de cobertura catastral.

**Hipótesis a comprobar:**
- H1: El distrito es la variable con mayor poder explicativo sobre el precio de oferta (más que la superficie).
- H2: La distancia al metro tiene correlación negativa con el precio, especialmente en distritos periféricos.
- H3: Los inmuebles con año de construcción posterior a 2000 tienen un precio por m² significativamente mayor que los anteriores a 1980.

**Visualizaciones que pueden incorporarse al MVP:**
Mapa de calor de precios por distrito, distribución de precios para el distrito seleccionado, y gráfico de importancia de variables del modelo.

---

## 3. Tipo de modelos que se van a plantear

**Tipo de tarea:** regresión supervisada. La variable objetivo es `precio_oferta` (continua, en euros). El modelo aprende a estimar el precio de oferta de un anuncio dado sus atributos, no el precio de cierre de la transacción.

| Alternativa | Tipo | Por qué se plantea | Limitación principal |
|---|---|---|---|
| **Baseline** | Media del precio por distrito y tipo de inmueble | Referencia mínima reproducible sin modelo. Cualquier modelo debe superarla claramente para justificar su complejidad. | No captura la superficie ni el resto de variables; será impreciso en inmuebles atípicos dentro del mismo segmento. |
| **Modelo 1: Regresión lineal múltiple** | Modelo lineal interpretable | Permite obtener coeficientes directamente interpretables (cuánto sube el precio por cada m² adicional, o por cada km de distancia al metro menos). Sirve como primer modelo real y como referencia de interpretabilidad. | Asume relaciones lineales entre variables y precio, lo que puede no cumplirse en todos los segmentos del mercado. |
| **Modelo 2: Random Forest Regressor** | Ensemble de árboles de decisión | Captura relaciones no lineales e interacciones entre variables (por ejemplo, el efecto del metro puede depender del distrito). Robusto frente a outliers y a variables con distintas escalas. Ofrece importancia de variables. | Menos interpretable que la regresión lineal; mayor riesgo de sobreajuste si el dataset es pequeño; más lento de entrenar. |
| **Modelo 3 (opcional): Gradient Boosting (XGBoost / LightGBM)** | Boosting de árboles | Si Random Forest no supera la regresión lineal, Gradient Boosting suele capturar mejor las no linealidades con menos sobreajuste. Se plantea como tercer candidato solo si el tiempo del curso lo permite. | Mayor complejidad de hiperparámetros; menos intuitivo para presentar en el MVP. |

La selección final entre Modelo 1 y Modelo 2 se hará según los criterios definidos en la sección 6. No se plantean modelos de deep learning (innecesarios para el volumen y el tipo de datos de este proyecto) ni modelos de series temporales (la dimensión temporal del dataset es limitada).

---

## 4. Datos de entrada del análisis y los modelos

**Dataset de entrada:** `gold_anuncios` (tabla SQLite, capa gold definida en `03_modelo_datos.md`).

**Granularidad:** una fila por anuncio activo en Fotocasa en la fecha de extracción. Clave primaria: `(id_anuncio, fecha_extraccion)`.

**Nota sobre la dimensión temporal:** si se dispone de varias extracciones a lo largo del curso, se usará la más reciente como base principal del entrenamiento. Los anuncios repetidos entre extracciones (mismo `id_anuncio` en distintas fechas) se tratarán como observaciones independientes, ya que pueden reflejar cambios de precio relevantes para el modelo.

### Variables de entrada

| Variable | Descripción | Tipo | Transformación necesaria |
|---|---|---|---|
| `superficie_m2` | Superficie del anuncio (o catastral si `catastro_confianza = alta`) | Numérica continua | Ninguna; se aplicará escalado si el modelo lo requiere |
| `habitaciones` | Número de habitaciones | Numérica discreta | Tratamiento de nulos por mediana de distrito |
| `banos` | Número de baños | Numérica discreta | Tratamiento de nulos por mediana; puede omitirse si falta en >30% de registros |
| `tipo_inmueble` | Categoría del inmueble | Categórica (5 valores) | One-hot encoding |
| `distrito` | Distrito de Madrid | Categórica (21 valores) | One-hot encoding o target encoding según el modelo |
| `año_construccion` | Año de construcción del inmueble | Numérica discreta | Solo disponible si `catastro_confianza ∈ {alta, media}`; se creará `antiguedad` como variable derivada |
| `dist_metro_m` | Distancia al transporte más cercano | Numérica continua | Tratamiento de nulos si OSM no devuelve resultado (raro en Madrid) |
| `dist_colegio_m` | Distancia al colegio más cercano | Numérica continua | Igual que `dist_metro_m` |
| `dist_parque_m` | Distancia al parque más cercano | Numérica continua | Igual que `dist_metro_m` |
| `num_comercios_500m` | Comercios en 500 m | Numérica discreta | Posible transformación logarítmica si la distribución es muy asimétrica |
| `precio_por_m2` | Variable derivada: precio_oferta / superficie_m2 | Numérica continua | Solo para EDA y detección de outliers; **no se usa como feature del modelo** (sería fuga de información) |
| `antiguedad` | Variable derivada: nueva / reciente / antigua | Categórica (3 valores) | Derivada de `año_construccion`; one-hot encoding |

### Variables que **no** se utilizarán en el modelo y motivo

| Variable | Motivo de exclusión |
|---|---|
| `precio_por_m2` | **Fuga de información (data leakage):** se calcula a partir de `precio_oferta`, que es la variable objetivo. Usarla como feature haría que el modelo trivialmente prediga el precio. Solo se usa en EDA. |
| `barrio` | Alta cardinalidad (>100 valores) y cobertura incompleta en los anuncios. Se prefiere `distrito` como agrupación geográfica más estable. |
| `superficie_m2_catastro` | Solo disponible en una fracción de registros; se usa como fuente alternativa de `superficie_m2`, no como feature independiente. |
| `catastro_confianza` | Variable de trazabilidad del pipeline, no una característica del inmueble. Se puede usar como variable de análisis de calidad pero no como feature del modelo. |
| `latitud` / `longitud` | Las coordenadas brutas no son features directamente interpretables para el modelo de regresión; su información ya está capturada por `distrito` y las variables de proximidad de OSM. |
| `id_anuncio` | Identificador sin valor predictivo. |
| `fecha_extraccion` | En una primera versión del modelo no se usará como feature; podría incorporarse si se dispone de suficientes extracciones para capturar tendencia temporal. |

---

## 5. Datos de salida y forma de consumo

El modelo produce una única salida principal por cada anuncio o conjunto de características introducido:

| Campo de salida | Descripción | Tipo | Uso posterior |
|---|---|---|---|
| `id_anuncio` | Identificador del anuncio evaluado | integer | Trazabilidad: permite unir la predicción con el anuncio original |
| `fecha_ejecucion` | Fecha en que se genera la predicción | date | Control de actualización; el modelo no debe usarse con datos de más de 3 meses sin reentrenamiento |
| `precio_oferta_estimado` | Precio de oferta estimado por el modelo en euros | float | Resultado principal mostrado en el dashboard |
| `intervalo_inferior` / `intervalo_superior` | Intervalo de confianza aproximado al 80% | float | Mostrado en el dashboard como rango habitual para anuncios similares |
| `diferencia_pct` | Diferencia porcentual entre el precio del anuncio y la estimación: `(precio_anuncio - estimacion) / estimacion * 100` | float | Indicador de si el anuncio está por encima o por debajo del precio estimado; se muestra con signo y color en el dashboard |
| `variables_relevantes` | Top 3 variables con mayor peso en la predicción de ese anuncio | texto | Explicación para el usuario: "El precio estimado se basa principalmente en el distrito, la superficie y la distancia al metro" |

**Cómo utilizará el resultado el usuario:**
En el dashboard del MVP, el usuario introduce las características de un anuncio (o pega la URL de Fotocasa) y obtiene: (1) el precio estimado, (2) el rango habitual, (3) la diferencia porcentual respecto al precio publicado y (4) las principales variables que explican la estimación. Con esa información puede decidir si el anuncio está sobrevalorado, infravalorado o en rango y actuar en consecuencia.

**Aclaración importante para el usuario:**
La estimación es un precio de oferta de referencia basado en anuncios comparables en el mercado, no un precio de tasación ni una garantía de precio de venta. Se mostrará esta aclaración de forma visible en el dashboard para no sobredimensionar la promesa del producto.

**Formato previsto:** tabla en SQLite (`predicciones`) + visualización en dashboard interactivo (Streamlit o similar).

---

## 6. Estrategia para diseñar y seleccionar el modelo

### Preparación del dataset de modelado

A partir de `gold_anuncios` se construirá un dataset de modelado aplicando los siguientes pasos en orden:

1. Filtrar registros con campos imprescindibles presentes (`precio_oferta`, `superficie_m2`, `distrito`, coordenadas).
2. Aplicar filtro de outliers por percentiles de `precio_por_m2` (descartar el 1% inferior y superior).
3. Aplicar imputación de nulos en `habitaciones` y `banos` por mediana del distrito y tipo de inmueble.
4. Construir variables derivadas: `precio_por_m2` (solo EDA), `antiguedad`.
5. Codificar variables categóricas: one-hot encoding para `tipo_inmueble` y `distrito`.
6. Dividir el dataset en train/test según la estrategia descrita en la sección 7.

### Construcción del baseline

El baseline se construirá calculando, para cada combinación de `(distrito, tipo_inmueble)`, la **mediana** del `precio_oferta` observado en el conjunto de entrenamiento. La predicción del baseline para cualquier anuncio del test será la mediana del grupo al que pertenece. Se usará la mediana en lugar de la media para mayor robustez frente a outliers. Este baseline es reproducible, interpretable y no trivial de superar.

### Criterios de comparación entre modelos

| Criterio | Peso en la decisión |
|---|---|
| MAE en test (métrica principal) | Alto |
| RMSE en test (penaliza errores grandes) | Medio |
| Diferencia entre MAE en train y MAE en test (sobreajuste) | Alto |
| Interpretabilidad del modelo (puede explicarse al usuario) | Medio |
| Tiempo de entrenamiento e inferencia | Bajo |

### Regla de decisión final

Se seleccionará el modelo que cumpla las tres condiciones siguientes:
1. MAE en test inferior al 15% del precio medio del dataset.
2. Mejora el MAE del baseline en al menos un 20%.
3. La diferencia entre MAE en train y MAE en test no supera el 25% del MAE en train (indicador de sobreajuste controlado).

Si la Regresión lineal y Random Forest tienen MAE similares (diferencia < 5%), se preferirá la Regresión lineal por su mayor interpretabilidad y facilidad de explicación al usuario.

---

## 7. Estrategia de validación y evaluación

### Separación de datos

Se utilizará una **separación aleatoria estratificada por distrito**, en la siguiente proporción:

- **Train:** 70% de los anuncios.
- **Validación:** 15% (para ajuste de hiperparámetros de Random Forest).
- **Test:** 15% (para evaluación final; no se toca hasta tener el modelo definitivo).

La estratificación por distrito garantiza que todos los distritos están representados en las tres particiones, evitando que el modelo se evalúe en distritos que no ha visto durante el entrenamiento.

**¿Por qué no separación temporal?** Idealmente, la separación temporal (entrenar con extracciones antiguas, evaluar con las nuevas) sería más realista. Sin embargo, dado el volumen limitado de datos y el número probablemente reducido de extracciones disponibles durante el curso, la separación aleatoria estratificada es más robusta estadísticamente. Si se dispone de tres o más extracciones en fechas distintas, se planteará una separación temporal como validación adicional.

**Prevención de data leakage:**
- `precio_por_m2` excluida de las features (calculada a partir de la variable objetivo).
- La mediana del baseline se calcula *solo sobre el train*, nunca sobre el test.
- Los parámetros de imputación (medianas de nulos) se calculan *solo sobre el train* y se aplican al test.
- Los encodings categóricos se ajustan *solo sobre el train*.

### Métricas

| Métrica | Justificación |
|---|---|
| **MAE (Mean Absolute Error)** | Métrica principal. Mide el error medio en euros, directamente interpretable para el usuario ("el modelo se equivoca de media X euros"). Robusta frente a outliers. |
| **RMSE (Root Mean Squared Error)** | Métrica secundaria. Penaliza más los errores grandes; útil para detectar si el modelo falla especialmente en inmuebles de precio muy alto o muy bajo. |
| **R² (coeficiente de determinación)** | Complementario. Indica qué proporción de la varianza del precio explica el modelo. Útil para comunicar el rendimiento de forma intuitiva. |
| **MAE relativo (MAE / precio medio)** | Expresa el error como porcentaje del precio, que es la métrica más interpretable para el usuario final y el criterio de aceptación del proyecto. |

No se usará MAPE (Mean Absolute Percentage Error) como métrica principal porque en datos inmobiliarios puede verse distorsionado por inmuebles de precio muy bajo.

### Análisis de errores

Tras evaluar en test se realizarán los siguientes análisis:
- Distribución de residuos (precio real − precio estimado): ¿son simétricos? ¿hay sesgo sistemático?
- MAE por distrito: ¿hay distritos donde el modelo falla más? ¿coincide con los que tienen menos anuncios?
- MAE por tipo de inmueble: ¿el modelo funciona igual para pisos que para chalets?
- MAE por rango de precio: ¿el error es mayor en inmuebles de lujo (posible subrepresentación en el dataset)?
- Casos con mayor error absoluto: revisión manual de los 20 anuncios con mayor error para detectar patrones (errores de datos, inmuebles atípicos, outliers no filtrados).

### Criterio de aceptación mínimo

El modelo se considerará válido si:
- MAE relativo en test < 15% del precio medio del dataset.
- Mejora el baseline en al menos un 20% en MAE.

Si ningún modelo alcanza estos umbrales, se revisará la calidad del dataset (proporción de outliers, sesgo de cobertura por distrito, volumen insuficiente) antes de concluir que el problema no es modelable con los datos disponibles.

---

## 8. Riesgos y alternativas

**¿La variable objetivo está disponible y representa el fenómeno que se quiere predecir?**
Sí, `precio_oferta` está siempre disponible en los anuncios de Fotocasa y es el valor central del proyecto. El riesgo es que no representa el precio de cierre real, sino el precio de publicación. Esto se acepta como limitación conocida y se comunica explícitamente en el MVP.

**¿Existe riesgo de data leakage?**
El riesgo más claro es `precio_por_m2`, que está excluida de las features. El resto de variables son características del inmueble o del entorno, ninguna derivada del precio, por lo que no hay leakage adicional identificado. La única precaución adicional es calcular todos los parámetros de preprocesamiento (imputaciones, encodings, medianas del baseline) exclusivamente sobre el train.

**¿El volumen y la calidad de los datos son suficientes?**
Con 3.000-8.000 anuncios y 10-12 features, el volumen es suficiente para regresión lineal y Random Forest. Si el volumen real tras el filtrado fuera inferior a 2.000 registros, se reduciría el número de features y se evitaría Random Forest por riesgo de sobreajuste. La calidad depende en parte del cruce con Catastro (cobertura de `año_construccion`) y de las variables de OSM, ambas clasificadas como deseables pero no imprescindibles para el modelo mínimo.

**¿Hay sesgos de cobertura o segmentos con pocos datos?**
Sí: los distritos periféricos de Madrid (Vicálvaro, Barajas, Moratalaz) suelen tener menos anuncios que los centrales. Si algún distrito tiene menos de 50 anuncios en el dataset filtrado, se valorará agruparlo con distritos vecinos o eliminarlo del modelo para evitar estimaciones poco fiables en ese segmento.

**¿Qué parte de la estrategia genera más incertidumbre?**
La disponibilidad de `año_construccion` tras el cruce con Catastro. Si la proporción de `catastro_confianza = alta` es baja (inferior al 40%), el modelo tendrá que entrenarse sin esta variable en la mayoría de registros, lo que reduce su capacidad explicativa. Se verificará esto en el EDA y se decidirá si incluirla como feature con imputación o excluirla del modelo principal.

**¿Qué alternativa si el modelo no supera el baseline?**
Si ningún modelo supera el baseline en un 20%, se revisará el pipeline de datos (posibles errores en la limpieza, outliers mal filtrados, features con mala calidad). Si tras la revisión el resultado sigue siendo insatisfactorio, el MVP se reorientará hacia un análisis descriptivo avanzado (dashboard de comparación de anuncios por distrito y tipo, sin predicción activa), que sigue siendo útil para el usuario aunque no incorpore un modelo predictivo.
