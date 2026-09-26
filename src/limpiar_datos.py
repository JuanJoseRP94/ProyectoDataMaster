import pandas as pd
import os

RAW = "data/raw/fotocasa_madrid_raw.csv"
PROCESSED = "data/processed/fotocasa_processed.csv"
GOLD = "data/gold/gold_anuncios.csv"

os.makedirs("data/processed", exist_ok=True)
os.makedirs("data/gold", exist_ok=True)

print("Cargando datos...")
df = pd.read_csv(RAW, low_memory=False)
print(f"Filas originales: {len(df)}")

# Seleccionar columnas con nombres exactos del CSV
columnas = {
    "propertyId":           "id_anuncio",
    "transaction/price":    "precio_oferta",
    "surface":              "superficie_m2",
    "rooms":                "habitaciones",
    "baths":                "banos",
    "location/level7Name":  "distrito",
    "zipCode":              "codigo_postal",
    "url":                  "url",
    "publicationDate":      "fecha_publicacion",
    "location/latitude":    "latitud",
    "location/longitude":   "longitud",
    "antiquity":            "antiguedad",
    "street":               "calle",
}

cols_disponibles = {k: v for k, v in columnas.items() if k in df.columns}
df = df[list(cols_disponibles.keys())].rename(columns=cols_disponibles)

print(f"Columnas seleccionadas: {list(df.columns)}")

# --- CAPA PROCESSED ---
df["precio_oferta"] = pd.to_numeric(df["precio_oferta"], errors="coerce")
df["superficie_m2"] = pd.to_numeric(df["superficie_m2"], errors="coerce")
df["habitaciones"]  = pd.to_numeric(df["habitaciones"], errors="coerce")
df["banos"]         = pd.to_numeric(df["banos"], errors="coerce")

df["fecha_extraccion"] = "2026-09-26"
df["tipo_inmueble"] = "piso"

df.to_csv(PROCESSED, index=False)
print(f"Processed guardado: {len(df)} filas -> {PROCESSED}")

# --- CAPA GOLD ---
antes = len(df)
df = df.dropna(subset=["precio_oferta", "superficie_m2", "distrito"])
print(f"Filas eliminadas por nulos en campos clave: {antes - len(df)}")

df = df[(df["precio_oferta"] >= 30000) & (df["precio_oferta"] <= 5000000)]
df = df[df["superficie_m2"] >= 15]

df["precio_por_m2"] = df["precio_oferta"] / df["superficie_m2"]
p1  = df["precio_por_m2"].quantile(0.01)
p99 = df["precio_por_m2"].quantile(0.99)
antes = len(df)
df = df[(df["precio_por_m2"] >= p1) & (df["precio_por_m2"] <= p99)]
print(f"Filas eliminadas por outliers: {antes - len(df)}")

df["habitaciones"] = df["habitaciones"].fillna(df["habitaciones"].median())
df["banos"]        = df["banos"].fillna(df["banos"].median())
df["distrito"] = df["distrito"].astype(str).str.strip().str.title()
df["anuncios_distrito"] = df.groupby("distrito")["id_anuncio"].transform("count")

df.to_csv(GOLD, index=False)
print(f"\nGold guardado: {len(df)} filas -> {GOLD}")
print(f"\nResumen del dataset gold:")
print(f"  Precio medio:    {df['precio_oferta'].mean():,.0f} €")
print(f"  Precio mediana:  {df['precio_oferta'].median():,.0f} €")
print(f"  Superficie media: {df['superficie_m2'].mean():.0f} m²")
print(f"  Distritos únicos: {df['distrito'].nunique()}")
print(f"\nTop 10 distritos:")
print(df['distrito'].value_counts().head(10))