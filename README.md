# PrecioJusto Madrid

### Predicción de precio de oferta inmobiliario en Madrid



Proyecto final del Máster en Data Science — Juan José Romero



---



## ¿Qué hace este proyecto?



Aplicación web que estima el precio de oferta habitual de una vivienda en Madrid

a partir de sus características (distrito, superficie, habitaciones, baños),

basándose en anuncios reales extraídos de Fotocasa.



**Importante:** el modelo predice precio de oferta (lo que pide el vendedor),

no precio de cierre ni valor de tasación oficial.



---



## Resultados del modelo



| Métrica | Valor |

|---|---|

| Modelo | Random Forest |

| R² en test | 0.842 |

| MAE en test | 181.431 € |

| Mejora sobre baseline | 56.3% |

| Anuncios en el dataset | 478 |

| Fuente de datos | Fotocasa Madrid (sept. 2026) |


---



## Estructura del repositorio

ProyectoDataMaster/

├── data/

│ ├── processed/ # Datos limpios

│ └── gold/ # Dataset final para el modelo

├── src/

│ ├── limpiar\_datos.py # Pipeline de limpieza

│ ├── entrenar\_modelo.py # Entrenamiento del modelo

│ └── app.py # Dashboard Streamlit

└── docs/

└── entregas/ # Documentación del proyecto (entregas 1-5)




---



## Cómo ejecutar la app



```bash

pip install pandas scikit-learn streamlit plotly

python src/limpiar\_datos.py

python src/entrenar\_modelo.py

streamlit run src/app.py

```



---



## Tecnología utilizada



**Python** — pandas, scikit-learn, streamlit, plotly

**Fuente de datos** — Fotocasa (scraping vía Apify)

**Modelo** — Random Forest Regressor

**Alcance geográfico** — Madrid capital (21 distritos)

