# Datos necesarios

**Autor:** Juan José Romero  
**Entrega:** 2 — Selección de idea y análisis de datos  
**Proyecto:** Predicción de precios de vivienda en España

---

## 1. Idea seleccionada

**Predicción de precios de vivienda en España mediante modelos de regresión y análisis geoespacial.**

### Problema que resuelve

El mercado inmobiliario español presenta una opacidad estructural que dificulta la toma de decisiones tanto para compradores particulares como para inversores y entidades financieras. **Determinar si el precio de un inmueble es justo o está sobrevaluado requiere hoy un conocimiento experto o el acceso a herramientas de tasación profesional de coste elevado.** Esta asimetría de información penaliza especialmente a compradores sin experiencia, que representan la mayoría de las transacciones del mercado residencial. El problema es relevante en un contexto de escalada sostenida de precios en las principales ciudades españolas, donde la falta de transparencia genera ineficiencias tanto en el mercado de compraventa como en el de alquiler.

### Solución planteada

El proyecto abordará el problema desde un enfoque de Data Science supervisado, construyendo un modelo de regresión capaz de **estimar el precio de mercado de una vivienda a partir de sus características físicas, su localización y su entorno urbano.** Los datos de cada inmueble (superficie, año de construcción, número de habitaciones y tipo de uso) se complementarán con variables geoespaciales obtenidas a partir de OpenStreetMap: distancia a transporte público, proximidad a centros educativos, zonas verdes y servicios comerciales. Esta capa geoespacial es clave porque permite al modelo capturar el valor del entorno más allá de los metros cuadrados. El enfoque general consistirá en combinar fuentes de datos públicas oficiales con datos de oferta real del mercado para entrenar el modelo, y se explorarán algoritmos como regresión lineal múltiple, Random Forest y Gradient Boosting.

### MVP del proyecto final

El producto mínimo viable consistirá en un dashboard interactivo que permita introducir las características de una vivienda (municipio, superficie, número de habitaciones, año de construcción y proximidad a servicios clave) y obtenga una estimación de precio junto con un intervalo de confianza. El dashboard mostrará también un mapa de calor con la distribución de precios por zona geográfica y una visualización de las variables con mayor peso en la predicción. El modelo subyacente será evaluado con métricas estándar de regresión (RMSE, MAE y R²) y se presentará como un informe técnico reproducible. El proyecto demostrará, en suma, un flujo completo de Data Science: ingesta de datos, limpieza, feature engineering geoespacial, modelado y visualización.

---

## 2. Datos necesarios

### Variables e información requerida

Los datos del proyecto se pueden agrupar en dos bloques:

**Bloque A — Variables del inmueble (imprescindibles):**

- **Precio de venta o tasación** (variable objetivo del modelo)
- **Superficie construida** en m²
- **Número de habitaciones** y número de baños
- **Año de construcción** del inmueble
- **Tipo de inmueble** (piso, chalet, dúplex, estudio)
- **Dirección o coordenadas** (latitud/longitud) para geolocalizar
- **Municipio y provincia**

**Bloque B — Variables geoespaciales derivadas (deseables):**

- Distancia en metros a la **parada de metro o autobús más cercana**
- Distancia al **centro educativo más próximo** (colegio, instituto)
- Distancia a **zonas verdes o parques**
- Número de **servicios comerciales** en un radio de 500 m
- Distancia al **centro del municipio** (punto de referencia)

### Granularidad y profundidad histórica

**Granularidad:** a nivel de inmueble individual. Cada fila del dataset representará una vivienda con sus características y su precio.

**Profundidad histórica:** datos de los últimos 3-5 años para el modelo de precios de tasación; los datos geoespaciales de OpenStreetMap son actuales y se obtienen en el momento de la consulta.

**Volumen estimado:** entre 5.000 y 50.000 registros de viviendas es suficiente para entrenar un modelo robusto. La API de Idealista puede proporcionar varios miles de anuncios activos por ciudad.

### Datos imprescindibles vs. deseables

**Imprescindibles:** precio, superficie, municipio/coordenadas, número de habitaciones y año de construcción. Sin estas variables el modelo no puede construirse.

**Deseables pero no bloqueantes:** variables geoespaciales (distancias a servicios). Enriquecen el modelo y mejoran la precisión, pero el proyecto puede arrancar sin ellas y añadirlas como segunda fase.

---

## 3. Fuentes de datos previstas

### Fuente principal: Idealista API

Idealista es el mayor portal inmobiliario de España y proporciona datos reales de mercado (anuncios activos de compraventa) a través de una API oficial. Constituye la fuente más rica para obtener precio, superficie, habitaciones y ubicación de cada inmueble.

