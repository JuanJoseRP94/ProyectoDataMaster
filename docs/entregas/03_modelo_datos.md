# Entrega 3 - Diseño del modelo de datos y capa gold del proyecto

> **Nota de versión (v3):** tras el segundo feedback del profesor, se cierra el portal principal en **Fotocasa** (descartando la alternativa abierta Pisos.com/Fotocasa), se redefine la granularidad de la capa gold como *una fila por anuncio activo en la fecha de extracción* (no por inmueble único), se precisa el alcance del modelo como predictor de **precio de oferta** (no de precio de mercado ni de cierre), y se añaden criterios de confianza y trazabilidad para el cruce con Catastro.

## 1. Resumen de la idea y datos del proyecto

El proyecto aborda la dificultad que tienen compradores y vendedores particulares para evaluar si el precio pedido por una vivienda en Madrid es razonable respecto a anuncios comparables en el mercado. La solución planteada es un modelo de regresión que estima el **precio de oferta** de un anuncio de vivienda en venta en Madrid a partir de sus características físicas y de su entorno urbano, presentado a través de un dashboard interactivo. Es importante aclarar que el modelo no predice el precio final de cierre de la transacción ni el valor real de mercado, sino el precio al que el vendedor publica el inmueble — una distinción que se mantendrá explícita en todos los entregables del proyecto.

Las fuentes de datos son cuatro: **scraping de Fotocasa** (precio de oferta, superficie, habitaciones, tipo de inmueble, distrito y URL del anuncio — fuente principal y única portal seleccionado), el **Catastro** vía sus servicios web libres sin certificado (año de construcción y superficie oficial, como enriquecimiento opcional), el **Ministerio de Vivienda / INE** (series agregadas de precio por distrito, usadas únicamente como benchmark externo, no como entrada al modelo) y **OpenStreetMap / Overpass API** (variables geoespaciales de proximidad a transporte, colegios, parques y comercios). Fotocasa aporta la variable objetivo y los datos de anuncio; Catastro enriquece con datos oficiales cuando el cruce es posible; Ministerio/INE validan el rango de precios; OpenStreetMap añade contexto geoespacial.

## 2. Tecnología o formato de almacenamiento elegido

Se ha optado por una combinación de **CSV + SQLite**, evitando deliberadamente una base de datos relacional de servidor (PostgreSQL, MySQL) por no ser necesaria en este proyecto.

- **CSV** para la capa raw: es el formato de salida natural del proceso de scraping (cada ejecución del scraper en Python con `requests` + `BeautifulSoup` escribirá directamente a CSV), de la respuesta de los servicios web del Catastro tras parsear el XML, y de las descargas del Ministerio de Vivienda/INE. Es legible, fácil de versionar y no requiere herramientas adicionales para inspeccionarlo.
- **SQLite** para las capas processed y gold: al ser un único fichero `.db` sin necesidad de servidor, permite trabajar con tablas relacionables y hacer consultas SQL cuando convenga (por ejemplo, filtrar por barrio o calcular agregados), sin la complejidad de instalar y mantener un gestor de base de datos completo.

Esta combinación es coherente con el volumen esperado del proyecto (entre 3.000 y 8.000 registros en Madrid), con el nivel de desarrollo del curso, y con el hecho de trabajar en solitario: prioriza la simplicidad operativa sin sacrificar la posibilidad de hacer consultas estructuradas.

No se ha optado por Parquet porque el volumen de datos no lo justifica (Parquet aporta valor con volúmenes mucho mayores o necesidades de lectura columnar optimizada), ni por Excel, que no es adecuado para procesos automatizados de limpieza y transformación.

## 3. Estructura de capas de datos

Se utilizará la estructura estándar de tres capas:

```
data/
|-- raw/
|   |-- fotocasa_madrid_YYYYMMDD.csv   ← una extracción por fecha de scraping
|   |-- catastro_madrid_2026.csv
|   |-- ministerio_vivienda_series.csv
|   `-- osm_servicios_madrid.csv
|-- processed/
|   |-- anuncios_limpio.csv
|   |-- catastro_enriquecido.csv       ← con columna de confianza del cruce
|   `-- servicios_geo_limpio.csv
`-- gold/
    `-- gold_anuncios.db
```

