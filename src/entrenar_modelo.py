import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib
import os

os.makedirs("data/model", exist_ok=True)

print("Cargando datos gold...")
df = pd.read_csv("data/gold/gold_anuncios.csv")
print(f"Filas: {len(df)}")

# Features y target
FEATURES = ["superficie_m2", "habitaciones", "banos", "distrito", "tipo_inmueble"]
TARGET = "precio_oferta"

df = df.dropna(subset=FEATURES + [TARGET])
print(f"Filas tras eliminar nulos en features: {len(df)}")

X = df[FEATURES]
y = df[TARGET]
grupos = df["id_anuncio"]

# Split agrupado por id_anuncio (evita leakage)
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(X, y, groups=grupos))

X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
print(f"Train: {len(X_train)} | Test: {len(X_test)}")

# Preprocesamiento
cat_features = ["distrito", "tipo_inmueble"]
num_features = ["superficie_m2", "habitaciones", "banos"]

preprocessor = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_features),
    ("num", "passthrough", num_features)
])

# --- BASELINE: mediana por distrito ---
mediana_distrito = y_train.groupby(X_train["distrito"]).median()
baseline_pred = X_test["distrito"].map(mediana_distrito).fillna(y_train.median())
mae_baseline = mean_absolute_error(y_test, baseline_pred)
print(f"\nBaseline (mediana por distrito):")
print(f"  MAE: {mae_baseline:,.0f} €")

# --- MODELO 1: Regresión Lineal ---
pipe_lr = Pipeline([
    ("prep", preprocessor),
    ("model", LinearRegression())
])
pipe_lr.fit(X_train, y_train)
pred_lr = pipe_lr.predict(X_test)
mae_lr = mean_absolute_error(y_test, pred_lr)
r2_lr  = r2_score(y_test, pred_lr)
print(f"\nRegresión Lineal:")
print(f"  MAE: {mae_lr:,.0f} €  |  R²: {r2_lr:.3f}")

# --- MODELO 2: Random Forest ---
pipe_rf = Pipeline([
    ("prep", preprocessor),
    ("model", RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1))
])
pipe_rf.fit(X_train, y_train)
pred_rf = pipe_rf.predict(X_test)
mae_rf = mean_absolute_error(y_test, pred_rf)
r2_rf  = r2_score(y_test, pred_rf)
print(f"\nRandom Forest:")
print(f"  MAE: {mae_rf:,.0f} €  |  R²: {r2_rf:.3f}")

# Mejora sobre baseline
mejora_lr = (mae_baseline - mae_lr) / mae_baseline * 100
mejora_rf = (mae_baseline - mae_rf) / mae_baseline * 100
print(f"\nMejora sobre baseline:")
print(f"  Regresión Lineal: {mejora_lr:.1f}%")
print(f"  Random Forest:    {mejora_rf:.1f}%")

# Seleccionar el mejor modelo
if mae_rf < mae_lr:
    mejor_modelo = pipe_rf
    nombre_modelo = "Random Forest"
    mae_final = mae_rf
    r2_final = r2_rf
else:
    mejor_modelo = pipe_lr
    nombre_modelo = "Regresión Lineal"
    mae_final = mae_lr
    r2_final = r2_lr

print(f"\nModelo seleccionado: {nombre_modelo}")
print(f"  MAE final: {mae_final:,.0f} €")
print(f"  R²:        {r2_final:.3f}")

# Importancia de variables (solo Random Forest)
feature_names = (
    pipe_rf.named_steps["prep"]
    .transformers_[0][1]
    .get_feature_names_out(cat_features).tolist()
    + num_features
)
importancias = pipe_rf.named_steps["model"].feature_importances_
imp_df = pd.DataFrame({"variable": feature_names, "importancia": importancias})
imp_df = imp_df.sort_values("importancia", ascending=False).head(10)
print(f"\nTop 10 variables más importantes (Random Forest):")
print(imp_df.to_string(index=False))

# Guardar modelo y metadatos
joblib.dump(mejor_modelo, "data/model/modelo.pkl")
joblib.dump(pipe_rf, "data/model/modelo_rf.pkl")

meta = {
    "modelo": nombre_modelo,
    "mae": round(mae_final),
    "r2": round(r2_final, 3),
    "mae_baseline": round(mae_baseline),
    "mejora_baseline_pct": round(mejora_rf if mae_rf < mae_lr else mejora_lr, 1),
    "n_train": len(X_train),
    "n_test": len(X_test),
    "fecha": "2026-09-26"
}
import json
with open("data/model/meta.json", "w") as f:
    json.dump(meta, f, indent=2)

print(f"\nModelo guardado en data/model/modelo.pkl")
print("Listo.")