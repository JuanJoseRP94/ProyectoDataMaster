"""Reglas compartidas de limpieza, enriquecimiento y formato."""

from __future__ import annotations

import json
import unicodedata
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone

ROOT = Path(__file__).resolve().parents[1]
METRO_PATH = ROOT / "data" / "processed" / "metro_madrid.csv"

# Puerta del Sol, referencia de centro que el usuario entiende.
SOL_LAT = 40.416775
SOL_LON = -3.703790

# Códigos de antigüedad de Fotocasa, contrastados uno a uno con anuncios reales.
ANTIGUEDAD = {
    1: ("Menos de 1 año", 0.5),
    2: ("1 a 5 años", 3),
    3: ("5 a 10 años", 7.5),
    4: ("10 a 20 años", 15),
    5: ("20 a 30 años", 25),
    6: ("30 a 50 años", 40),
    7: ("50 a 70 años", 60),
    8: ("70 a 100 años", 85),
    9: ("Más de 100 años", 110),
}

DISTRITOS = {
    "arganzuela": "Arganzuela",
    "barajas": "Barajas",
    "barrio de salamanca": "Salamanca",
    "salamanca": "Salamanca",
    "carabanchel": "Carabanchel",
    "centro": "Centro",
    "chamartin": "Chamartín",
    "chamberi": "Chamberí",
    "ciudad lineal": "Ciudad Lineal",
    "fuencarral - el pardo": "Fuencarral-El Pardo",
    "fuencarral-el pardo": "Fuencarral-El Pardo",
    "hortaleza": "Hortaleza",
    "latina": "Latina",
    "moncloa - aravaca": "Moncloa-Aravaca",
    "moncloa-aravaca": "Moncloa-Aravaca",
    "moratalaz": "Moratalaz",
    "puente de vallecas": "Puente de Vallecas",
    "retiro": "Retiro",
    "san blas": "San Blas-Canillejas",
    "san blas-canillejas": "San Blas-Canillejas",
    "san blas canillejas": "San Blas-Canillejas",
    "tetuan": "Tetuán",
    "usera": "Usera",
    "vicalvaro": "Vicálvaro",
    "villa de vallecas": "Villa de Vallecas",
    "villaverde": "Villaverde",
}

# Nombres planos para explicar el modelo a un comprador.
NOMBRES_VARIABLES = {
    "superficie_m2": "Superficie",
    "habitaciones": "Habitaciones",
    "banos": "Baños",
    "antiguedad_anos": "Antigüedad",
    "dist_metro_m": "Cercanía al metro",
    "dist_sol_m": "Cercanía al centro",
    "distrito": "Distrito",
    "tipo_inmueble": "Tipo de inmueble",
}


def quitar_acentos(texto: str) -> str:
    texto = str(texto).replace("\ufffd", "")
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.lower().split())


def normalizar_distrito(valor) -> str | None:
    if pd.isna(valor):
        return None
    clave = quitar_acentos(valor)
    return DISTRITOS.get(clave)


def haversine_m(lat1, lon1, lat2, lon2):
    """Distancia en metros. Acepta escalares o arrays."""
    r = 6_371_000
    p1, l1, p2, l2 = map(np.radians, [np.asarray(lat1, dtype=float), np.asarray(lon1, dtype=float),
                                      np.asarray(lat2, dtype=float), np.asarray(lon2, dtype=float)])
    dp = p2 - p1
    dl = l2 - l1
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def distancia_minima_m(lat, lon, puntos: pd.DataFrame) -> float:
    if puntos.empty or pd.isna(lat) or pd.isna(lon):
        return float("nan")
    dist = haversine_m(lat, lon, puntos["latitud"].to_numpy(), puntos["longitud"].to_numpy())
    return float(np.min(dist))