| Capa | Contenido esperado |
|---|---|
| **Raw** | Extracciones directas de cada fuente: HTML de Fotocasa parseado y volcado a CSV (un fichero por fecha de extracción, con el nombre incluyendo la fecha), respuesta XML del Catastro convertida a CSV, CSV del Ministerio/INE tal cual se descarga, y JSON de Overpass API convertido a CSV. Sin transformar, solo aplanado para poder guardarlo. |
| **Processed** | Datos con tipos corregidos (precio y superficie como numérico, símbolo € eliminado), columnas renombradas de forma consistente, duplicados resueltos, coordenadas validadas, y resultado del cruce con Catastro documentado con columna de confianza. |
| **Gold** | Tabla única `gold_anuncios`, con **una fila por anuncio activo en la fecha de extracción**, todas las variables calculadas, lista para EDA y modelado. |

Se mantiene la estructura de tres capas porque cada fuente requiere una limpieza distinta antes de combinarse. La capa raw guarda una copia fechada de cada extracción de Fotocasa, lo que permite comparar cómo evolucionan los anuncios a lo largo del curso sin perder las capturas anteriores.

## 4. Definición de la capa gold

La capa gold de este proyecto consiste en una única tabla:

| Dataset gold | Granularidad | Campos clave | Uso posterior |
|---|---|---|---|
| `gold_anuncios` | Una fila por **anuncio activo en Fotocasa en la fecha de extracción** | `id_anuncio`, `fecha_extraccion`, `precio_oferta`, `superficie_m2`, `habitaciones`, `distrito`, `dist_metro_m` | Modelo de regresión (entrenamiento) + EDA + Dashboard interactivo |

**Decisión de granularidad — justificación explícita:**

La granularidad es *anuncio × fecha de extracción*, no *inmueble único*. Esta decisión es deliberada y responde a una limitación real de los datos: no disponemos de ninguna clave oficial que permita identificar de forma fiable si dos anuncios distintos corresponden al mismo inmueble físico. Un mismo piso puede estar publicado por varias agencias con precios distintos, puede haber sido retirado y republicado, o puede haber cambiado de precio entre extracciones. Pretender deduplicar hasta "una fila por inmueble" requeriría heurísticas (comparar dirección + superficie + precio) que introducirían errores silenciosos difíciles de detectar y de justificar.

Por tanto, **el modelo aprende sobre el precio al que se publican anuncios de vivienda**, no sobre el valor intrínseco de inmuebles únicos. Esto es exactamente lo que los datos permiten afirmar, sin sobredimensionar la promesa del proyecto.

La clave primaria del dataset gold es la combinación `(id_anuncio, fecha_extraccion)`, donde `id_anuncio` se extrae directamente del identificador numérico presente en la URL de cada anuncio de Fotocasa (ej. `/en-venta/piso/madrid/.../123456` → `id_anuncio = 123456`). Esto garantiza un identificador estable y sin ambigüedad.

**Descripción funcional:** conjunto final de anuncios de vivienda en venta en Madrid extraídos de Fotocasa, con variables de características del anuncio, enriquecimiento catastral (cuando disponible) y variables geoespaciales calculadas, listo para EDA y modelado. La variable objetivo es el **precio de oferta** publicado en el anuncio.

**Número aproximado esperado de registros:** entre 3.000 y 8.000 anuncios por extracción. Si se realizan varias extracciones a lo largo del curso, el dataset raw acumulará más registros, pero la capa gold se construirá sobre la extracción más reciente o sobre una selección filtrada, según la fase del proyecto.

**Campos principales:**

| Campo | Tipo de dato | Descripción |
|---|---|---|
| `id_anuncio` | integer | ID numérico extraído de la URL del anuncio en Fotocasa — estable mientras el anuncio esté activo |
| `fecha_extraccion` | date | Fecha de la ejecución del scraper — formato YYYY-MM-DD |
| `precio_oferta` | float | Precio publicado en el anuncio en euros — **variable objetivo**; es precio de oferta, no de cierre |
| `superficie_m2` | float | Superficie en m² declarada en el anuncio; fuente: Fotocasa |
| `superficie_m2_catastro` | float | Superficie oficial según Catastro; solo disponible si el cruce tiene éxito |
| `habitaciones` | integer | Número de habitaciones |
| `banos` | integer | Número de baños; no siempre informado |
| `tipo_inmueble` | string (categórica) | Piso, chalet, dúplex, estudio — normalizado |
| `distrito` | string (categórica) | Distrito de Madrid (21 valores posibles según nomenclatura oficial) |
| `barrio` | string (categórica) | Barrio de Madrid; no siempre informado en el anuncio |
| `latitud` | float | Coordenada geográfica geocodificada a partir de la dirección del anuncio |
| `longitud` | float | Coordenada geográfica |
| `año_construccion` | integer | Año de construcción; fuente: Catastro; solo si el cruce tiene éxito |
| `catastro_confianza` | string (categórica) | Nivel de confianza del cruce con Catastro: `alta`, `media`, `sin_cruce` |
| `dist_metro_m` | float | Distancia en metros a la parada de transporte más cercana; fuente: OSM |
| `dist_colegio_m` | float | Distancia al centro educativo más próximo; fuente: OSM |
| `dist_parque_m` | float | Distancia a la zona verde más cercana; fuente: OSM |
| `num_comercios_500m` | integer | Número de comercios en radio de 500 m; fuente: OSM |

