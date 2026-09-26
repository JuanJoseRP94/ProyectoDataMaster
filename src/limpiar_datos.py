"""Deja el CSV de Fotocasa listo para entrenar.

Usa el export más reciente de Apify en data/raw (dataset_fotocasa*.csv).
Si no hay, lee data/raw/fotocasa_madrid_raw.csv y, en último caso, el processed.
"""

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from features import (
    ROOT,
    antiguedad_a_anos,
    cargar_metro,
    enriquecer_distancias,
    etiqueta_antiguedad,
    etiqueta_tipo,
    normalizar_distrito,
)

RAW = ROOT / "data" / "raw" / "fotocasa_madrid_raw.csv"
PROCESSED = ROOT / "data" / "processed" / "fotocasa_processed.csv"
GOLD = ROOT / "data" / "gold" / "gold_anuncios.csv"

# Nombres que salen del actor de Apify y nombres ya limpios.
RENOMBRES = {
    "propertyId": "id_anuncio",
    "transaction/price": "precio_oferta",
    "price": "precio_oferta",
    "surface": "superficie_m2",
    "rooms": "habitaciones",
    "baths": "banos",
    "location/level7Name": "distrito",
    "location/level5Name": "municipio",
    "location/level8Name": "barrio",
    "zipCode": "codigo_postal",
    "url": "url",
    "link": "url",
    "publicationDate": "fecha_publicacion",
    "location/latitude": "latitud",
    "location/longitude": "longitud",
    "latitude": "latitud",
    "longitude": "longitud",
    "antiquity": "antiguedad_codigo",
    "antiguedad": "antiguedad_codigo",
    "street": "calle",
    "propertySubtype": "subtipo_codigo",
}