- **Acceso:** registro como desarrollador en [developers.idealista.com](https://developers.idealista.com). Idealista tiene un programa de acceso para proyectos de investigación y académicos; basta con solicitar API key y client secret indicando el contexto del proyecto.
- **Formato:** JSON via API REST
- **Histórico:** no disponible directamente (datos de anuncios activos), aunque existen repositorios en GitHub con extracciones históricas
- **Estabilidad:** alta — plataforma líder con API mantenida activamente
- **Riesgo principal:** la aprobación del acceso no es inmediata (puede tardar días o semanas). Como alternativa existe un cliente Python no oficial (`idealista-api` en GitHub) mientras se espera la API key.

### Fuente secundaria: Ministerio de Vivienda — valor tasado

El Ministerio de Vivienda y Agenda Urbana publica trimestralmente estadísticas de valor tasado de vivienda libre por municipio y tipología. Son datos agregados (no por inmueble individual) pero muy útiles para contextualizar y validar el modelo.

- **Acceso:** [mivau.gob.es — Observatorio de Vivienda y Suelo](https://www.mivau.gob.es/el-ministerio/observatorios-y-estadisticas) (sección Valor Tasado de la Vivienda)
- **Formato:** Excel / CSV, descarga directa sin registro
- **Histórico:** disponible desde 2004, serie temporal completa
- **Estabilidad:** muy alta — fuente oficial del Gobierno de España
- **Riesgo:** granularidad municipal (no por inmueble), por lo que no sustituye a Idealista para entrenar el modelo, pero es ideal para análisis exploratorio y benchmark.

### Fuente terciaria: Catastro — características físicas

La Sede Electrónica del Catastro ofrece una API REST pública que devuelve, para cualquier referencia catastral, la superficie construida, el año de construcción, el uso del inmueble y las coordenadas geográficas. Es la fuente más fiable para características físicas de inmuebles.

- **Acceso:** API libre en [sede.catastro.gob.es](https://sede.catastro.gob.es) — sin registro, sin límites estrictos documentados
- **Formato:** XML / JSON via API REST
- **Histórico:** datos actuales del Catastro (se actualiza con cada transmisión)
- **Estabilidad:** muy alta — servicio oficial del Ministerio de Hacienda
- **Riesgo:** el Catastro no incluye el precio de mercado (solo el valor catastral, que no equivale al precio de venta). Debe cruzarse con Idealista para tener precio real.

### Fuente de enriquecimiento geoespacial: OpenStreetMap + Overpass API

A través de su API Overpass se puede consultar, para cualquier coordenada, la ubicación de paradas de transporte, colegios, hospitales, parques y comercios en un radio determinado. Esto permite calcular las variables de proximidad que enriquecen el modelo.

- **Acceso:** API pública en [overpass-api.de](https://overpass-api.de) — gratuita, sin registro
- **Formato:** JSON / XML via API REST
- **Librería Python recomendada:** `OSMnx` o `geopy` — simplifican mucho las consultas geoespaciales
- **Histórico:** datos actuales (mapa actualizado por la comunidad en tiempo real)
- **Estabilidad:** alta — proyecto con millones de contribuidores activos
- **Riesgo:** calidad variable según la zona; en ciudades grandes los datos son muy completos, pero en municipios pequeños puede haber lagunas. Se mitigará limitando el análisis a ciudades con buena cobertura (Madrid, Barcelona, Sevilla, Valencia…).

---

## 4. Consideraciones de privacidad y protección de datos

El proyecto trabaja exclusivamente con datos de inmuebles, no con datos de personas físicas identificables. Se detallan a continuación las consideraciones relevantes:

- **Ausencia de datos personales directos:** los datos del Catastro no incluyen información sobre titulares (la API pública solo devuelve datos no protegidos). Los anuncios de Idealista identifican inmuebles, no propietarios.
- **Datos de geolocalización:** las coordenadas son de inmuebles en oferta pública, no de personas. No requieren anonimización.
- **Uso académico:** todas las fuentes utilizadas son abiertas o tienen acceso académico previsto. El Catastro y el Ministerio de Vivienda publican sus datos bajo licencias de reutilización de información pública (Ley 37/2007). La API de Idealista, una vez aprobado el acceso, permite uso para investigación.
- **Sin datos sensibles:** el proyecto no trabaja con categorías especiales de datos según el RGPD (salud, religión, ideología, etc.).
- **Riesgo ético bajo:** no existe riesgo de discriminación o sesgo que afecte directamente a personas, aunque se tendrá en cuenta el posible sesgo de representación geográfica (los datos de Idealista están sesgados hacia grandes ciudades).

---

## 5. Viabilidad inicial del proyecto

### ¿Es viable obtener los datos?

Sí, con alta probabilidad. Las fuentes del Ministerio de Vivienda y el Catastro son accesibles de inmediato, sin registro, en formatos estándar. La API de Idealista requiere aprobación previa pero tiene un canal documentado para proyectos académicos y cuenta con clientes Python en GitHub que permiten empezar incluso antes de tener acceso oficial. OpenStreetMap es completamente abierto y no presenta ninguna barrera de acceso.

### ¿Tienen suficiente calidad los datos?

El Catastro y el Ministerio de Vivienda son fuentes oficiales con alta fiabilidad. Idealista, como fuente de oferta real del mercado, es la referencia del sector para análisis inmobiliarios en España y ha sido utilizada en múltiples trabajos académicos y de investigación. OpenStreetMap tiene cobertura excelente en las principales ciudades españolas. La combinación de estas fuentes ofrece una calidad y granularidad más que suficientes para el propósito del proyecto.

### ¿Es realista desarrollarla durante el curso?

Sí. El proyecto tiene una estructura modular que permite avanzar por fases: primero datos del Ministerio para el análisis exploratorio, luego datos de Idealista para entrenar el modelo, y finalmente las variables geoespaciales de OpenStreetMap como mejora incremental. Es posible presentar un MVP funcional aunque alguna de las fases de enriquecimiento quede pendiente.

### ¿Qué parte es más arriesgada?

El principal riesgo es el tiempo de aprobación de la API de Idealista, que puede no ser inmediato. En segundo lugar, la integración de variables geoespaciales requiere conocimientos de programación algo más avanzados que tendré que estudiar por mi cuenta.

### Plan de contingencia

Si la API de Idealista no está disponible a tiempo, se utilizará el portal de datos abiertos del Ayuntamiento de Madrid ([datos.madrid.es](https://datos.madrid.es)), que publica datasets de vivienda con precio y características en formato CSV de descarga directa, sin necesidad de registro. Como segunda alternativa, el portal [datos.gob.es](https://datos.gob.es) agrega datasets de transacciones inmobiliarias de múltiples fuentes oficiales. Ninguno de estos escenarios alternativos requiere scraping ni acceso no autorizado.
