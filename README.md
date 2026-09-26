# PrecioJusto Madrid

Estimador de precio de oferta de pisos en Madrid capital, para un comprador que quiere saber si un anuncio está dentro de lo habitual.

Proyecto final del Máster en Data Science — Juan José Romero.

La cifra es el **precio de oferta** (lo que se pide en Fotocasa), no el precio de firma ni una tasación.

## Qué hace la aplicación

El usuario indica distrito, superficie, habitaciones, baños y, si los conoce, la antigüedad y la calle. La aplicación devuelve:

- una referencia de precio
- el rango en el que se mueve la mitad central de los anuncios parecidos de ese distrito
- si el anuncio concreto está por encima, en rango o por debajo
- pisos reales comparables, con enlace a Fotocasa
- la confianza de la zona (alta, media o baja según cuántos anuncios hay)

## Resultados del modelo

Entrenado con anuncios que el modelo no ve en el test (20 %, separado por anuncio).

| Métrica | Valor |
|---|---|
| Modelo | Gradient Boosting sobre el precio en logaritmo |
| Error medio en test | 18,5 % (MAE 131.046 €) |
| R² en test | 0,897 |
| Baseline: mediana de precio del distrito | MAE 350.850 € |
| Baseline: €/m² mediano del distrito × superficie | MAE 151.661 € |
| Mejora frente a ese baseline de €/m² | 13,6 % |
| Anuncios | 3.823 pisos (sin casas ni chalets), de 4.000 descargados |
| Fuente | Fotocasa, Madrid capital, septiembre 2026 |

La mejora frente al €/m² del distrito es pequeña: varios distritos tienen muy pocos anuncios. Por eso la aplicación enseña los comparables, no solo la cifra del modelo. Lo que más mueve el €/m² es la cercanía al centro, el distrito y la cercanía al metro.

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
python src/limpiar_datos.py
python src/entrenar_modelo.py
streamlit run src/app.py
```

Si hay un CSV nuevo de Apify en `data/raw/fotocasa_madrid_raw.csv`, la limpieza usa ese archivo. Si no, usa el dataset ya procesado.

## Estructura

```
src/features.py          reglas compartidas, metro y formato
src/limpiar_datos.py     limpieza, distritos y distancia al metro
src/entrenar_modelo.py   comparación de modelos y modelo guardado
src/app.py               aplicación
data/gold/               dataset de entrenamiento
data/processed/          estaciones de metro (OpenStreetMap)
docs/entregas/           documentación del curso
```

## Tecnología

Python, pandas, scikit-learn, Streamlit y Plotly. Anuncios de Fotocasa vía Apify. Distancias al metro calculadas con OpenStreetMap (Overpass), sin coste. Alcance: Madrid capital, 21 distritos.