def cargar_origen() -> tuple[pd.DataFrame, str]:
    raw_dir = ROOT / "data" / "raw"
    candidatos = sorted(raw_dir.glob("dataset_fotocasa*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if candidatos:
        print(f"Leyendo extracción de Apify: {candidatos[0].name}")
        return pd.read_csv(candidatos[0], low_memory=False), "raw"
    if RAW.exists():
        print(f"Leyendo extracción de Apify: {RAW.name}")
        return pd.read_csv(RAW, low_memory=False), "raw"
    if PROCESSED.exists():
        print(f"No hay CSV nuevo en data/raw. Uso {PROCESSED.name}")
        return pd.read_csv(PROCESSED, low_memory=False), "processed"
    raise FileNotFoundError(
        "No encuentro datos. Deja el CSV de Apify en data/raw."
    )


def estandarizar(df: pd.DataFrame) -> pd.DataFrame:
    # Si el export trae precio en dos columnas, nos quedamos con la de la transacción.
    if "transaction/price" in df.columns and "price" in df.columns:
        df = df.drop(columns=["price"])
    presentes = {k: v for k, v in RENOMBRES.items() if k in df.columns}
    df = df.rename(columns=presentes)
    df = df.loc[:, ~df.columns.duplicated()]
    return df


def main():
    df, origen = cargar_origen()
    print(f"Filas de entrada: {len(df)}")
    df = estandarizar(df)

    imprescindibles = ["id_anuncio", "precio_oferta", "superficie_m2", "distrito", "latitud", "longitud"]
    faltan = [c for c in imprescindibles if c not in df.columns]
    if faltan:
        raise SystemExit(f"Al CSV le faltan columnas imprescindibles: {faltan}")

    for col in ["precio_oferta", "superficie_m2", "habitaciones", "banos", "latitud", "longitud", "antiguedad_codigo"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["distrito"] = df["distrito"].map(normalizar_distrito)
    antes = len(df)
    df = df.dropna(subset=["distrito"])
    print(f"Fuera de los 21 distritos de Madrid capital: {antes - len(df)}")

    df["antiguedad_anos"] = df["antiguedad_codigo"].map(antiguedad_a_anos) if "antiguedad_codigo" in df.columns else float("nan")
    df["antiguedad"] = df["antiguedad_codigo"].map(etiqueta_antiguedad) if "antiguedad_codigo" in df.columns else None

    if "subtipo_codigo" in df.columns:
        df["subtipo_codigo"] = pd.to_numeric(df["subtipo_codigo"], errors="coerce")
        df["tipo_inmueble"] = df["subtipo_codigo"].map(etiqueta_tipo)
    elif "tipo_inmueble" not in df.columns:
        df["tipo_inmueble"] = "Piso"
    antes = len(df)
    df = df.dropna(subset=["tipo_inmueble"])
    print(f"Casas, chalets o tipos que no son piso: {antes - len(df)}")

    if "fecha_extraccion" not in df.columns:
        df["fecha_extraccion"] = "2026-09-26"

    df = df.drop_duplicates(subset=["id_anuncio"], keep="first")

    antes = len(df)
    df = df.dropna(subset=["precio_oferta", "superficie_m2", "latitud", "longitud"])
    print(f"Sin precio, superficie o coordenadas: {antes - len(df)}")

    # Topes fijos de un piso en Madrid. No se calculan sobre el propio dataset,
    # para no usar el precio (la variable objetivo) al decidir qué entra en test.
    antes = len(df)
    df = df[(df["precio_oferta"] >= 50_000) & (df["precio_oferta"] <= 5_000_000)]
    df = df[(df["superficie_m2"] >= 20) & (df["superficie_m2"] <= 500)]
    df = df[df["latitud"].between(40.30, 40.60) & df["longitud"].between(-3.95, -3.45)]
    df["precio_por_m2"] = df["precio_oferta"] / df["superficie_m2"]
    df = df[(df["precio_por_m2"] >= 1_500) & (df["precio_por_m2"] <= 22_000)]
    print(f"Descartados por estar fuera del rango de un piso en Madrid: {antes - len(df)}")
    conteo = df["tipo_inmueble"].value_counts()
    raros = conteo[conteo < 8].index
    if len(raros):
        print(f"Tipos con menos de 8 anuncios, agrupados como Piso: {list(raros)}")
        df.loc[df["tipo_inmueble"].isin(raros), "tipo_inmueble"] = "Piso"

    print("Descargando estaciones de metro (OpenStreetMap)...")
    metro = cargar_metro()
    print(f"Estaciones de metro: {len(metro)}")
    df = enriquecer_distancias(df, metro)

    df["anuncios_distrito"] = df.groupby("distrito")["id_anuncio"].transform("count")

    columnas = [
        "id_anuncio", "precio_oferta", "superficie_m2", "habitaciones", "banos",
        "distrito", "codigo_postal", "url", "fecha_publicacion", "latitud", "longitud",
        "antiguedad_codigo", "antiguedad", "antiguedad_anos", "calle",
        "fecha_extraccion", "tipo_inmueble", "precio_por_m2",
        "dist_metro_m", "dist_sol_m", "anuncios_distrito",
    ]
    if "barrio" in df.columns:
        columnas.insert(6, "barrio")
    columnas = [c for c in columnas if c in df.columns]

    GOLD.parent.mkdir(parents=True, exist_ok=True)
    df[columnas].to_csv(GOLD, index=False)

    if origen == "raw":
        PROCESSED.parent.mkdir(parents=True, exist_ok=True)
        df[columnas].to_csv(PROCESSED, index=False)
        print(f"Processed actualizado: {PROCESSED}")

    print(f"\nGold guardado: {len(df)} filas -> {GOLD}")
    print(f"  Precio mediano:   {df['precio_oferta'].median():,.0f} €")
    print(f"  €/m² mediano:     {df['precio_por_m2'].median():,.0f}")
    print(f"  Metro, mediana:   {df['dist_metro_m'].median():,.0f} m")
    print(f"  Con antigüedad:   {df['antiguedad_anos'].notna().sum()} de {len(df)}")
    print(f"  Distritos:        {df['distrito'].nunique()}")
    print("\nAnuncios por distrito:")
    print(df["distrito"].value_counts().to_string())


if __name__ == "__main__":
    main()
