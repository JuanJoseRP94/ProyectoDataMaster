# Entrega 2 - Selección de idea de proyecto y análisis de datos necesarios

> **Nota de versión:** este documento ha sido revisado tras la devolución del profesor, que señaló el riesgo de depender de la API de Idealista (acceso no garantizado a tiempo, sin histórico, y datos de oferta no equivalentes a precio de cierre). Se ha cerrado una ciudad, una fuente principal realmente disponible desde el primer día y una alternativa de descarga inmediata. Los cambios respecto a la versión anterior se indican explícitamente en cada sección.

## 1. Idea seleccionada

**Predicción de precios de vivienda en Madrid mediante modelos de regresión y análisis geoespacial.**

### Problema que resuelve

El mercado inmobiliario español presenta una opacidad estructural que dificulta la toma de decisiones tanto para compradores particulares como para inversores. Determinar si el precio de un inmueble es justo o está sobrevaluado requiere hoy un conocimiento experto o el acceso a herramientas de tasación profesional de coste elevado. Esta asimetría de información penaliza especialmente a compradores sin experiencia, que representan la mayoría de las transacciones del mercado residencial. El problema es relevante en un contexto de escalada sostenida de precios en las principales ciudades españolas, donde la falta de transparencia genera ineficiencias tanto en el mercado de compraventa como en el de alquiler.

### Solución planteada

El proyecto abordará el problema desde un enfoque de Data Science supervisado, construyendo un modelo de regresión capaz de estimar el precio de mercado de una vivienda **en la ciudad de Madrid** a partir de sus características físicas, su localización y su entorno urbano. Los datos de cada inmueble (superficie, habitaciones, tipo de inmueble y precio de oferta) se obtendrán de un portal inmobiliario mediante scraping ligero, se complementarán con datos oficiales del Catastro (superficie certificada, año de construcción) y se enriquecerán con variables geoespaciales de OpenStreetMap (distancia a transporte, colegios, parques y comercios). El enfoque general consistirá en entrenar y comparar varios algoritmos de regresión (lineal múltiple, Random Forest, Gradient Boosting), evaluando su capacidad de generalización con técnicas estándar de validación.

### MVP del proyecto final

El producto mínimo viable consistirá en un dashboard interactivo que permita introducir las características de una vivienda en Madrid (barrio, superficie, número de habitaciones, año de construcción y proximidad a servicios clave) y obtenga una estimación de precio junto con un intervalo de confianza. El dashboard mostrará también un mapa de calor con la distribución de precios por barrio y una visualización de las variables con mayor peso en la predicción. El modelo será evaluado con métricas estándar de regresión (RMSE, MAE y R²) y se presentará como un informe técnico reproducible.

---

## 2. Datos necesarios

*(Sin cambios sustanciales respecto a la versión anterior; se mantiene aquí por completitud y trazabilidad)*

### Variables e información requerida

**Bloque A — Variables del inmueble (imprescindibles):**
- Precio de oferta (variable objetivo del modelo)
- Superficie construida en m²
- Número de habitaciones y número de baños
- Tipo de inmueble (piso, chalet, dúplex, estudio)
- Dirección o coordenadas (latitud/longitud)
- Barrio y distrito de Madrid

**Bloque B — Variables geoespaciales derivadas (deseables):**
- Distancia a la parada de metro o autobús más cercana
- Distancia al centro educativo más próximo
- Distancia a zonas verdes o parques
- Número de servicios comerciales en un radio de 500 m

### Granularidad y profundidad histórica

- **Granularidad:** a nivel de inmueble individual (una fila = una vivienda en oferta).
- **Profundidad histórica:** los anuncios de portales inmobiliarios reflejan oferta activa en el momento de la extracción; no existe histórico de precios de cierre por inmueble individual de acceso público. Se compensará con varias extracciones espaciadas en el tiempo durante el curso para capturar variación temporal limitada, y con las series históricas del Ministerio de Vivienda y el INE como contexto agregado.
- **Volumen estimado:** entre 3.000 y 8.000 anuncios activos en Madrid capital es razonable y suficiente para un modelo de regresión robusto en este contexto académico.

### Datos imprescindibles vs. deseables

- **Imprescindibles:** precio de oferta, superficie, barrio/coordenadas, número de habitaciones.
- **Deseables:** año de construcción (Catastro), variables geoespaciales (OpenStreetMap).

---

## 3. Fuentes de datos previstas

> **Cambio principal respecto a la versión anterior:** se sustituye Idealista como fuente principal por **Pisos.com o Fotocasa**, mediante scraping ligero con Python, por ser fuentes con menor protección anti-bot y de acceso inmediato sin proceso de aprobación. Idealista queda descartada como fuente principal, precisamente por el riesgo señalado por el profesor.

### Fuente principal: Pisos.com / Fotocasa (scraping ligero)

Ambos portales publican anuncios de compraventa de vivienda en Madrid con la información necesaria (precio, superficie, habitaciones, ubicación, tipo de inmueble) directamente visible en el HTML de cada anuncio, sin necesidad de renderizado JavaScript complejo ni de sistemas de bloqueo agresivos como los de Idealista.