**Clave primaria:** combinación `(id_anuncio, fecha_extraccion)`.

**Variable objetivo:** `precio_oferta`. Variables más relevantes esperadas: `superficie_m2`, `distrito`, `dist_metro_m`, `año_construccion`.

**Fuente mandante por campo:** Fotocasa manda en precio, superficie declarada, habitaciones, tipo y distrito. Catastro manda en superficie oficial y año de construcción, pero solo cuando `catastro_confianza` es `alta` o `media`. OSM manda en todas las variables geoespaciales.

**Fase posterior que lo consume:** EDA exploratorio, entrenamiento del modelo de regresión, y dashboard interactivo (estimador de precio de oferta + mapa de calor por distrito).

## 5. Relaciones entre datos

El proyecto trabaja, en la capa gold, con un **único dataset combinado** (`gold_anuncios`). No existen múltiples tablas en la capa final, ya que el objetivo es tener una fila por anuncio con toda la información ya integrada, sin joins en tiempo de análisis.

Antes de llegar a la capa gold, sí existen relaciones entre fuentes que se resuelven en la capa processed:

```
fotocasa.direccion          1 --- 0..1   catastro.referencia_catastral
anuncios_limpio.coordenadas 1 --- N      osm_servicios.punto_interes
```

**Cruce Fotocasa → Catastro (1:0..1, opcional):**
La relación es teóricamente 1:1 (cada anuncio corresponde a un inmueble catastral), pero en la práctica el cruce no siempre es posible porque las direcciones de los anuncios son texto libre y no siempre coinciden exactamente con la nomenclatura catastral. El cruce se hará consultando el servicio web SOAP del Catastro con la calle y número del anuncio. Para cada intento de cruce se asignará un nivel de confianza:
- **`alta`**: la dirección del anuncio devuelve una única referencia catastral con superficie similar (±15%) a la declarada en el anuncio.
- **`media`**: la dirección devuelve resultado, pero hay discrepancia de superficie o ambigüedad de número (portal, escalera).
- **`sin_cruce`**: la consulta no devuelve resultado o la dirección del anuncio es insuficiente para localizar el inmueble.

Los registros con `sin_cruce` entran igualmente en la capa gold, pero sin los campos de Catastro (`año_construccion`, `superficie_m2_catastro`). El modelo se entrenará sobre todos los registros, usando solo los campos de Fotocasa cuando el Catastro no esté disponible. Se documentará la proporción de cada nivel de confianza como métrica de calidad del pipeline.

**Relación con OpenStreetMap (1:N → agregada a 1:1):**
Para cada anuncio se consultan múltiples puntos de interés cercanos y se agregan a un único valor por campo (mínimo para distancias, conteo para comercios), resultando en una relación efectiva 1:1 en la capa gold.

**Ministerio de Vivienda / INE:**
No se cruza con `gold_anuncios`. Se mantiene como tabla de referencia aparte en `processed/ministerio_series.csv` para validar que los precios medios del dataset estén en el rango esperado por distrito.

## 6. Diccionario de datos inicial

