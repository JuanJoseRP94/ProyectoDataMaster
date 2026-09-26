"""Compara varios modelos y guarda el que menos se equivoca en validación cruzada."""

from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
import joblib

sys.path.insert(0, str(Path(__file__).resolve().parent))

from features import FEATURES_CAT, FEATURES_NUM, NOMBRES_VARIABLES, ROOT, ModeloPrecioM2

GOLD = ROOT / "data" / "gold" / "gold_anuncios.csv"
MODEL_DIR = ROOT / "data" / "model"


def columnas_modelo(df: pd.DataFrame) -> list[str]:
    cat = list(FEATURES_CAT)
    if "tipo_inmueble" in df.columns and df["tipo_inmueble"].nunique(dropna=True) > 1:
        cat.append("tipo_inmueble")
    return FEATURES_NUM + cat


def hacer_preprocesador(columnas: list[str]) -> ColumnTransformer:
    cat = [c for c in columnas if c in ("distrito", "tipo_inmueble")]
    num = [c for c in columnas if c not in cat]
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat),
        ("num", SimpleImputer(strategy="median"), num),
    ])


def bosque():
    return RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=3,
        max_features=0.6,
        random_state=42,
        n_jobs=-1,
    )


def candidatos(columnas: list[str]) -> dict:
    def tubo(modelo):
        return Pipeline([
            ("prep", hacer_preprocesador(columnas)),
            ("model", modelo),
        ])

    rf = tubo(bosque())
    return {
        "Regresión lineal (precio en log)": TransformedTargetRegressor(
            regressor=tubo(LinearRegression()),
            func=np.log1p,
            inverse_func=np.expm1,
        ),
        "Random Forest": rf,
        "Random Forest (precio en log)": TransformedTargetRegressor(
            regressor=tubo(bosque()),
            func=np.log1p,
            inverse_func=np.expm1,
        ),
        "Gradient Boosting (precio en log)": TransformedTargetRegressor(
            regressor=tubo(HistGradientBoostingRegressor(
                max_depth=4,
                learning_rate=0.06,
                max_iter=300,
                min_samples_leaf=8,
                l2_regularization=1.0,
                random_state=42,
            )),
            func=np.log1p,
            inverse_func=np.expm1,
        ),
        "Random Forest (€/m² × superficie)": ModeloPrecioM2(pipeline=tubo(bosque())),
    }


def mape(y_real, y_pred) -> float:
    y_real = np.asarray(y_real, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_real - y_pred) / y_real) * 100)


def nombre_variable(feature: str) -> str:
    if "distrito" in feature:
        return "distrito"
    if "tipo_inmueble" in feature:
        return "tipo_inmueble"
    for clave in list(FEATURES_NUM) + ["tipo_inmueble", "distrito"]:
        if feature.endswith(clave):
            return clave
    return feature


def importancias_agrupadas(modelo, X: pd.DataFrame, y: pd.Series) -> list[dict]:
    # En el modelo de €/m² la superficie también multiplica el resultado.
    # Si se permuta ahí, parece más importante de lo que es. Medimos el peso
    # sobre el €/m², que es lo que el modelo aprende de verdad.
    if isinstance(modelo, ModeloPrecioM2):
        estimador = modelo.pipeline_
        objetivo = np.asarray(y, dtype=float) / np.asarray(X["superficie_m2"], dtype=float)
    else:
        estimador = modelo
        objetivo = y
    resultado = permutation_importance(
        estimador, X, objetivo,
        n_repeats=8,
        random_state=42,
        scoring="neg_mean_absolute_error",
        n_jobs=1,
    )
    pesos: dict[str, float] = {}
    for feature, peso in zip(X.columns, resultado.importances_mean):
        clave = nombre_variable(feature)
        pesos[clave] = pesos.get(clave, 0.0) + max(float(peso), 0.0)
    total = sum(pesos.values()) or 1.0
    ordenadas = sorted(pesos.items(), key=lambda par: par[1], reverse=True)
    return [
        {"variable": NOMBRES_VARIABLES.get(clave, clave), "peso": round(peso / total, 3)}
        for clave, peso in ordenadas
    ]


