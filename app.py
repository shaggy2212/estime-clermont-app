import streamlit as st
import numpy as np
import pandas as pd
import requests
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# ---------------------------
# Config
# ---------------------------
st.set_page_config(
    page_title="EstimeClermont",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PRIMARY = "#004D7F"
ACCENT = "#FF7E79"
SOFT = "#EAF2FF"

# Progress UX (force visible)
MIN_PROGRESS_SECONDS = 2.8

# Gare Clermont-de-l'Oise (lon/lat)
GARE_LON = 2.41767
GARE_LAT = 49.38531

# Périmètre (communes autorisées)
AREAS: Dict[str, Dict[str, str]] = {
    "Clermont-de-l'Oise": {"city": "Clermont", "postcode": "60600", "insee": "60157"},
    "Breuil-le-Vert": {"city": "Breuil-le-Vert", "postcode": "60600", "insee": "60107"},
    "Agnetz": {"city": "Agnetz", "postcode": "60600", "insee": "60007"},
    "Fitz-James": {"city": "Fitz-James", "postcode": "60600", "insee": "60234"},
    "Breuil-le-Sec": {"city": "Breuil-le-Sec", "postcode": "60840", "insee": "60106"},
    "Neuilly-sous-Clermont": {"city": "Neuilly-sous-Clermont", "postcode": "60290", "insee": "60451"},
    "Bailleval": {"city": "Bailleval", "postcode": "60140", "insee": "60042"},
}

AUTO_AREA = "🔎 Détection automatique"
DEFAULT_AREA = "Clermont-de-l'Oise"

# Géoplateforme (IGN)
GEOPF_COMPLETION_URL = "https://data.geopf.fr/geocodage/completion/"
GEOPF_SEARCH_URL = "https://data.geopf.fr/geocodage/search"

# DVF local (généré par build_dvf_local.py)
DVF_LOCAL_PATH = Path("data/dvf_local.parquet")

# Cache buster (change si besoin)
DVF_CACHE_BUSTER = "v7"

# ---------------------------
# Session state
# ---------------------------
st.session_state.setdefault("step", 1)
st.session_state.setdefault("geo", None)
st.session_state.setdefault("res", None)

# Step 1 inputs
st.session_state.setdefault("area_name", AUTO_AREA)
st.session_state.setdefault("area_locked", False)
st.session_state.setdefault("detected_area", DEFAULT_AREA)

# IMPORTANT: on garde des valeurs cohérentes (types stables)
st.session_state.setdefault("bien_type", "Maison")         # "Maison" ou "Appartement"
st.session_state.setdefault("surface", 100.0)              # float
st.session_state.setdefault("etat", "Moyen")
st.session_state.setdefault("nb_pieces", 3)                # int
st.session_state.setdefault("nb_chambres", 2)              # int
st.session_state.setdefault("addr_typed", "")
st.session_state.setdefault("addr_choice", "")
st.session_state.setdefault("addr_choice_display", "")

# Contact
st.session_state.setdefault("prenom", "")
st.session_state.setdefault("email", "")
st.session_state.setdefault("telephone", "")
st.session_state.setdefault("consent", False)

# UI
st.session_state.setdefault("show_explain", False)

# Hybrid storage
st.session_state.setdefault("hybrid_done", False)
st.session_state.setdefault("hybrid_payload", None)

# ---------------------------
# Debug mode: only when ?debug=1
# ---------------------------
DEBUG = False
try:
    DEBUG = (st.query_params.get("debug", "0") == "1")
except Exception:
    DEBUG = False

# ---------------------------
# CSS (stable + icons fix)
# ---------------------------
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

/* Poppins global */
html, body, [class*="stApp"] {{
  font-family: 'Poppins', sans-serif !important;
}}

/* ✅ Force expander chevron icons (Streamlit) */
i.material-icons, span.material-icons, [class*="material-icons"] {{
  font-family: 'Material Icons' !important;
}}
.material-symbols-outlined, .material-symbols-rounded, .material-symbols-sharp {{
  font-family: 'Material Symbols Outlined' !important;
}}

.main {{ background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%); }}

h1 {{
    color: {PRIMARY} !important;
    font-weight: 800 !important;
    text-align: center !important;
    margin-bottom: 0.2rem !important;
}}
h2 {{
    color: {PRIMARY} !important;
    font-weight: 750 !important;
}}
h3 {{
    color: {PRIMARY} !important;
    font-weight: 750 !important;
}}