| Campo | Descripción | Tipo de dato | Fuente | Obligatorio | Observaciones |
|---|---|---|---|---|---|
| `id_anuncio` | ID numérico del anuncio extraído de la URL de Fotocasa | integer | Fotocasa (scraping) | Sí | Estable mientras el anuncio está activo; forma parte de la PK junto con `fecha_extraccion` |
| `fecha_extraccion` | Fecha de la ejecución del scraper | date | Scraping | Sí | Formato YYYY-MM-DD; forma parte de la PK |
| `precio_oferta` | Precio publicado en el anuncio en euros | float | Fotocasa | Sí | Precio de **oferta**, no de cierre; viene como texto con € y puntos de miles, requiere limpieza |
| `superficie_m2` | Superficie en m² declarada en el anuncio | float | Fotocasa | Sí | Puede ser construida o útil según el anunciante; no siempre se especifica |
| `superficie_m2_catastro` | Superficie construida oficial según Catastro | float | Catastro | No | Solo disponible si `catastro_confianza` es `alta` o `media` |
| `habitaciones` | Número de habitaciones | integer | Fotocasa | Sí | — |
| `banos` | Número de baños | integer | Fotocasa | No | No siempre informado en el anuncio |
| `tipo_inmueble` | Categoría del inmueble | string (categórica) | Fotocasa | Sí | Valores: piso, chalet, dúplex, estudio — normalizar a minúsculas sin acentos |
| `distrito` | Distrito de Madrid | string (categórica) | Fotocasa | Sí | 21 valores posibles; normalizar contra nomenclatura oficial del Ayuntamiento de Madrid |
| `barrio` | Barrio de Madrid | string (categórica) | Fotocasa | No | No siempre informado; no se usará como variable del modelo por su alta cardinalidad |
| `latitud` / `longitud` | Coordenadas geocodificadas a partir de la dirección del anuncio | float | Geocodificación | Sí | Necesarias para el cruce con Catastro y con OSM |
| `año_construccion` | Año de construcción del inmueble | integer | Catastro | No | Solo si `catastro_confianza` es `alta` o `media` |
| `catastro_confianza` | Nivel de confianza del cruce con Catastro | string (categórica) | Pipeline interno | Sí | Valores: `alta`, `media`, `sin_cruce`; sirve de trazabilidad del enriquecimiento |
| `dist_metro_m` | Distancia en metros a la parada de transporte más cercana | float | OpenStreetMap | No | Cobertura excelente en Madrid capital |
| `dist_colegio_m` | Distancia en metros al centro educativo más próximo | float | OpenStreetMap | No | — |
| `dist_parque_m` | Distancia en metros a la zona verde más cercana | float | OpenStreetMap | No | — |
| `num_comercios_500m` | Número de comercios en radio de 500 m | integer | OpenStreetMap | No | — |

## 7. Problemas de calidad esperados

- **Valores nulos:** especialmente en `año_construccion` (solo cuando el cruce con Catastro tiene éxito) y `banos` (no siempre informado en Fotocasa). Las variables de OSM estarán disponibles en prácticamente todos los anuncios de Madrid capital, donde la cobertura es muy completa.
- **Duplicados entre extracciones:** el mismo anuncio (mismo `id_anuncio`) aparecerá en varias ejecuciones del scraper mientras esté activo. Esto es **esperado y aceptado** dado que la granularidad de la gold es anuncio × fecha. Lo que sí se elimina en la capa processed son los anuncios con `id_anuncio` duplicado *dentro de la misma extracción*, que indicarían un error del scraper.
- **Duplicados entre agencias:** un mismo inmueble físico puede estar publicado por varias agencias con `id_anuncio` distintos. No se intenta resolver esta ambigüedad en la capa gold, ya que sin clave oficial no es posible hacerlo de forma fiable. Se documenta como limitación conocida del dataset.
- **Inconsistencia en categorías:** `tipo_inmueble` y `distrito` pueden venir con variantes ortográficas desde Fotocasa. Se normalizarán a minúsculas sin acentos, usando la lista oficial de los 21 distritos de Madrid como referencia para el campo `distrito`.
- **Discrepancia de superficie entre fuentes:** la superficie declarada en Fotocasa puede ser construida o útil según el anunciante; la del Catastro siempre es construida. Solo se usa la superficie catastral cuando `catastro_confianza` es `alta`, para evitar comparar magnitudes distintas.
- **Precio de oferta vs. precio de cierre:** el modelo predice `precio_oferta`, no el precio de transacción real. Esta limitación queda explícita en el nombre del campo y en todos los entregables del proyecto. No se intenta corregir este sesgo.
- **Riesgo de scraping:** cambios en el HTML de Fotocasa pueden romper el scraper sin previo aviso. También existe riesgo de bloqueo temporal por IP si no se respetan límites de velocidad. Se mitigará con `User-Agent` adecuado, pausas entre peticiones y revisión del scraper al inicio de cada fase del curso.
- **Sesgo de cobertura por distrito:** los distritos del centro y del norte de Madrid (Salamanca, Chamberí, Retiro) suelen tener más anuncios que los periféricos. Esto puede sesgar el modelo hacia precios altos si no se controla en la fase de EDA.
- **Outliers:** anuncios de lujo o errores de introducción (precio de 1 € o superficie de 1 m²) pueden distorsionar el modelo y se filtrarán por percentiles en la limpieza.