def main():
    print("Cargando datos gold...")
    df = pd.read_csv(GOLD)
    columnas = columnas_modelo(df)
    df = df.dropna(subset=["precio_oferta", "superficie_m2", "distrito", "dist_metro_m", "dist_sol_m"])
    print(f"Filas: {len(df)} | Variables: {columnas}")

    X = df[columnas]
    y = df["precio_oferta"]
    grupos = df["id_anuncio"]

    separador = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(separador.split(X, y, groups=grupos))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    grupos_train = grupos.iloc[train_idx]
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")

    mediana_precio = y_train.groupby(X_train["distrito"]).median()
    base_precio = X_test["distrito"].map(mediana_precio).fillna(y_train.median())
    mae_base_precio = mean_absolute_error(y_test, base_precio)

    eur_m2 = y_train / X_train["superficie_m2"]
    mediana_m2 = eur_m2.groupby(X_train["distrito"]).median()
    base_m2 = X_test["distrito"].map(mediana_m2).fillna(eur_m2.median()) * X_test["superficie_m2"]
    mae_base_m2 = mean_absolute_error(y_test, base_m2)
    print(f"\nBaseline, mediana de precio por distrito:     {mae_base_precio:,.0f} €")
    print(f"Baseline, mediana de €/m² × superficie:       {mae_base_m2:,.0f} €")

    cv = GroupKFold(n_splits=5)
    resultados = []
    for nombre, modelo in candidatos(columnas).items():
        scores = -cross_val_score(
            modelo, X_train, y_train,
            groups=grupos_train,
            cv=cv,
            scoring="neg_mean_absolute_error",
            n_jobs=1,
        )
        mae_cv = float(scores.mean())
        print(f"{nombre}: MAE de validación {mae_cv:,.0f} €")
        resultados.append((mae_cv, nombre, modelo))

    resultados.sort(key=lambda t: t[0])
    _, nombre_final, modelo_final = resultados[0]
    modelo_final.fit(X_train, y_train)
    pred = np.clip(modelo_final.predict(X_test), 0, None)
    mae = mean_absolute_error(y_test, pred)
    r2 = r2_score(y_test, pred)
    error_pct = mape(y_test, pred)

    print(f"\nModelo elegido por validación: {nombre_final}")
    print(f"  MAE en test:  {mae:,.0f} €")
    print(f"  Error medio:  {error_pct:.1f} %")
    print(f"  R² en test:   {r2:.3f}")
    print(f"  Mejora vs mediana de precio: {(mae_base_precio - mae) / mae_base_precio * 100:.1f}%")
    print(f"  Mejora vs mediana de €/m²:   {(mae_base_m2 - mae) / mae_base_m2 * 100:.1f}%")

    pesos = importancias_agrupadas(modelo_final, X_train, y_train)
    print("\nPeso de cada variable:")
    for item in pesos:
        print(f"  {item['variable']}: {item['peso'] * 100:.0f}%")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo_final, MODEL_DIR / "modelo.pkl")

    meta = {
        "modelo": nombre_final,
        "mae": round(mae),
        "mape": round(error_pct, 1),
        "r2": round(float(r2), 3),
        "mae_baseline": round(mae_base_precio),
        "mae_baseline_m2": round(mae_base_m2),
        "mejora_baseline_pct": round((mae_base_precio - mae) / mae_base_precio * 100, 1),
        "mejora_baseline_m2_pct": round((mae_base_m2 - mae) / mae_base_m2 * 100, 1),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_total": int(len(df)),
        "fecha": "2026-09-26",
        "columnas": columnas,
        "importancias": pesos,
    }
    (MODEL_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardado en {MODEL_DIR / 'modelo.pkl'}")


if __name__ == "__main__":
    main()
