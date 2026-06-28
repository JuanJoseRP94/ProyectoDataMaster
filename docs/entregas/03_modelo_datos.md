# Entrega 3 - Diseño del modelo de datos y capa gold del proyecto

> **Nota de versión:** este documento incorpora el cambio de fuente principal descrito en la versión revisada de `02_datos_necesarios.md`, tras la devolución del profesor sobre la entrega anterior. Se sustituye la API de Idealista por scraping ligero de un portal inmobiliario (Pisos.com / Fotocasa) y se cierra Madrid como única ciudad del proyecto.

## 1. Resumen de la idea y datos del proyecto

El proyecto aborda la falta de transparencia en el mercado inmobiliario español, donde compradores y vendedores particulares no tienen forma sencilla de saber si el precio de una vivienda es justo según sus características y su entorno. La solución planteada es un modelo de regresión que estima el precio de mercado de un inmueble **en Madrid** a partir de sus características físicas y de variables de entorno urbano, presentado a través de un dashboard interactivo.

Las fuentes de datos previstas son cuatro: **scraping ligero de Pisos.com / Fotocasa** (precio de oferta, superficie, habitaciones, ubicación — fuente principal, disponible desde el primer día sin proceso de aprobación), el **Catastro** vía sus servicios web libres sin certificado (características físicas oficiales del inmueble: superficie, año de construcción, uso), el **Ministerio de Vivienda / INE** (series agregadas de precio por distrito, usadas únicamente para contexto y validación, no como entrada al modelo) y **OpenStreetMap / Overpass API** (variables geoespaciales de proximidad a transporte, colegios, parques y comercios). El portal scrapeado aporta la variable objetivo (precio) y los datos de oferta real; Catastro enriquece con datos oficiales; Ministerio/INE sirven de benchmark; OpenStreetMap enriquece el modelo con el valor del entorno.

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
|   |-- scraping_pisos_madrid_2026.csv
|   |-- catastro_madrid_2026.csv
|   |-- ministerio_vivienda_series.csv
|   `-- osm_servicios_madrid.csv
|-- processed/
|   |-- viviendas_limpio.csv
|   `-- servicios_geo_limpio.csv
`-- gold/
    `-- gold_viviendas.db