def _descargar_metro() -> pd.DataFrame:
    query = """
    [out:json][timeout:90];
    (
      node["railway"="station"]["station"="subway"](40.30,-3.95,40.60,-3.45);
      node["public_transport"="station"]["subway"="yes"](40.30,-3.95,40.60,-3.45);
    );
    out body;
    """
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=query.encode("utf-8"),
        headers={"User-Agent": "PrecioJustoMadrid/1.0 (proyecto academico)"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    filas = []
    for el in payload.get("elements", []):
        tags = el.get("tags") or {}
        if "lat" not in el or "lon" not in el:
            continue
        filas.append({
            "nombre": tags.get("name", ""),
            "latitud": el["lat"],
            "longitud": el["lon"],
        })
    metro = pd.DataFrame(filas)
    if metro.empty:
        raise RuntimeError("Overpass no ha devuelto estaciones de metro.")
    metro = metro.drop_duplicates(subset=["latitud", "longitud"])
    return metro


def cargar_metro(actualizar: bool = False) -> pd.DataFrame:
    if METRO_PATH.exists() and not actualizar:
        metro = pd.read_csv(METRO_PATH)
        if len(metro) >= 50:
            return metro
    metro = _descargar_metro()
    METRO_PATH.parent.mkdir(parents=True, exist_ok=True)
    metro.to_csv(METRO_PATH, index=False)
    return metro


def enriquecer_distancias(df: pd.DataFrame, metro: pd.DataFrame) -> pd.DataFrame:
    lat = df["latitud"].to_numpy(dtype=float)
    lon = df["longitud"].to_numpy(dtype=float)
    mlat = metro["latitud"].to_numpy(dtype=float)
    mlon = metro["longitud"].to_numpy(dtype=float)

    # (n_anuncios, n_estaciones) cabe de sobra para unos miles de pisos.
    dist = haversine_m(lat[:, None], lon[:, None], mlat[None, :], mlon[None, :])
    df = df.copy()
    df["dist_metro_m"] = np.min(dist, axis=1).round(0)
    df["dist_sol_m"] = haversine_m(lat, lon, SOL_LAT, SOL_LON).round(0)
    return df


def euros(valor: float) -> str:
    return f"{valor:,.0f} €".replace(",", ".")


def geocodificar(consulta: str) -> dict | None:
    """Una consulta a Nominatim. Pensada para la demo, no para lotes."""
    url = (
        "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=es&q="
        + urllib.request.quote(consulta)
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PrecioJustoMadrid/1.0 (proyecto academico)"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data:
        return None
    item = data[0]
    return {
        "lat": float(item["lat"]),
        "lon": float(item["lon"]),
        "nombre": item.get("display_name", consulta),
    }


def antiguedad_a_anos(codigo) -> float:
    if pd.isna(codigo):
        return float("nan")
    try:
        codigo = int(float(codigo))
    except (TypeError, ValueError):
        return float("nan")
    info = ANTIGUEDAD.get(codigo)
    if info is None:
        return float("nan")
    return float(info[1])


# propertySubtype de Fotocasa, contrastado con el tipo que muestra el anuncio.
# Las casas (3 y 5) no entran: el producto estima pisos, no chalets.
SUBTIPOS = {
    1: "Piso",
    2: "Apartamento",
    6: "Ático",
    7: "Dúplex",
    8: "Estudio",
    52: "Planta baja",
    54: "Estudio",
}


def etiqueta_tipo(codigo):
    if pd.isna(codigo):
        return "Piso"
    try:
        codigo = int(float(codigo))
    except (TypeError, ValueError):
        return None
    return SUBTIPOS.get(codigo)


FEATURES_NUM = [
    "superficie_m2",
    "habitaciones",
    "banos",
    "antiguedad_anos",
    "dist_metro_m",
    "dist_sol_m",
]
FEATURES_CAT = ["distrito"]


class ModeloPrecioM2(BaseEstimator, RegressorMixin):
    """Predice €/m² y lo pasa a euros multiplicando por la superficie."""

    def __init__(self, pipeline=None):
        self.pipeline = pipeline

    def fit(self, X, y):
        superficie = np.asarray(X["superficie_m2"], dtype=float)
        self.pipeline_ = clone(self.pipeline)
        self.pipeline_.fit(X, np.asarray(y, dtype=float) / superficie)
        return self

    def predict(self, X):
        superficie = np.asarray(X["superficie_m2"], dtype=float)
        return self.pipeline_.predict(X) * superficie


def etiqueta_antiguedad(codigo) -> str | None:
    if pd.isna(codigo):
        return None
    try:
        codigo = int(float(codigo))
    except (TypeError, ValueError):
        return None
    info = ANTIGUEDAD.get(codigo)
    return info[0] if info else None