- **Acceso:** scraping con `requests` + `BeautifulSoup` en Python. Existe ya un caso académico documentado (proyecto de la asignatura de Tipología y Ciclo de Vida de los Datos del Máster en Ciencia de Datos de la UOC) que extrae datos de estos mismos portales con esta misma técnica, lo que valida la viabilidad del enfoque para un proyecto académico.
- **Formato esperado:** HTML parseado a CSV/tabla estructurada.
- **Histórico disponible:** no; son anuncios activos en el momento de la extracción. Se mitigará con extracciones periódicas (semanales o quincenales) durante el curso.
- **Estabilidad:** razonablemente alta, aunque cualquier cambio en la estructura HTML del portal puede romper el scraper y requerir mantenimiento.
- **Riesgos detectados:** posible bloqueo por IP si se hacen demasiadas peticiones en poco tiempo (se mitigará con límites de velocidad/*rate limiting* y `User-Agent` adecuado, respetando el archivo `robots.txt`); posibles cambios en el HTML de la web que rompan el scraper; el precio es de oferta, no de cierre de venta.

### Fuente de enriquecimiento: Catastro (servicios web libres, sin certificado)

El Catastro ofrece, además de la descarga masiva que requiere certificado digital, **servicios web SOAP de consulta de datos no protegidos**, accesibles sin certificado ni registro, que permiten consultar superficie, año de construcción y uso de un inmueble a partir de su dirección (provincia, municipio, calle y número). Existen librerías Python que ya envuelven este servicio (`pycatastro`).

- **Acceso:** servicios web públicos SOAP, sin registro. Límite documentado de 3.600 peticiones/hora por IP.
- **Formato:** XML vía servicio web (parseable con `pycatastro` o directamente).
- **Histórico:** datos actuales del Catastro.
- **Estabilidad:** muy alta — servicio oficial mantenido por la Dirección General del Catastro.
- **Riesgos:** el cruce con los anuncios scrapeados se hará por dirección, no por una clave exacta común, lo que puede generar coincidencias erróneas o inmuebles sin enriquecer.

### Fuente de contexto/benchmark: Ministerio de Vivienda + INE

Se mantienen como fuentes de validación y contexto, **no como fuente de entrada al modelo**: permiten comprobar que los precios obtenidos por scraping están en un rango coherente con las estadísticas oficiales agregadas por distrito/barrio.

- **Acceso:** descarga directa en CSV/Excel, sin registro.
- **Histórico:** extenso (varios años, incluso décadas en algunas series del INE).
- **Estabilidad:** muy alta — fuentes oficiales del Gobierno de España.
- **Riesgo:** granularidad agregada (no por inmueble), por lo que no sustituyen a la fuente principal.

### Fuente de enriquecimiento geoespacial: OpenStreetMap + Overpass API

Sin cambios respecto a la versión anterior: API pública y gratuita, sin registro, para calcular variables de proximidad a partir de coordenadas.

---

## 4. Consideraciones de privacidad y protección de datos

- El proyecto trabaja con datos de inmuebles en oferta pública, no con datos de personas físicas identificables.
- Los anuncios de portales inmobiliarios pueden incluir el nombre o teléfono del anunciante (agencia o particular); estos campos **se excluirán explícitamente** del dataset, ya que no son necesarios para el modelo y constituyen datos personales bajo el RGPD si corresponden a un particular.
- El Catastro, a través del servicio libre utilizado, no proporciona datos de titularidad, por lo que no hay riesgo de exposición de datos personales por esta vía.
- El scraping se realizará respetando el archivo `robots.txt` de cada portal y aplicando límites de velocidad razonables, evitando cualquier interferencia con el funcionamiento del sitio.
- No se utilizarán los datos extraídos con fines comerciales ni se redistribuirán; su uso queda limitado al ámbito académico del curso.
- Se ha decidido evitar deliberadamente Idealista no solo por motivos de viabilidad técnica, sino porque su sistema de protección anti-bot indica una voluntad explícita de restringir el acceso automatizado, lo que se ha valorado como una señal a respetar.

---

## 5. Viabilidad inicial del proyecto

### ¿Es viable obtener los datos?

Sí, con alta confianza. La fuente principal (Pisos.com / Fotocasa) es accesible desde el primer día sin ningún proceso de aprobación, y existe precedente académico documentado de uso de esta técnica con estos mismos portales. El Catastro y las fuentes de contexto son de acceso inmediato y oficial.

### ¿Tiene suficiente calidad, granularidad y profundidad histórica?

La granularidad por inmueble individual está garantizada por el scraping. La profundidad histórica es la principal limitación: no existe forma de obtener precios de cierre históricos por inmueble de acceso público en España, por lo que el proyecto trabajará principalmente con una "foto" del mercado actual, complementada con el contexto histórico agregado del Ministerio de Vivienda e INE. Esta limitación se documentará explícitamente como alcance del proyecto.

### ¿Es realista desarrollarla durante el curso?

Sí. El scraping de un portal con HTML relativamente simple es una tarea abordable en las primeras semanas, y el resto del pipeline (limpieza, enriquecimiento geoespacial, modelado, dashboard) sigue la misma estructura ya planteada.

### ¿Qué parte es más arriesgada?

El mantenimiento del scraper si el portal elegido cambia su estructura HTML durante el curso, y el cruce por dirección entre los anuncios y los datos del Catastro, que no tiene una clave exacta común.

### Alternativa si la fuente principal no funciona

Si Pisos.com bloquea el acceso o cambia su estructura de forma que el scraper deje de funcionar, se cambiará a Fotocasa (mismo enfoque técnico) o, como última alternativa, se reducirá el alcance del proyecto a un dataset estático obtenido mediante una única extracción amplia al inicio del curso, sin actualizaciones periódicas, aceptando trabajar con una muestra fija en lugar de un flujo continuo de datos.
