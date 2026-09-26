import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from features import (
    ANTIGUEDAD,
    ROOT,
    SOL_LAT,
    SOL_LON,
    distancia_minima_m,
    euros,
    geocodificar,
    haversine_m,
)

MODELO_PATH = ROOT / "data" / "model" / "modelo.pkl"
META_PATH = ROOT / "data" / "model" / "meta.json"
GOLD_PATH = ROOT / "data" / "gold" / "gold_anuncios.csv"
METRO_PATH = ROOT / "data" / "processed" / "metro_madrid.csv"

ETIQUETAS_ANTIGUEDAD = ["No la sé"] + [ANTIGUEDAD[i][0] for i in range(1, 10)]
ANOS_POR_ETIQUETA = {ANTIGUEDAD[i][0]: ANTIGUEDAD[i][1] for i in range(1, 10)}


st.set_page_config(page_title="PrecioJusto Madrid", page_icon="🏠", layout="wide")


@st.cache_resource
def cargar_modelo():
    import joblib
    import features  # noqa: F401  (hace falta para abrir el modelo guardado)
    return joblib.load(MODELO_PATH)


@st.cache_data
def cargar_datos():
    return pd.read_csv(GOLD_PATH)


@st.cache_data
def cargar_meta():
    return json.loads(META_PATH.read_text(encoding="utf-8"))


@st.cache_data
def cargar_metro():
    return pd.read_csv(METRO_PATH)


def buscar_anuncios_parecidos(df: pd.DataFrame, distrito: str, superficie: float) -> pd.DataFrame:
    zona = df[df["distrito"] == distrito].copy()
    zona["diferencia_m2"] = (zona["superficie_m2"] - superficie).abs()
    margen = max(15, superficie * 0.25)
    cercanos = zona[zona["diferencia_m2"] <= margen]
    pool = cercanos if len(cercanos) >= 3 else zona
    return pool.sort_values("diferencia_m2")


def confianza(n_distrito: int, n_parecidos: int) -> tuple[str, str]:
    if n_distrito < 15 or n_parecidos < 5:
        return (
            "Baja",
            "Hay pocos anuncios comparables en esta zona. Toma la cifra solo como orientación.",
        )
    if n_distrito < 40:
        return (
            "Media",
            "Hay anuncios en este distrito, pero no los suficientes para afinar mucho.",
        )
    return (
        "Alta",
        "Hay bastantes anuncios parecidos en este distrito.",
    )


@st.cache_data(show_spinner=False)
def buscar_calle(consulta: str):
    return geocodificar(consulta)


def localizar(calle: str, distrito: str, metro: pd.DataFrame, mediana_metro: float, mediana_sol: float):
    if not calle.strip():
        return mediana_metro, mediana_sol, "Sin calle, uso la distancia al metro típica de este distrito."

    # Si la calle no está en el distrito elegido, se busca en Madrid entero.
    consultas = [
        f"{calle}, {distrito}, Madrid, España",
        f"{calle}, Madrid, España",
    ]
    geo = None
    with st.spinner("Buscando la calle en Madrid..."):
        for consulta in consultas:
            try:
                candidato = buscar_calle(consulta)
            except Exception:
                candidato = None
            dentro = (
                candidato is not None
                and 40.30 <= candidato["lat"] <= 40.60
                and -3.95 <= candidato["lon"] <= -3.45
            )
            if dentro:
                geo = candidato
                break

    if geo is None:
        return (
            mediana_metro,
            mediana_sol,
            "No he encontrado esa calle dentro de Madrid. Uso la distancia típica del distrito.",
        )

    dist_metro = distancia_minima_m(geo["lat"], geo["lon"], metro)
    dist_sol = float(haversine_m(geo["lat"], geo["lon"], SOL_LAT, SOL_LON))
    texto = f"Calle localizada. El metro más cercano queda a unos {dist_metro:,.0f} m.".replace(",", ".")
    return dist_metro, dist_sol, texto


