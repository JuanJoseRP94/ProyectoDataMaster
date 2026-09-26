import streamlit as st
import pandas as pd
import joblib
import json
import plotly.express as px

st.set_page_config(page_title="PrecioJusto Madrid", page_icon="🏠", layout="wide")

@st.cache_resource
def cargar_modelo():
    return joblib.load("data/model/modelo.pkl")

@st.cache_data
def cargar_datos():
    return pd.read_csv("data/gold/gold_anuncios.csv")

@st.cache_data
def cargar_meta():
    with open("data/model/meta.json") as f:
        return json.load(f)

modelo = cargar_modelo()
df = cargar_datos()
meta = cargar_meta()

# --- CABECERA ---
st.title("🏠 PrecioJusto Madrid")
st.caption("Estimador de precio de oferta · Basado en anuncios reales de Fotocasa · Madrid capital")

col_aviso, _ = st.columns([3, 1])
with col_aviso:
    st.info("ℹ️ Este modelo estima el **precio de oferta** habitual para anuncios similares. "
            "No equivale al precio de cierre ni al valor de tasación oficial.")

st.divider()

# --- FORMULARIO + RESULTADOS ---
col_form, col_result = st.columns([1, 2])

with col_form:
    st.subheader("1. Características del anuncio")

    distritos = sorted(df["distrito"].dropna().unique().tolist())
    distrito = st.selectbox("Distrito", distritos)

    superficie = st.number_input("Superficie (m²)", min_value=15, max_value=1000, value=80)
    habitaciones = st.number_input("Habitaciones", min_value=1, max_value=10, value=3)
    banos = st.number_input("Baños", min_value=1, max_value=5, value=1)
    precio_anuncio = st.number_input("Precio del anuncio a evaluar (€)",
                                      min_value=0, max_value=10000000, value=0, step=10000)

    estimar = st.button("⚡ Estimar precio", type="primary", use_container_width=True)

with col_result:
    if estimar:
        entrada = pd.DataFrame([{
            "superficie_m2": superficie,
            "habitaciones": habitaciones,
            "banos": banos,
            "distrito": distrito,
            "tipo_inmueble": "piso"
        }])

        estimacion = modelo.predict(entrada)[0]

        # Intervalo aproximado basado en MAE
        mae = meta["mae"]
        intervalo_inf = max(0, estimacion - mae)
        intervalo_sup = estimacion + mae

        st.subheader("2. Resultado de la estimación")

        m1, m2, m3 = st.columns(3)
        m1.metric("Precio estimado", f"{estimacion:,.0f} €")
        m2.metric("Intervalo aproximado",
                  f"{intervalo_inf:,.0f} € – {intervalo_sup:,.0f} €")
        m3.metric("R² del modelo", f"{meta['r2']}")

        if precio_anuncio > 0:
            diferencia = precio_anuncio - estimacion
            pct = diferencia / estimacion * 100
            st.divider()
            if diferencia > 0:
                st.error(f"⬆️ El anuncio está **{pct:.1f}% por encima** del precio estimado "
                         f"({diferencia:,.0f} € más caro)")
            elif diferencia < 0:
                st.success(f"⬇️ El anuncio está **{abs(pct):.1f}% por debajo** del precio estimado "
                           f"({abs(diferencia):,.0f} € más barato)")
            else:
                st.success("✅ El precio del anuncio coincide exactamente con la estimación")

        st.divider()
        st.caption(f"Modelo: {meta['modelo']} · MAE en validación: {meta['mae']:,} € · "
                   f"Mejora sobre baseline: {meta['mejora_baseline_pct']}% · "
                   f"Datos: {len(df)} anuncios Fotocasa · Extracción: {meta['fecha']}")

    else:
        st.info("👈 Rellena las características del anuncio y pulsa **Estimar precio**")

st.divider()

# --- ANÁLISIS EXPLORATORIO ---
st.subheader("3. Análisis del mercado en Madrid")

tab1, tab2, tab3 = st.tabs(["Precio por distrito", "Precio vs superficie", "Distribución de precios"])

with tab1:
    resumen = df.groupby("distrito").agg(
        precio_medio=("precio_oferta", "mean"),
        n_anuncios=("id_anuncio", "count")
    ).reset_index().sort_values("precio_medio", ascending=True)

    fig1 = px.bar(resumen, x="precio_medio", y="distrito", orientation="h",
                  color="precio_medio", color_continuous_scale="Blues",
                  labels={"precio_medio": "Precio medio (€)", "distrito": "Distrito"},
                  title="Precio medio de oferta por distrito")
    fig1.update_layout(showlegend=False, height=500)
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    fig2 = px.scatter(df, x="superficie_m2", y="precio_oferta",
                      color="distrito", hover_data=["habitaciones", "banos"],
                      labels={"superficie_m2": "Superficie (m²)",
                              "precio_oferta": "Precio de oferta (€)"},
                      title="Relación entre superficie y precio de oferta")
    fig2.update_layout(height=450)
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    fig3 = px.histogram(df, x="precio_oferta", nbins=40,
                        labels={"precio_oferta": "Precio de oferta (€)"},
                        title="Distribución de precios de oferta en Madrid")
    fig3.update_layout(height=400)
    st.plotly_chart(fig3, use_container_width=True)