```

| Capa | Contenido esperado |
|---|---|
| **Raw** | Extracciones directas de cada fuente: HTML parseado del scraper de Pisos.com/Fotocasa volcado a CSV, respuesta XML del servicio web del Catastro convertida a CSV, CSV del Ministerio de Vivienda/INE tal cual se descarga, y JSON de Overpass API convertido a CSV. Sin transformar, solo aplanado para poder guardarlo en disco. |
| **Processed** | Datos con tipos corregidos (precio y superficie como numérico, símbolos de moneda eliminados), columnas renombradas de forma consistente entre fuentes, duplicados eliminados, y direcciones/coordenadas validadas. Aquí se hace también el cruce inicial entre los anuncios scrapeados y el Catastro por dirección. |
| **Gold** | Tabla única `gold_viviendas`, con una fila por inmueble y todas las variables (físicas + geoespaciales) ya calculadas, lista para EDA y modelado. |

Se ha optado por mantener esta estructura de tres capas (en lugar de proponer una alternativa) porque se ajusta bien al flujo del proyecto: cada fuente requiere una limpieza distinta antes de poder combinarse, por lo que tener una capa "processed" intermedia evita transformar directamente los datos crudos cada vez que se actualiza el modelo. Además, mantener la capa raw separada permite volver a ejecutar el scraper sin perder las extracciones anteriores, lo que ayuda a construir algo de variación temporal pese a no tener histórico de precios de cierre.

## 4. Definición de la capa gold

La capa gold de este proyecto consiste en una única tabla:

| Dataset gold | Granularidad | Campos clave | Uso posterior |
|---|---|---|---|
| `gold_viviendas` | Una fila por **inmueble individual** | `id_vivienda`, `precio`, `superficie_m2`, `habitaciones`, `distrito`, `dist_metro_m`, `dist_colegio_m` | Modelo de regresión (entrenamiento) + EDA + Dashboard interactivo |

**Descripción funcional:** representa el conjunto final de inmuebles en oferta en Madrid con todas sus características físicas y de entorno ya calculadas, listo para entrenar el modelo de predicción de precio y para alimentar las visualizaciones del dashboard.

**Granularidad:** una fila = un inmueble en oferta.

**Número aproximado esperado de registros:** entre 3.000 y 8.000 anuncios activos en Madrid capital, obtenidos en una o varias ejecuciones del scraper a lo largo del curso.

**Campos principales:**

| Campo | Tipo de dato | Descripción |
|---|---|---|
| `id_vivienda` | string (PK) | Identificador único del anuncio, generado a partir de la URL del anuncio scrapeado |
| `precio` | float | Precio de oferta en euros — **variable objetivo** |
| `superficie_m2` | float | Superficie construida en m² |
| `habitaciones` | integer | Número de habitaciones |
| `banos` | integer | Número de baños |
| `año_construccion` | integer | Año de construcción del inmueble (enriquecido desde Catastro) |
| `tipo_inmueble` | string (categórica) | Piso, chalet, dúplex, estudio |
| `distrito` | string (categórica) | Distrito de Madrid donde se ubica |
| `barrio` | string (categórica) | Barrio de Madrid, si el anuncio lo especifica |
| `latitud` | float | Coordenada geográfica (geocodificada a partir de la dirección del anuncio) |
| `longitud` | float | Coordenada geográfica |
| `dist_metro_m` | float | Distancia en metros a la parada de transporte más cercana |
| `dist_colegio_m` | float | Distancia en metros al centro educativo más próximo |
| `dist_parque_m` | float | Distancia en metros a la zona verde más cercana |
| `num_comercios_500m` | integer | Número de comercios en un radio de 500 metros |
| `fecha_extraccion` | date | Fecha en que se realizó el scraping de ese anuncio |

**Clave primaria:** `id_vivienda`.

**Variable objetivo:** `precio`. Variables más relevantes esperadas: `superficie_m2`, `distrito`, `dist_metro_m`, `año_construccion`.

**Fase posterior que lo consume:** EDA exploratorio, entrenamiento del modelo de regresión, y dashboard interactivo (simulador de precio + mapa de calor).

## 5. Relaciones entre datos

El proyecto trabaja, en la capa gold, con un **único dataset combinado** (`gold_viviendas`). No existen múltiples tablas relacionadas en la capa final, ya que el objetivo es tener una fila por vivienda con toda la información necesaria para el modelo, sin necesidad de joins en tiempo de análisis.

Sin embargo, **antes de llegar a la capa gold**, sí existen relaciones entre las fuentes originales que se resuelven en la capa processed:

```
scraping.direccion/coordenadas    1 --- 1   catastro.referencia_catastral
viviendas_limpio.coordenadas      1 --- N   osm_servicios.punto_interes
```

- La relación entre los **anuncios scrapeados** y el **Catastro** es teóricamente 1:1 (cada anuncio corresponde a un inmueble con una única referencia catastral), aunque en la práctica el cruce se hará por dirección (calle y número, consultados contra el servicio web del Catastro), ya que no existe un identificador común exacto entre ambas fuentes. No todas las direcciones de los anuncios estarán completas o serán exactas, por lo que se espera un porcentaje de inmuebles sin enriquecimiento catastral.
- La relación con **OpenStreetMap** es 1:N: para cada vivienda se consultan múltiples puntos de interés (varias paradas de transporte, varios colegios, etc.) y se agregan mediante una función de mínimo (distancia al más cercano) o conteo (número de comercios en un radio).
- Los datos del **Ministerio de Vivienda / INE** no se cruzan directamente con `gold_viviendas`; se mantienen como tabla de referencia aparte (`processed/ministerio_series.csv`) para contexto y validación del modelo, comparando el precio medio que predice el modelo con las estadísticas oficiales por distrito.

El principal problema esperado al combinar fuentes es la **ausencia de una clave común exacta** entre los anuncios scrapeados y el Catastro, lo que obligará a un cruce por dirección textual y a aceptar un margen de inmuebles que no se podrán enriquecer con datos catastrales.

## 6. Diccionario de datos inicial

| Campo | Descripción | Tipo de dato | Fuente | Obligatorio | Observaciones |
|---|---|---|---|---|---|
| `id_vivienda` | Identificador único del anuncio | string | Scraping (Pisos.com/Fotocasa) | Sí | Se genera a partir de la URL del anuncio, que sí es estable |
| `precio` | Precio de oferta en euros | float | Scraping | Sí | Viene como texto con símbolo €/puntos de miles; requiere limpieza |
| `superficie_m2` | Superficie construida en metros cuadrados | float | Scraping / Catastro | Sí | Puede haber discrepancias entre ambas fuentes; se prioriza Catastro si existe el cruce |
| `habitaciones` | Número de habitaciones | integer | Scraping | Sí | — |
| `banos` | Número de baños | integer | Scraping | No | Deseable, no siempre informado en el anuncio |
| `año_construccion` | Año de construcción del inmueble | integer | Catastro | No | Deseable; solo disponible si el cruce por dirección tiene éxito |
| `tipo_inmueble` | Categoría del inmueble (piso, chalet, dúplex...) | string (categórica) | Scraping | Sí | Normalizar valores (ej. "Piso" vs "piso" vs "Apartamento") |
| `distrito` | Distrito de Madrid donde se ubica el inmueble | string (categórica) | Scraping | Sí | Normalizar nombres (acentos, mayúsculas, variantes de escritura) |
| `barrio` | Barrio de Madrid | string (categórica) | Scraping | No | No todos los anuncios lo especifican |
| `latitud` / `longitud` | Coordenadas geográficas del inmueble | float | Geocodificación de la dirección del anuncio | Sí | Necesarias para el cruce con OpenStreetMap y con el Catastro |
| `dist_metro_m` | Distancia en metros a transporte público más cercano | float | OpenStreetMap (Overpass) | No | Deseable; cobertura excelente en Madrid capital |
| `dist_colegio_m` | Distancia en metros al colegio más cercano | float | OpenStreetMap (Overpass) | No | Deseable |
| `dist_parque_m` | Distancia en metros a zona verde más cercana | float | OpenStreetMap (Overpass) | No | Deseable |
| `num_comercios_500m` | Número de comercios en radio de 500m | integer | OpenStreetMap (Overpass) | No | Deseable |
| `fecha_extraccion` | Fecha de la ejecución del scraper que obtuvo el registro | date | Scraping | Sí | Formato esperado: YYYY-MM-DD; permite distinguir extracciones sucesivas |

## 7. Problemas de calidad esperados

- **Valores nulos:** especialmente en `año_construccion` (solo disponible si el cruce con Catastro tiene éxito) y `banos` (no siempre informado en el anuncio). También es posible que algunas consultas a OpenStreetMap no devuelvan resultados en zonas concretas con poca cobertura.
- **Duplicados:** un mismo inmueble puede estar publicado varias veces (reanuncios, varias inmobiliarias gestionando el mismo piso) o aparecer repetido entre distintas ejecuciones del scraper si sigue activo. Será necesario deduplicar por similitud de dirección, superficie y precio, y por URL del anuncio entre ejecuciones.
- **Inconsistencia en categorías:** el campo `tipo_inmueble` y `distrito` pueden venir escritos de formas distintas (con o sin acentos, mayúsculas, abreviaturas, variantes del nombre del distrito).
- **Unidades de medida distintas:** posible discrepancia entre la superficie declarada en el anuncio (construida o útil, no siempre se especifica) y la superficie catastral, que sigue un criterio normativo distinto.
- **Cambios de definición entre fuentes:** el precio obtenido por scraping es un precio de oferta (lo que pide el vendedor), no necesariamente el precio final de venta, lo que introduce un sesgo respecto a transacciones reales. Esto se documentará como limitación del modelo.
- **Datos desactualizados:** los anuncios reflejan oferta activa en el momento de la extracción; no hay forma de obtener precios históricos de venta cerrada por inmueble de acceso público. La variación temporal solo podrá capturarse mediante extracciones sucesivas a lo largo del curso.
- **Riesgo propio del scraping:** cambios en la estructura HTML del portal pueden romper el scraper sin previo aviso, dejando de extraerse campos o devolviendo valores vacíos; esto requerirá revisión periódica del código del scraper. También existe riesgo de bloqueo temporal por IP si no se respetan límites de velocidad razonables.
- **Sesgo de cobertura geográfica:** aunque el proyecto se centra en Madrid capital, la cantidad de anuncios y la calidad de OpenStreetMap pueden variar entre distritos, estando mejor representados los distritos centrales y de mayor actividad inmobiliaria.
- **Outliers:** viviendas de lujo o anuncios con errores de introducción de datos (precios anómalamente bajos o superficies erróneas, frecuentes en plataformas de anuncios gestionados por particulares) pueden distorsionar el modelo.
- **Problemas al cruzar fuentes:** como se ha mencionado en el punto 5, el cruce entre los anuncios scrapeados y el Catastro no tiene clave exacta y se hará por dirección textual, lo que puede generar asociaciones incorrectas o ausencia de cruce en direcciones mal formateadas en el anuncio original.

## 8. Decisiones de limpieza y transformación previstas

- **Valores nulos:** para `banos` y `año_construccion`, se imputará con la mediana del distrito o tipo de inmueble cuando falten, documentando qué proporción de registros ha sido imputada. Para las variables geoespaciales sin resultado de OSM, se asignará un valor nulo explícito (no se imputará una distancia ficticia) y se creará una columna booleana indicando si el dato está disponible.
- **Duplicados:** se eliminarán anuncios con la misma URL (entre ejecuciones del scraper) y los que coincidan en dirección, superficie y precio, conservando el registro más reciente.
- **Normalización:** los nombres de distritos/barrios y categorías de tipo de inmueble se normalizarán a minúsculas sin acentos mediante un diccionario de mapeo manual basado en la lista oficial de los 21 distritos de Madrid.
- **Variables derivadas:** se calculará `precio_por_m2` (precio / superficie) como variable auxiliar para detectar outliers, y una variable categórica `antiguedad` (nueva / reciente / antigua) derivada del año de construcción cuando esté disponible.
- **Outliers:** se aplicará un filtro basado en percentiles (se descartará el 1% superior e inferior de `precio_por_m2`) para evitar que errores de introducción de datos distorsionen el modelo.
- **Criterio de validez de un registro:** un registro se considerará válido para entrar en la capa gold si tiene informados como mínimo `precio`, `superficie_m2`, `distrito` y coordenadas válidas. Los registros sin estos campos imprescindibles se descartarán y se contabilizarán para reportar la tasa de pérdida de datos.
- **Datos descartados:** se descartarán anuncios fuera del municipio de Madrid (algunos portales incluyen localidades cercanas en los resultados de búsqueda) para mantener consistencia en el alcance geográfico del proyecto.

## 9. Riesgos del modelo de datos

**Parte más clara:** la definición de la tabla `gold_viviendas` y sus campos principales. Al trabajar con un único dataset combinado y una única ciudad, el contrato de datos es sencillo de entender y de mantener.

**Parte que genera más incertidumbre:** el mantenimiento del scraper a lo largo del curso. A diferencia de una API estable, el HTML de un portal inmobiliario puede cambiar sin previo aviso, lo que obligaría a ajustar el código de extracción. También genera incertidumbre el cruce entre los anuncios scrapeados y el Catastro, al no existir una clave exacta entre ambas fuentes.

**Fuente que puede dar más problemas:** el portal scrapeado (Pisos.com o Fotocasa), tanto por el riesgo de bloqueo de IP o cambios de estructura HTML, como por el hecho de que los precios son de oferta y no de cierre de venta, lo que limita la fiabilidad del modelo como predictor de precio "real" de transacción.

**Si no se pudiera construir la capa gold como se ha definido:** se simplificaría eliminando las variables geoespaciales de OpenStreetMap y el cruce con Catastro (ambos deseables, no imprescindibles), trabajando únicamente con las variables que ofrece directamente el scraping. El modelo perdería capacidad explicativa pero seguiría siendo viable con un volumen de datos suficiente.

**Alternativa de simplificación:** si el scraper deja de funcionar de forma sostenida durante el curso (bloqueo persistente o cambio estructural del portal), se cambiará de portal (de Pisos.com a Fotocasa, o viceversa, ya que ambos exponen información similar en el HTML) manteniendo el mismo enfoque técnico. Como última alternativa, se trabajaría con una única extracción amplia realizada al inicio del curso como dataset estático, renunciando a actualizaciones periódicas pero conservando la granularidad por inmueble individual que es la pieza central del proyecto.