def grafico_rango(bajo, estimacion, alto, precio):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[bajo, alto],
        y=[1, 1],
        mode="lines",
        line=dict(color="#9bb8d3", width=14),
        hoverinfo="skip",
        showlegend=False,
    ))
    marcas_x = [estimacion]
    marcas_y = [1]
    textos = ["Estimación"]
    colores = ["#1f4b99"]
    if precio and precio > 0:
        marcas_x.append(precio)
        marcas_y.append(1)
        textos.append("Tu anuncio")
        colores.append("#b45309")
    fig.add_trace(go.Scatter(
        x=marcas_x,
        y=marcas_y,
        mode="markers+text",
        marker=dict(size=16, color=colores),
        text=textos,
        textposition="top center",
        showlegend=False,
        hovertemplate="%{x:,.0f} €<extra></extra>",
    ))
    fig.update_layout(
        height=160,
        margin=dict(l=10, r=10, t=28, b=10),
        xaxis_title=None,
        yaxis=dict(visible=False),
        separators=".,",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(tickformat=",")
    return fig


if not MODELO_PATH.exists() or not META_PATH.exists() or not GOLD_PATH.exists():
    st.error("Faltan el modelo o los datos. Desde la carpeta del proyecto ejecuta "
             "`python src/limpiar_datos.py` y después `python src/entrenar_modelo.py`.")
    st.stop()

modelo = cargar_modelo()
df = cargar_datos()
meta = cargar_meta()
metro = cargar_metro()

st.title("PrecioJusto Madrid")
st.caption("Para saber si el precio de un piso en venta está dentro de lo que se pide ahora mismo en ese distrito.")
st.info(
    "La referencia es el **precio de oferta**: lo que piden los anuncios parecidos en Fotocasa. "
    "No es el precio al que se acaba firmando, ni una tasación."
)

distritos = sorted(df["distrito"].dropna().unique().tolist())
mediana_metro = df.groupby("distrito")["dist_metro_m"].median()
mediana_sol = df.groupby("distrito")["dist_sol_m"].median()
mediana_m2_distrito = df.groupby("distrito")["precio_por_m2"].median()
mediana_m2_ciudad = float(df["precio_por_m2"].median())

col_form, col_result = st.columns([1, 1.35], gap="large")

with col_form:
    st.subheader("El piso que estás mirando")
    distrito = st.selectbox("Distrito", distritos, index=distritos.index("Centro") if "Centro" in distritos else 0)
    superficie = st.number_input("Superficie (m²)", min_value=20, max_value=500, value=80, step=1)
    habitaciones = st.number_input("Habitaciones", min_value=1, max_value=10, value=3, step=1)
    banos = st.number_input("Baños", min_value=1, max_value=6, value=1, step=1)
    tipos = sorted(df["tipo_inmueble"].dropna().unique().tolist())
    tipo = st.selectbox("Tipo de inmueble", tipos, index=tipos.index("Piso") if "Piso" in tipos else 0)
    antiguedad = st.selectbox("Antigüedad", ETIQUETAS_ANTIGUEDAD)
    calle = st.text_input("Calle (opcional)", placeholder="Ej. Calle de Alcalá 50")
    precio_anuncio = st.number_input(
        "Precio que piden en el anuncio (€)",
        min_value=0,
        max_value=10_000_000,
        value=0,
        step=5000,
        help="Déjalo en 0 si solo quieres una referencia, sin comparar un anuncio concreto.",
    )

dist_metro, dist_sol, nota_ubicacion = localizar(
    calle, distrito, metro,
    float(mediana_metro.get(distrito, df["dist_metro_m"].median())),
    float(mediana_sol.get(distrito, df["dist_sol_m"].median())),
)

anos = ANOS_POR_ETIQUETA.get(antiguedad, np.nan)
fila = {
    "superficie_m2": float(superficie),
    "habitaciones": float(habitaciones),
    "banos": float(banos),
    "distrito": distrito,
    "antiguedad_anos": anos,
    "dist_metro_m": float(dist_metro),
    "dist_sol_m": float(dist_sol),
}
if "tipo_inmueble" in meta["columnas"]:
    fila["tipo_inmueble"] = tipo

entrada = pd.DataFrame([fila])
estimacion = float(np.clip(modelo.predict(entrada[meta["columnas"]])[0], 0, None))

parecidos = buscar_anuncios_parecidos(df, distrito, float(superficie))
muestra_rango = parecidos if len(parecidos) >= 8 else df[df["distrito"] == distrito]
p25 = float(muestra_rango["precio_por_m2"].quantile(0.25))
p75 = float(muestra_rango["precio_por_m2"].quantile(0.75))
rango_bajo = p25 * float(superficie)
rango_alto = p75 * float(superficie)
n_distrito = int((df["distrito"] == distrito).sum())
nivel, texto_confianza = confianza(n_distrito, len(parecidos))
eur_m2_zona = float(mediana_m2_distrito.get(distrito, mediana_m2_ciudad))

with col_result:
    st.subheader("Referencia de precio")
    st.metric("Se suele pedir", euros(estimacion))
    st.plotly_chart(
        grafico_rango(rango_bajo, estimacion, rango_alto, precio_anuncio),
        width="stretch",
        config={"displayModeBar": False},
    )

    if precio_anuncio > 0:
        if precio_anuncio > rango_alto:
            diferencia = (precio_anuncio - estimacion) / estimacion * 100
            detalle = (
                f"Queda un {diferencia:.0f}% por encima de la referencia ({euros(estimacion)})."
                if diferencia >= 1
                else f"La referencia del modelo es {euros(estimacion)}."
            )
            st.error(
                f"Por encima de lo habitual. En {distrito}, un piso de este tamaño se mueve "
                f"entre {euros(rango_bajo)} y {euros(rango_alto)}. Este anuncio pide "
                f"{euros(precio_anuncio)}. {detalle}"
            )
        elif precio_anuncio < rango_bajo:
            diferencia = (estimacion - precio_anuncio) / estimacion * 100
            detalle = (
                f"Queda un {diferencia:.0f}% por debajo de la referencia ({euros(estimacion)})."
                if diferencia >= 1
                else f"La referencia del modelo es {euros(estimacion)}."
            )
            st.success(
                f"Por debajo de lo habitual. En {distrito}, un piso de este tamaño se mueve "
                f"entre {euros(rango_bajo)} y {euros(rango_alto)}. Este anuncio pide "
                f"{euros(precio_anuncio)}. {detalle} "
                f"Conviene mirar por qué: planta, estado, o un anuncio mal puesto."
            )
        else:
            st.info(
                f"En rango. {euros(precio_anuncio)} entra en lo que se pide ahora mismo "
                f"por un piso de este tamaño en {distrito} "
                f"({euros(rango_bajo)} – {euros(rango_alto)})."
            )
    else:
        st.caption("Escribe el precio del anuncio para ver si está por encima o por debajo de lo habitual.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Rango habitual", f"{euros(rango_bajo)} – {euros(rango_alto)}")
    c2.metric("Confianza", nivel)
    c3.metric("€/m² en el distrito", f"{eur_m2_zona:,.0f}".replace(",", "."))
    if nivel == "Baja":
        st.warning(texto_confianza)
    else:
        st.caption(texto_confianza)
    st.caption(nota_ubicacion)
    st.caption(
        f"En la mitad central de los anuncios parecidos de {distrito} se piden "
        f"entre {euros(p25).removesuffix(' €')} y {euros(p75).removesuffix(' €')} €/m². "
        f"En el conjunto de Madrid, la mediana es {euros(mediana_m2_ciudad).removesuffix(' €')} €/m²."
    )

st.divider()
st.subheader("Anuncios parecidos ahora mismo en Fotocasa")
st.caption("Mismo distrito y superficie cercana. Son anuncios reales, no ejemplos inventados.")

tabla = parecidos.head(5).copy()
tabla["Superficie"] = tabla["superficie_m2"].map(lambda v: f"{v:.0f} m²")
tabla["Hab."] = tabla["habitaciones"].map(lambda v: "—" if pd.isna(v) else f"{v:.0f}")
tabla["Baños"] = tabla["banos"].map(lambda v: "—" if pd.isna(v) else f"{v:.0f}")
tabla["Precio"] = tabla["precio_oferta"].map(euros)
tabla["€/m²"] = tabla["precio_por_m2"].map(lambda v: f"{v:,.0f}".replace(",", "."))
tabla["Antigüedad"] = tabla["antiguedad"].fillna("Sin dato")
tabla["Anuncio"] = tabla["url"]
st.dataframe(
    tabla[["Superficie", "Hab.", "Baños", "Precio", "€/m²", "Antigüedad", "Anuncio"]],
    column_config={"Anuncio": st.column_config.LinkColumn("Anuncio", display_text="Ver en Fotocasa")},
    hide_index=True,
    width="stretch",
)

mapa = parecidos.head(40)
fig_mapa = px.scatter_map(
    mapa,
    lat="latitud",
    lon="longitud",
    color="precio_por_m2",
    size="superficie_m2",
    hover_data={"precio_oferta": ":.0f", "superficie_m2": ":.0f", "latitud": False, "longitud": False},
    color_continuous_scale="Blues",
    zoom=12,
    height=420,
    labels={"precio_por_m2": "€/m²"},
)
fig_mapa.update_layout(map_style="open-street-map", margin=dict(l=0, r=0, t=0, b=0))
st.plotly_chart(fig_mapa, width="stretch")

st.subheader("De qué depende el precio")
pesos = pd.DataFrame(meta["importancias"])
fig_pesos = px.bar(
    pesos,
    x="peso",
    y="variable",
    orientation="h",
    labels={"peso": "Peso en la estimación", "variable": ""},
)
fig_pesos.update_layout(
    showlegend=False,
    height=320,
    yaxis={"categoryorder": "total ascending"},
    xaxis_tickformat=".0%",
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(fig_pesos, width="stretch")
principales = ", ".join(pesos["variable"].head(3).str.lower())
st.caption(f"Lo que más mueve el precio es {principales}.")

with st.expander("Ver cómo está el mercado en Madrid"):
    resumen = (
        df.groupby("distrito", as_index=False)
        .agg(precio_medio=("precio_oferta", "median"), n_anuncios=("id_anuncio", "count"))
        .sort_values("precio_medio")
    )
    fig1 = px.bar(
        resumen, x="precio_medio", y="distrito", orientation="h",
        color="precio_medio", color_continuous_scale="Blues",
        labels={"precio_medio": "Precio mediano (€)", "distrito": "Distrito"},
        title="Precio mediano de oferta por distrito",
        hover_data=["n_anuncios"],
    )
    fig1.update_layout(showlegend=False, height=560, separators=".,")
    st.plotly_chart(fig1, width="stretch")

    fig2 = px.scatter(
        df, x="superficie_m2", y="precio_oferta", color="distrito",
        hover_data=["habitaciones", "banos"],
        labels={"superficie_m2": "Superficie (m²)", "precio_oferta": "Precio de oferta (€)"},
        title="Superficie y precio de oferta",
    )
    fig2.update_layout(height=460, separators=".,")
    st.plotly_chart(fig2, width="stretch")

with st.expander("Sobre esta referencia"):
    st.write(
        f"En anuncios que el modelo no usó para entrenarse, el desvío medio es del "
        f"**{meta['mape']}%** (unos {euros(meta['mae'])}). "
        "La cifra en euros crece con los pisos caros; el porcentaje describe mejor un piso normal."
    )
    st.write(
        f"Multiplicar los metros por el €/m² mediano del distrito ya es una referencia útil. "
        f"En el test, el modelo la mejora un **{meta['mejora_baseline_m2_pct']}%**. "
        "La diferencia es pequeña porque hay pocos anuncios y varios distritos están casi vacíos. "
        "Por eso la tabla de arriba enseña pisos reales, no solo una cifra."
    )
    st.write(
        f"Muestra: {meta['n_total']} anuncios de Fotocasa en Madrid capital, extracción del {meta['fecha']}. "
        "Precio de oferta, no precio de compra ni tasación."
    )