.small-note {{ color:#4b5563; font-size:0.92rem; line-height:1.45; }}

.badge {{
  display:inline-block; padding:0.35rem 0.75rem; border-radius:999px;
  background: rgba(0, 77, 127, 0.10); color:{PRIMARY}; font-weight:700; font-size:0.85rem;
}}

.card {{
  background: white; border-radius: 16px; padding: 1.05rem 1.1rem;
  box-shadow: 0 10px 26px rgba(0, 77, 127, 0.10);
  border: 1px solid rgba(0,0,0,0.06);
  overflow: hidden;
}}
.card.accent-top {{ border-top: 4px solid {ACCENT}; }}
.card.soft {{
  background: linear-gradient(135deg, {SOFT} 0%, #ffffff 100%);
  border: 1px solid rgba(0, 77, 127, 0.10);
}}

.metric {{
  background: linear-gradient(135deg, {ACCENT} 0%, #ff5b66 100%);
  color: white; border-radius: 16px; padding: 1.15rem 1.2rem;
  box-shadow: 0 12px 28px rgba(255, 126, 121, 0.28);
}}
.metric .k {{ font-size:0.86rem; opacity:0.95; margin:0; }}
.metric .v {{ font-size:1.55rem; font-weight:850; margin:0.12rem 0 0 0; letter-spacing:-0.02em; }}

hr {{ border: none; border-top: 1px solid rgba(0,0,0,0.08); margin: 1.3rem 0; }}

/* Primary buttons */
.stButton > button,
.stFormSubmitButton > button {{
    background: linear-gradient(135deg, {ACCENT} 0%, #ff5b66 100%) !important;
    color: white !important;
    font-weight: 900 !important;
    border-radius: 14px !important;
    border: none !important;
    padding: 1.05rem 1.2rem !important;
    font-size: 1.07rem !important;
    box-shadow: 0 10px 26px rgba(255, 126, 121, 0.35) !important;
}}
.stButton > button:hover,
.stFormSubmitButton > button:hover {{
    box-shadow: 0 14px 34px rgba(255, 126, 121, 0.48) !important;
    transform: translateY(-1px);
}}

/* Secondary button */
.secondary-btn .stButton > button {{
    background: rgba(0, 77, 127, 0.08) !important;
    color: {PRIMARY} !important;
    font-weight: 800 !important;
    border: 1px solid rgba(0, 77, 127, 0.20) !important;
    box-shadow: none !important;
}}
.secondary-btn .stButton > button:hover {{
    background: rgba(0, 77, 127, 0.12) !important;
    box-shadow: none !important;
    transform: none !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------
# Helpers (general)
# ---------------------------
def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dl / 2) ** 2
    return float(2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))


def norm(s: str) -> str:
    return (s or "").strip().lower().replace("’", "'")


def eur(x: float) -> str:
    return f"{x:,.0f} €".replace(",", " ")


def normalize_query_to_area(q: str, city: str, postcode: str) -> str:
    q = (q or "").strip()
    if not q:
        return q
    low = norm(q)
    if postcode not in low and norm(city) not in low:
        q = f"{q}, {postcode} {city}, Oise, France"
    return q


def get_effective_area() -> Tuple[str, Dict[str, str]]:
    if st.session_state.area_name in AREAS:
        a = st.session_state.area_name
        return a, AREAS[a]
    detected = st.session_state.get("detected_area")
    if detected in AREAS:
        return detected, AREAS[detected]
    return DEFAULT_AREA, AREAS[DEFAULT_AREA]


def parse_display_choice(display_value: str) -> Tuple[Optional[str], str]:
    s = (display_value or "").strip()
    for sep in [" — ", "—", " - ", "-"]:
        if sep in s:
            a, lab = s.split(sep, 1)
            a = a.strip()
            lab = lab.strip()
            if a in AREAS:
                return a, lab
            return None, lab
    return None, s


def on_addr_choice_display_change():
    display_val = st.session_state.get("addr_choice_display", "")
    area, label = parse_display_choice(display_val)
    st.session_state.addr_choice = label
    if area:
        st.session_state.detected_area = area
        st.session_state.area_locked = True


# ---------------------------
# GeoPlateforme (IGN)
# ---------------------------
@st.cache_data(ttl=60 * 60, show_spinner=False)
def geopf_completion(text: str, postcode: str, city: str, max_resp: int = 7) -> List[str]:
    if not text or len(text.strip()) < 3:
        return []
    params = {
        "text": text.strip(),
        "terr": postcode,
        "type": "StreetAddress",
        "maximumResponses": max_resp,
        "city": city,
    }
    r = requests.get(GEOPF_COMPLETION_URL, params=params, timeout=8)
    r.raise_for_status()
    data = r.json()
    results = data.get("results") or data.get("features") or []
    out: List[str] = []
    for it in results:
        props = it.get("properties", it) if isinstance(it, dict) else {}
        label = props.get("label") or props.get("fulltext") or props.get("name")
        if not label:
            continue
        if postcode and postcode not in label:
            continue
        if city and norm(city) not in norm(label):
            continue
        out.append(label)

    # dedup
    seen = set()
    dedup = []
    for lab in out:
        if lab not in seen:
            dedup.append(lab)
            seen.add(lab)
    return dedup


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def geopf_geocode_one(query: str) -> Optional[Dict[str, Any]]:
    if not query:
        return None
    params = {"q": query, "limit": 1}
    r = requests.get(GEOPF_SEARCH_URL, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    feats = data.get("features", [])
    if not feats:
        return None
    f0 = feats[0]
    geom = f0.get("geometry", {})
    props = f0.get("properties", {})
    coords = geom.get("coordinates")
    if not coords or len(coords) < 2:
        return None
    lon, lat = float(coords[0]), float(coords[1])
    return {"lat": lat, "lon": lon, "label": props.get("label") or query}


# ---------------------------
# Estimation (step 1)
# ---------------------------
def quartier_from_distance(distance_m: float) -> str:
    if distance_m < 500:
        return "Nord (Gare)"
    if distance_m < 1500:
        return "Centre-ville"
    if distance_m < 2500:
        return "Sud (Résidentiel)"
    if distance_m < 3500:
        return "Est (Pavillons)"
    return "Ouest (Neuf)"


def base_prix_m2(quartier: str, bien_type: str) -> float:
    table = {
        "Centre-ville": {"Maison": 2100, "Appartement": 2500},
        "Nord (Gare)": {"Maison": 1950, "Appartement": 2200},
        "Sud (Résidentiel)": {"Maison": 2350, "Appartement": 2700},
        "Est (Pavillons)": {"Maison": 2000, "Appartement": 2300},
        "Ouest (Neuf)": {"Maison": 2450, "Appartement": 2800},
    }
    return float(table[quartier][bien_type])


def estimate_price(
    bien_type: str,
    surface: float,
    nb_pieces: int,
    nb_chambres: int,
    etat: str,
    distance_m: float
) -> Dict[str, Any]:
    quartier = quartier_from_distance(distance_m)
    prix_m2 = base_prix_m2(quartier, bien_type)

    facteur_pieces = 1 + (nb_pieces - 3) * 0.03
    facteur_chambres = 1 + (nb_chambres - 2) * 0.05
    facteur_etat = {"À rénover": 0.85, "Moyen": 1.0, "Bon": 1.06, "Rénové": 1.12}[etat]
    facteur_gare = 1 + min(0.08, 0.5 / (1 + distance_m / 1000))

    prix_total = prix_m2 * surface * facteur_pieces * facteur_chambres * facteur_etat * facteur_gare
    return {
        "quartier": quartier,
        "distance_gare_m": int(round(distance_m)),
        "prix_m2": prix_m2 * facteur_pieces * facteur_chambres * facteur_etat * facteur_gare,
        "prix_total": prix_total,
        "min": prix_total * 0.93,
        "max": prix_total * 1.07,
        "explain": {
            "Base €/m²": round(prix_m2, 0),
            "Impact pièces": f"{(facteur_pieces - 1) * 100:+.1f}%",
            "Impact chambres": f"{(facteur_chambres - 1) * 100:+.1f}%",
            "Impact état": f"{(facteur_etat - 1) * 100:+.1f}%",
            "Bonus gare": f"{(facteur_gare - 1) * 100:+.1f}%",
        },
    }


# ---------------------------
# DVF local: load + normalize
# ---------------------------
def normalize_type_local(x: Any) -> str:
    """
    Normalise les libellés DVF vers EXACTEMENT:
      - "Maison"
      - "Appartement"
      - "Autre"
    """
    s = str(x or "").strip().lower()
    s = s.replace("’", "'")
    s = s.replace("appartementement", "appartement")
    s = s.replace("appartemment", "appartement")
    s = s.replace("appartemnt", "appartement")
    s = s.replace("apt", "appartement")
    if "appart" in s:
        return "Appartement"
    if "maison" in s:
        return "Maison"
    return "Autre"


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def load_dvf_local(_bust: str = DVF_CACHE_BUSTER) -> pd.DataFrame:
    if not DVF_LOCAL_PATH.exists():
        return pd.DataFrame()

    df = pd.read_parquet(DVF_LOCAL_PATH)

    # coercions
    df["date_mutation"] = pd.to_datetime(df.get("date_mutation"), errors="coerce")
    df["valeur_fonciere"] = pd.to_numeric(df.get("valeur_fonciere"), errors="coerce")
    df["surface_reelle_bati"] = pd.to_numeric(df.get("surface_reelle_bati"), errors="coerce")
    df["longitude"] = pd.to_numeric(df.get("longitude"), errors="coerce")
    df["latitude"] = pd.to_numeric(df.get("latitude"), errors="coerce")

    # garde RAW + normalisation
    if "type_local" in df.columns:
        df["type_local_raw"] = df["type_local"]
    else:
        df["type_local_raw"] = None
        df["type_local"] = None

    df["type_local"] = df["type_local_raw"].apply(normalize_type_local)

    # ✅ (MODIF #1) pièces DVF (si dispo), stockées en nb_pieces_dvf
    if "nombre_pieces_principales" in df.columns:
        df["nb_pieces_dvf"] = pd.to_numeric(df["nombre_pieces_principales"], errors="coerce")
    elif "nb_pieces" in df.columns:
        df["nb_pieces_dvf"] = pd.to_numeric(df["nb_pieces"], errors="coerce")
    else:
        df["nb_pieces_dvf"] = np.nan

    # filtres qualité
    df = df.dropna(subset=["date_mutation", "valeur_fonciere", "surface_reelle_bati", "longitude", "latitude", "type_local"])
    df = df[df["type_local"].isin(["Maison", "Appartement"])]
    df = df[(df["valeur_fonciere"] > 1000) & (df["surface_reelle_bati"] >= 10)]
    return df


def dvf_select_similaires_strict(
    df_all: pd.DataFrame,
    lat: float,
    lon: float,
    bien_type: str,
    surface: float,
) -> Tuple[pd.DataFrame, int, float]:
    """
    Retourne (df_similaires, rayon_utilise, tol_utilisee).
    STRICT:
      - type_local strict
      - surface strict (tol progressive)
      - jamais de fallback qui mélange les types ou explose les surfaces
    """
    if df_all.empty:
        return pd.DataFrame(), 0, 0.0

    target_type = normalize_type_local(bien_type)
    surface = float(surface)

    max_date = df_all["date_mutation"].max()
    if pd.isna(max_date):
        return pd.DataFrame(), 0, 0.0

    cutoff = max_date - pd.Timedelta(days=365)
    df = df_all[df_all["date_mutation"] >= cutoff].copy()
    if df.empty:
        return pd.DataFrame(), 0, 0.0

    # strict type
    df["type_local"] = df["type_local"].apply(normalize_type_local)
    df = df[df["type_local"] == target_type].copy()
    if df.empty:
        return pd.DataFrame(), 0, 0.0

    # distance vectorized
    lat_arr = df["latitude"].to_numpy(dtype=float)
    lon_arr = df["longitude"].to_numpy(dtype=float)
    lat0 = float(lat)
    lon0 = float(lon)

    R = 6371000.0
    phi1 = np.radians(lat0)
    phi2 = np.radians(lat_arr)
    dphi = np.radians(lat_arr - lat0)
    dl = np.radians(lon_arr - lon0)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dl / 2) ** 2
    dist = 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    df["distance_m"] = dist

    radii = [800, 1500, 2500, 3500]

    if target_type == "Appartement":
        tolerances = [0.25, 0.30, 0.35]
        min_needed = 4
    else:
        tolerances = [0.30, 0.40, 0.45]
        min_needed = 4

    best = pd.DataFrame()
    used_radius = 0
    used_tol = 0.0

    for rad in radii:
        df_r = df[df["distance_m"] <= rad].copy()
        if df_r.empty:
            continue

        for tol in tolerances:
            low = surface * (1 - tol)
            high = surface * (1 + tol)
            df_s = df_r[(df_r["surface_reelle_bati"] >= low) & (df_r["surface_reelle_bati"] <= high)].copy()
            if df_s.empty:
                continue

            df_s["prix_m2"] = df_s["valeur_fonciere"] / df_s["surface_reelle_bati"]
            df_s = df_s.replace([np.inf, -np.inf], np.nan).dropna(subset=["prix_m2"])

            if len(df_s) >= 10:
                q10 = df_s["prix_m2"].quantile(0.10)
                q90 = df_s["prix_m2"].quantile(0.90)
                df_s = df_s[(df_s["prix_m2"] >= q10) & (df_s["prix_m2"] <= q90)]

            if len(df_s) >= min_needed:
                best = df_s
                used_radius = rad
                used_tol = tol
                break

        if not best.empty:
            break

    if best.empty:
        tol = tolerances[-1]
        low = surface * (1 - tol)
        high = surface * (1 + tol)
        rad = radii[-1]

        df_fb = df[df["distance_m"] <= rad].copy()
        df_fb = df_fb[(df_fb["surface_reelle_bati"] >= low) & (df_fb["surface_reelle_bati"] <= high)].copy()
        if df_fb.empty:
            return pd.DataFrame(), 0, 0.0

        df_fb["prix_m2"] = df_fb["valeur_fonciere"] / df_fb["surface_reelle_bati"]
        df_fb = df_fb.replace([np.inf, -np.inf], np.nan).dropna(subset=["prix_m2"])
        df_fb = df_fb.sort_values(["distance_m", "date_mutation"], ascending=[True, False]).head(3)
        return df_fb, rad, tol

    best = best.sort_values(["distance_m", "date_mutation"], ascending=[True, False]).copy()
    return best, used_radius, used_tol


def reliability_and_weight(n: int) -> Tuple[str, float]:
    if n > 15:
        return "🟢 Très élevée", 0.78
    if n >= 8:
        return "🟢 Élevée", 0.72
    if n >= 4:
        return "🟡 Bonne", 0.62
    if n >= 2:
        return "🟠 Modérée", 0.50
    return "🔴 Faible", 0.0


def target_band_pct(label: str) -> float:
    if "Très élevée" in label:
        return 0.055
    if "Élevée" in label:
        return 0.065
    if "Bonne" in label:
        return 0.075
    if "Modérée" in label:
        return 0.095
    return 0.14


def abs_band_caps(bien_type: str) -> Tuple[float, float]:
    # FULL width caps
    if normalize_type_local(bien_type) == "Appartement":
        return 5000.0, 11000.0
    return 8000.0, 18000.0


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ---------------------------
# Debug tools (only in debug mode)
# ---------------------------
if DEBUG:
    with st.expander("🧹 Outils (debug)", expanded=False):
        cols = st.columns([1, 1])
        with cols[0]:
            if st.button("Vider le cache Streamlit"):
                st.cache_data.clear()
                st.success("Cache vidé. Rechargement…")
                st.rerun()
        with cols[1]:
            if st.button("Forcer reload DVF (cache buster)"):
                st.session_state["_dvf_bust_manual"] = str(time.time())
                st.cache_data.clear()
                st.success("DVF reload forcé. Rechargement…")
                st.rerun()
        st.caption(f"DVF cache buster: {DVF_CACHE_BUSTER}")


# ---------------------------
# Header
# ---------------------------
effective_area, effective_info = get_effective_area()
badge_label = f"{effective_area} ({effective_info['postcode']})"

st.markdown("<h1>🏠 Estimation locale</h1>", unsafe_allow_html=True)
st.markdown(
    f"<div style='text-align:center; margin-bottom:0.6rem;'><span class='badge'>Secteur : {badge_label}</span></div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='card accent-top'><b>Objectif :</b> vous donner une <b>fourchette crédible</b> en 30 secondes, "
    "puis affiner avec des ventes comparables (DVF) et les spécificités du bien.</div>",
    unsafe_allow_html=True,
)
st.markdown("<hr/>", unsafe_allow_html=True)

# ---------------------------
# Step 1
# ---------------------------
if st.session_state.step == 1:
    colL, colR = st.columns([1.2, 1], gap="large")

    with colL:
        st.markdown("## 📍 Votre secteur")
        area_options = [AUTO_AREA] + list(AREAS.keys())
        st.selectbox("Choisissez la commune (ou laissez en auto)", area_options, key="area_name")

        if st.session_state.area_name in AREAS:
            st.session_state.detected_area = st.session_state.area_name
            st.session_state.area_locked = True
        else:
            if st.session_state.get("detected_area") not in AREAS:
                st.session_state.detected_area = DEFAULT_AREA

        effective_area, ai = get_effective_area()
        st.markdown(
            f"<div class='card soft'><b>Commune utilisée pour la recherche :</b> {effective_area} — <b>CP :</b> {ai['postcode']}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("## 📋 Décrivez votre bien")
        c1, c2 = st.columns(2)

        with c1:
            st.selectbox("Type de bien", ["Maison", "Appartement"], key="bien_type")
            st.number_input("Surface (m²)", min_value=10.0, max_value=500.0, step=1.0, key="surface")
            st.selectbox("État du bien", ["À rénover", "Moyen", "Bon", "Rénové"], key="etat")

        with c2:
            st.number_input("Nombre de pièces", min_value=1, max_value=12, step=1, key="nb_pieces")
            st.number_input("Nombre de chambres", min_value=0, max_value=10, step=1, key="nb_chambres")
            st.markdown(
                "<div class='small-note'>Plus le descriptif est précis, plus l’estimation sera cohérente.</div>",
                unsafe_allow_html=True,
            )

        st.markdown("## 🧭 Localisation")
        st.text_input("Commencez à taper l’adresse", placeholder="Ex : 5 Rue du Chemin Blanc", key="addr_typed")
        st.markdown(
            "<div class='small-note'>Plus l’adresse est précise (numéro + rue), plus le résultat est fiable.</div>",
            unsafe_allow_html=True,
        )

        typed = st.session_state.addr_typed.strip()
        addr_status = st.empty()
        suggestions_display: List[str] = []

        if len(typed) >= 3:
            addr_status.markdown("<div class='small-note'>🔎 Recherche en cours…</div>", unsafe_allow_html=True)
        else:
            addr_status.markdown("<div class='small-note'>Tapez au moins 3 caractères pour voir des suggestions.</div>", unsafe_allow_html=True)

        if st.session_state.area_name == AUTO_AREA:
            if len(typed) >= 3:
                for area_name, info in AREAS.items():
                    try:
                        labs = geopf_completion(typed, postcode=info["postcode"], city=info["city"], max_resp=5)
                    except Exception:
                        labs = []
                    for lab in labs:
                        suggestions_display.append(f"{area_name} — {lab}")
        else:
            if len(typed) >= 3:
                try:
                    labs = geopf_completion(typed, postcode=ai["postcode"], city=ai["city"])
                except Exception:
                    labs = []
                suggestions_display = labs[:]

        if len(typed) >= 3:
            addr_status.empty()

        if suggestions_display:
            prev_display = st.session_state.get("addr_choice_display", "")
            default_index = suggestions_display.index(prev_display) if prev_display in suggestions_display else 0
            st.selectbox(
                "Suggestions (secteur)",
                suggestions_display,
                index=default_index,
                key="addr_choice_display",
                on_change=on_addr_choice_display_change,
            )
        else:
            st.session_state.addr_choice = typed
            st.session_state.addr_choice_display = typed

        if st.session_state.area_name == AUTO_AREA:
            detected = st.session_state.get("detected_area")
            if detected in AREAS and st.session_state.area_locked:
                inf = AREAS[detected]
                st.markdown(
                    f"<div class='card soft'><b>Commune détectée :</b> {detected} — <b>CP :</b> {inf['postcode']}</div>",
                    unsafe_allow_html=True,
                )

        if st.button("🚀 Obtenir ma fourchette (sans engagement)", use_container_width=True):
            if st.session_state.area_name == AUTO_AREA:
                detected_area, detected_label = parse_display_choice(st.session_state.get("addr_choice_display", ""))
                if detected_area:
                    st.session_state.detected_area = detected_area
                    st.session_state.area_locked = True
                    st.session_state.addr_choice = detected_label
                elif st.session_state.get("detected_area") in AREAS and st.session_state.area_locked:
                    pass
                else:
                    st.error("Choisis une suggestion d’adresse (pour détecter la commune) ou sélectionne la commune manuellement.")
                    st.stop()

            effective_area, ai = get_effective_area()

            addr_choice = (st.session_state.addr_choice or "").strip()
            if not addr_choice or len(addr_choice) < 6:
                st.error("Ajoute une adresse plus complète (ou choisis une suggestion dans le secteur).")
                st.stop()

            q = normalize_query_to_area(addr_choice, city=ai["city"], postcode=ai["postcode"])

            try:
                geo = geopf_geocode_one(q)
            except Exception:
                geo = None

            if not geo:
                st.error("Impossible de géocoder l’adresse. Choisis une suggestion ou précise numéro + rue.")
                st.stop()

            label_low = norm(geo.get("label") or "")
            if ai["postcode"] not in label_low or norm(ai["city"]) not in label_low:
                st.error("Cette adresse ne semble pas être dans la commune sélectionnée/détectée. Choisis une suggestion du secteur.")
                st.stop()

            distance_m = haversine_m(geo["lat"], geo["lon"], GARE_LAT, GARE_LON)
            res = estimate_price(
                st.session_state.bien_type,
                float(st.session_state.surface),
                int(st.session_state.nb_pieces),
                int(st.session_state.nb_chambres),
                st.session_state.etat,
                distance_m,
            )

            st.session_state.geo = geo
            st.session_state.res = res
            st.session_state.step = 2
            st.session_state.hybrid_done = False
            st.session_state.hybrid_payload = None
            st.rerun()

    with colR:
        st.markdown("## 💎 Ce que vous obtenez")
        st.markdown(
            "<div class='card accent-top'>"
            "✅ Adresse filtrée sur la commune (auto ou manuel)<br/>"
            "✅ Distance à la gare calculée automatiquement<br/>"
            "✅ Fourchette immédiate<br/>"
            "✅ Fourchette optimisée (DVF + comparables) après email"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='card soft'><b>Note :</b> l’estimation est indicative. L’affinage final se fait après vérification "
            "(état réel, travaux, terrain, nuisances, exposition, prestations) — et comparables DVF.</div>",
            unsafe_allow_html=True,
        )

# ---------------------------
# Step 2
# ---------------------------
if st.session_state.step == 2 and st.session_state.geo and st.session_state.res:
    # padding anti “atterrissage trop bas”
    st.markdown("<div style='height:220px'></div>", unsafe_allow_html=True)

    geo = st.session_state.geo
    res = st.session_state.res
    effective_area, ai = get_effective_area()

    if effective_area == "Clermont-de-l'Oise":
        sector_display = f"{effective_area} — {res.get('quartier','')}"
    else:
        sector_display = effective_area

    st.markdown("## ✨ Votre estimation (fourchette immédiate)")

    m1, m2, m3 = st.columns(3, gap="medium")
    with m1:
        st.markdown(
            f"<div class='metric'><p class='k'>Fourchette</p><p class='v'>{eur(res['min'])} – {eur(res['max'])}</p></div>",
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f"<div class='metric'><p class='k'>Secteur</p><p class='v'>{sector_display}</p></div>",
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f"<div class='metric'><p class='k'>Distance gare</p><p class='v'>{res['distance_gare_m']} m</p></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div class='card soft'><b>Adresse géocodée :</b> {geo.get('label','')}<br/>"
        f"<b>Prix/m² indicatif (après facteurs) :</b> {eur(res['prix_m2'])} / m²</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<hr/>", unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="medium")
    with left:
        st.markdown("<div class='secondary-btn'>", unsafe_allow_html=True)
        if st.button("⬅️ Modifier les infos du bien", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.toggle("Afficher l’explication (transparence)", key="show_explain")

    if st.session_state.show_explain:
        ex = res.get("explain", {})
        st.markdown("<div class='card accent-top'>", unsafe_allow_html=True)
        st.markdown("### 🧾 Détail du calcul (résumé)")
        st.markdown(
            f"""
- **Base quartier (€/m²)** : {ex.get("Base €/m²", "—")}
- **Pièces** : {ex.get("Impact pièces", "—")}
- **Chambres** : {ex.get("Impact chambres", "—")}
- **État du bien** : {ex.get("Impact état", "—")}
- **Proximité gare** : {ex.get("Bonus gare", "—")}
""".strip()
        )
        st.markdown(
            "<p class='small-note'>Ces facteurs sont indicatifs. La visite et les caractéristiques réelles "
            "(travaux, terrain, nuisances, exposition, prestations) peuvent faire varier l’estimation.</p>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    st.markdown("## 📩 Recevoir la fourchette optimisée (comparables DVF)")
    st.markdown("<div class='card accent-top'>", unsafe_allow_html=True)

    with st.form("contact_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Votre prénom", key="prenom")
            st.text_input("Votre email", key="email")
        with c2:
            st.text_input("Votre téléphone", key="telephone")
            st.checkbox("J’accepte d’être recontacté au sujet de cette estimation (sans spam).", key="consent")

        submitted = st.form_submit_button("✅ Obtenir la fourchette optimisée", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if not (st.session_state.prenom and st.session_state.email and st.session_state.telephone and st.session_state.consent):
            st.error("Il manque une info (ou le consentement).")
        else:
            t0 = time.time()
            progress = st.progress(0, text="🔎 Recherche des ventes comparables (12 mois)…")

            def progress_step(pct: int, txt: str, min_sleep: float = 0.25):
                progress.progress(pct, text=txt)
                time.sleep(min_sleep)

            try:
                progress_step(10, "📦 Chargement de la base DVF locale…", 0.40)
                df_all = load_dvf_local(st.session_state.get("_dvf_bust_manual", DVF_CACHE_BUSTER))
                if df_all.empty:
                    st.warning("⚠️ Base DVF locale introuvable (fichier parquet manquant).")
                    st.stop()

                progress_step(55, "🏡 Sélection de comparables cohérents (type + surface)…", 0.80)
                df_local, used_radius, used_tol = dvf_select_similaires_strict(
                    df_all=df_all,
                    lat=float(geo["lat"]),
                    lon=float(geo["lon"]),
                    bien_type=st.session_state.bien_type,
                    surface=float(st.session_state.surface),
                )

                # --- DEBUG DVF (uniquement si ?debug=1) ---
                if DEBUG:
                    st.markdown("### 🧪 Debug DVF (type_local)")
                    st.write("Type demandé (formulaire) :", st.session_state.bien_type)

                    max_date_dbg = df_all["date_mutation"].max()
                    cutoff_dbg = max_date_dbg - pd.Timedelta(days=365)
                    df12 = df_all[df_all["date_mutation"] >= cutoff_dbg].copy()

                    st.write("Valeurs RAW (12 mois) :")
                    if "type_local_raw" in df12.columns:
                        st.write(df12["type_local_raw"].astype(str).str.strip().value_counts().head(30))
                    else:
                        st.warning("Colonne type_local_raw absente.")

                    st.write("Valeurs NORMALISÉES (12 mois) :")
                    st.write(df12["type_local"].value_counts())

                    st.write("Comparables RETOURNÉS : n =", len(df_local))
                    if not df_local.empty:
                        st.write("value_counts type_local :", df_local["type_local"].value_counts())
                        st.write(
                            "surface min/max (avant filtre) :",
                            float(df_local["surface_reelle_bati"].min()),
                            "/",
                            float(df_local["surface_reelle_bati"].max()),
                        )
                        cols_show = [
                            c for c in [
                                "type_local_raw", "type_local", "surface_reelle_bati", "nb_pieces_dvf",
                                "valeur_fonciere", "date_mutation", "nom_commune", "distance_m"
                            ] if c in df_local.columns
                        ]
                        st.dataframe(df_local[cols_show].head(25), use_container_width=True)

                # ✅ ULTIMATE ENFORCEMENT (zéro incohérence autorisée)
                target_type = normalize_type_local(st.session_state.bien_type)
                if not df_local.empty:
                    df_local["type_local"] = df_local["type_local"].apply(normalize_type_local)
                    df_local = df_local[df_local["type_local"] == target_type].copy()

                    tol = float(used_tol or (0.35 if target_type == "Appartement" else 0.45))
                    s0 = float(st.session_state.surface)
                    lo = s0 * (1 - tol)
                    hi = s0 * (1 + tol)
                    df_local = df_local[(df_local["surface_reelle_bati"] >= lo) & (df_local["surface_reelle_bati"] <= hi)].copy()

                # De-dup preview
                if not df_local.empty:
                    df_local = df_local.drop_duplicates(
                        subset=["date_mutation", "valeur_fonciere", "surface_reelle_bati", "type_local", "nom_commune"],
                        keep="first",
                    )

                progress_step(75, "📊 Calcul de la fourchette optimisée…", 0.80)

                algo_min = float(res["min"])
                algo_max = float(res["max"])
                algo_center = (algo_min + algo_max) / 2.0
                algo_width = algo_max - algo_min

                nb_similaires = int(len(df_local))
                max_date = df_all["date_mutation"].max()
                last_update = max_date.strftime("%B %Y") if pd.notna(max_date) else "—"

                fiabilite_label, poids_dvf = reliability_and_weight(nb_similaires)
                note_guardrail = ""

                # valeurs par défaut
                opt_min, opt_max = algo_min, algo_max

                if nb_similaires < 2:
                    note_guardrail = (
                        "Pas assez de comparables STRICTS sur 12 mois : "
                        "on reste proche de l’estimation immédiate (pour éviter une incohérence)."
                    )
                else:
                    # ensure prix_m2 exists
                    if "prix_m2" not in df_local.columns:
                        df_local["prix_m2"] = df_local["valeur_fonciere"] / df_local["surface_reelle_bati"]
                        df_local = df_local.replace([np.inf, -np.inf], np.nan).dropna(subset=["prix_m2"])

                    dvf_m2_low = float(df_local["prix_m2"].quantile(0.25))
                    dvf_m2_high = float(df_local["prix_m2"].quantile(0.75))

                    surface_used = float(st.session_state.surface)
                    dvf_min = dvf_m2_low * surface_used
                    dvf_max = dvf_m2_high * surface_used

                    # ✅ Filet de sécurité #1 (DVF) : jamais inversé
                    if dvf_min > dvf_max:
                        dvf_min, dvf_max = dvf_max, dvf_min

                    # hybrid on bounds
                    opt_min = poids_dvf * dvf_min + (1 - poids_dvf) * algo_min
                    opt_max = poids_dvf * dvf_max + (1 - poids_dvf) * algo_max

                    # Force "optimized" narrower and not weird
                    band_pct = target_band_pct(fiabilite_label)
                    full_width_target = max(1.0, ((opt_min + opt_max) / 2.0) * band_pct)

                    abs_min_cap, abs_max_cap = abs_band_caps(st.session_state.bien_type)
                    full_width_target = clamp(full_width_target, abs_min_cap, abs_max_cap)
                    full_width_target = min(full_width_target, algo_width * 0.82)

                    c = (opt_min + opt_max) / 2.0
                    opt_min = c - full_width_target / 2.0
                    opt_max = c + full_width_target / 2.0

                    slack = algo_width * 0.10
                    opt_min = max(opt_min, algo_min - slack)
                    opt_max = min(opt_max, algo_max + slack)

                    opt_center = (opt_min + opt_max) / 2.0
                    ratio = opt_center / max(1.0, algo_center)
                    if ratio > 1.18 or ratio < 0.82:
                        note_guardrail = "Marché hétérogène : on tempère l’optimisation pour éviter une incohérence."
                        pull = 0.45
                        opt_min = (1 - pull) * opt_min + pull * algo_min
                        opt_max = (1 - pull) * opt_max + pull * algo_max

                # ✅ (MODIF #3) Filet de sécurité #3 (anti-déception SOUPLE)
                # opt_min ne peut pas être plus bas que algo_min - X%
                X = 0.03  # 3%
                opt_min_floor = float(algo_min) * (1.0 - X)
                opt_min = max(float(opt_min), opt_min_floor)

                # garde une largeur mini (évite les fourchettes "ridicules")
                min_width = max(4000.0, 0.02 * max(1.0, opt_min))
                if float(opt_max) < opt_min + min_width:
                    opt_max = opt_min + min_width

                # ✅ Filet de sécurité #2 (opt) : jamais de fourchette inversée / NaN
                opt_min = float(opt_min)
                opt_max = float(opt_max)
                if not np.isfinite(opt_min) or not np.isfinite(opt_max):
                    opt_min, opt_max = float(res["min"]), float(res["max"])
                if opt_min > opt_max:
                    opt_min, opt_max = opt_max, opt_min

                # ✅ (MODIF #2) preview_records inclut nb de pièces (si dispo)
                preview_records: List[Dict[str, Any]] = []
                if nb_similaires > 0:
                    prev = df_local.sort_values(["distance_m", "date_mutation"], ascending=[True, False]).head(5)
                    for _, r in prev.iterrows():
                        try:
                            mois = pd.to_datetime(r["date_mutation"]).strftime("%m/%Y")
                        except Exception:
                            mois = "—"
                        pieces_val = None
                        try:
                            if "nb_pieces_dvf" in r.index and pd.notna(r.get("nb_pieces_dvf", np.nan)):
                                pieces_val = int(float(r.get("nb_pieces_dvf")))
                        except Exception:
                            pieces_val = None

                        preview_records.append(
                            {
                                "type_local": str(r.get("type_local", "")),
                                "surface": int(round(float(r.get("surface_reelle_bati", 0)))),
                                "pieces": pieces_val,
                                "prix": float(r.get("valeur_fonciere", 0)),
                                "mois": mois,
                                "commune": str(r.get("nom_commune", "Secteur")),
                                "dist": int(round(float(r.get("distance_m", 0)) / 100.0) * 100),
                            }
                        )

                progress_step(90, "🔍 Vérification de cohérence…", 0.55)

                # enforce minimum UX duration
                dt = time.time() - t0
                if dt < MIN_PROGRESS_SECONDS:
                    time.sleep(MIN_PROGRESS_SECONDS - dt)

                progress.progress(100, text="✅ Terminé.")
                time.sleep(0.20)

                st.session_state.hybrid_payload = {
                    "fiabilite_label": fiabilite_label,
                    "nb_similaires": nb_similaires,
                    "poids_dvf": float(poids_dvf),
                    "opt_min": float(opt_min),
                    "opt_max": float(opt_max),
                    "last_update": last_update,
                    "used_radius": int(used_radius),
                    "used_tol": float(used_tol),
                    "note_guardrail": note_guardrail,
                    "similaires_preview": preview_records,
                    "bien_type": target_type,
                }
                st.session_state.hybrid_done = True

            finally:
                progress.empty()

            st.success(f"Merci {st.session_state.prenom} ✅ Je te contacte rapidement pour affiner et te donner des comparables précis.")
            st.rerun()

    # Render optimized
    if st.session_state.hybrid_done and st.session_state.hybrid_payload:
        hp = st.session_state.hybrid_payload

        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown("## 💎 Fourchette de valeur optimisée")

        st.markdown(
            f"<div class='metric'><p class='k'>Valeur estimée</p>"
            f"<p class='v'>{eur(hp['opt_min'])} – {eur(hp['opt_max'])}</p></div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<div class='card soft'>"
            f"<b>Indice de fiabilité :</b> {hp['fiabilite_label']}<br>"
            f"Basé sur <b>{hp['nb_similaires']}</b> biens comparables STRICTS (12 mois) "
            f"(rayon max : {hp.get('used_radius','—')} m)<br><br>"
            f"Basé sur <b>plus d’une centaine de ventes officielles récentes</b> "
            f"(DVF – data.gouv.fr, dernière mise à jour : {hp['last_update']})"
            f"</div>",
            unsafe_allow_html=True,
        )

        if hp.get("note_guardrail"):
            st.markdown(
                f"<div class='card accent-top'><b>Note :</b> {hp['note_guardrail']}</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<div class='card'>"
            "<b>Important :</b><br><br>"
            "Cette estimation est basée sur les données officielles du marché.<br><br>"
            "Toutefois, aucun algorithme ne peut évaluer :<br>"
            "– l’état réel du bien<br>"
            "– les travaux réalisés<br>"
            "– l’isolation<br>"
            "– les nuisances<br>"
            "– l’exposition<br>"
            "– l’extérieur / terrain<br><br>"
            "<b>Pour obtenir une estimation précise, une visite du bien est indispensable.</b><br><br>"
            "Je vous contacte personnellement pour affiner cette estimation et définir "
            "la meilleure stratégie de mise en vente."
            "</div>",
            unsafe_allow_html=True,
        )

        if hp.get("similaires_preview"):
            st.markdown("<div class='card accent-top'>", unsafe_allow_html=True)
            st.markdown("### 🧾 Exemples de comparables (localisation volontairement vague)")
            for r in hp["similaires_preview"]:
                pieces_txt = f"{r['pieces']} p." if r.get("pieces") is not None else "p. ?"
                st.markdown(
                    f"- **{r['type_local']}** · **{r['surface']} m²** · **{pieces_txt}** · **{eur(r['prix'])}** · "
                    f"**{r['mois']}** · **{r['commune']}** (~{r['dist']} m)"
                )
            st.markdown("</div>", unsafe_allow_html=True)