## 8. Decisiones de limpieza y transformación previstas

- **Valores nulos:** `banos` y `año_construccion` se imputarán con la mediana del distrito y tipo de inmueble, documentando la proporción imputada. Las variables de OSM se dejarán como nulo explícito cuando no haya resultado (no se imputa una distancia ficticia); se creará una columna booleana `osm_disponible` como trazabilidad.
- **Duplicados dentro de una extracción:** si el mismo `id_anuncio` aparece más de una vez en el mismo fichero raw (error del scraper), se conserva solo la primera ocurrencia y se registra el incidente.
- **Duplicados entre extracciones:** son datos válidos y esperados (mismo anuncio activo en fechas distintas). No se eliminan; la PK compuesta `(id_anuncio, fecha_extraccion)` los distingue correctamente.
- **Normalización:** `distrito` se normalizará contra la lista oficial de los 21 distritos de Madrid usando un diccionario de mapeo. `tipo_inmueble` se normalizará a 5 categorías: `piso`, `chalet`, `duplex`, `estudio`, `otro`.
- **Superficie mandante:** cuando `catastro_confianza = alta`, el campo `superficie_m2` del modelo se tomará de `superficie_m2_catastro`. En los demás casos, se usará la superficie declarada en Fotocasa. Se creará una columna `superficie_fuente` (`fotocasa` / `catastro`) para trazabilidad.
- **Variables derivadas:** `precio_por_m2` (precio_oferta / superficie_m2) para detección de outliers, y `antiguedad` (nueva ≤5 años / reciente ≤20 años / antigua >20 años) derivada de `año_construccion` cuando esté disponible.
- **Outliers:** se filtrarán el 1% superior e inferior de `precio_por_m2`. Adicionalmente se descartarán anuncios con `precio_oferta < 30.000 €` o `superficie_m2 < 15` como errores manifiestos.
- **Criterio de validez para entrar en la capa gold:** el registro debe tener `precio_oferta`, `superficie_m2`, `distrito` y coordenadas válidas. Sin alguno de estos cuatro campos el registro se descarta y se contabiliza en un informe de calidad del pipeline.
- **Fuera de alcance geográfico:** se descartarán anuncios fuera del municipio de Madrid (Fotocasa puede devolver resultados de municipios limítrofes en búsquedas amplias).

## 9. Riesgos del modelo de datos

**Parte más clara:** la definición de la tabla `gold_anuncios`, su clave primaria compuesta y sus campos principales. La granularidad *anuncio × fecha* es honesta con los datos disponibles y elimina la necesidad de heurísticas de deduplicación que introducirían errores difíciles de detectar. El contrato de datos está cerrado: Fotocasa manda en precio y características del anuncio, Catastro en datos oficiales del inmueble (cuando hay cruce), y OSM en variables geoespaciales.

**Parte que genera más incertidumbre:** el rendimiento del cruce con Catastro. La proporción de registros con `catastro_confianza = alta` determinará cuántos anuncios tendrán `año_construccion` disponible, que es una de las variables más relevantes para el modelo. Si esa proporción es baja (por ejemplo, por anuncios con direcciones incompletas), el modelo perderá capacidad explicativa en esa dimensión.

**Fuente que puede dar más problemas:** Fotocasa, por el riesgo de cambios en su estructura HTML o bloqueo de IP. Al haber cerrado el portal a uno solo (ya no hay alternativa abierta entre dos), cualquier problema con Fotocasa requiere una decisión de reemplazo. Se mitigará realizando la primera extracción grande al inicio del curso para tener un dataset estático de respaldo incluso si el scraper deja de funcionar temporalmente.

**Si no se pudiera construir la capa gold como se ha definido:** la versión mínima viable del dataset gold es un CSV con solo las columnas de Fotocasa (`id_anuncio`, `fecha_extraccion`, `precio_oferta`, `superficie_m2`, `habitaciones`, `tipo_inmueble`, `distrito`). Sin Catastro ni OSM el modelo es más simple pero completamente funcional. Esta versión de emergencia puede construirse con una sola ejecución del scraper sin ningún cruce adicional.

**Alternativa de simplificación:** si Fotocasa bloquea el scraper de forma persistente, se migrará a Pisos.com con el mismo enfoque técnico (HTML similar, ID en URL). Como última alternativa, se trabajará con el dataset estático obtenido en la primera extracción, sin actualizaciones, aceptando una muestra fija en lugar de un flujo continuo.
