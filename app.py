import streamlit as st
import numpy as np
import pandas as pd
import requests
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# ===========================
# Config
# ===========================
st.set_page_config(
    page_title="EstimeClermont",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PRIMARY = "#004D7F"
ACCENT = "#FF7E79"
SOFT = "#EAF2FF"

MIN_PROGRESS_SECONDS = 5.2

GARE_LON = 2.41767
GARE_LAT = 49.38531

# URL de prise de RDV — remplace par ton lien Calendly / Cal.com / etc.
BOOKING_URL = "https://hakimremax.youcanbook.me/"

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

GEOPF_COMPLETION_URL = "https://data.geopf.fr/geocodage/completion/"
GEOPF_SEARCH_URL = "https://data.geopf.fr/geocodage/search"

DVF_LOCAL_PATH = Path("data/dvf_local.parquet")
DVF_CACHE_BUSTER = "v9"

# ===========================
# Session state
# ===========================
st.session_state.setdefault("geo", None)
st.session_state.setdefault("result_payload", None)
st.session_state.setdefault("area_name", AUTO_AREA)
st.session_state.setdefault("area_locked", False)
st.session_state.setdefault("detected_area", DEFAULT_AREA)
st.session_state.setdefault("bien_type", None)
st.session_state.setdefault("surface", 0.0)
st.session_state.setdefault("etat", None)
st.session_state.setdefault("nb_pieces", 0)
st.session_state.setdefault("nb_chambres", 0)
st.session_state.setdefault("addr_typed", "")
st.session_state.setdefault("addr_choice_display", "")
st.session_state.setdefault("addr_choice", "")
st.session_state.setdefault("prenom", "")
st.session_state.setdefault("email", "")
st.session_state.setdefault("consent", False)

# ===========================
# Debug mode
# ===========================
DEBUG = False
try:
    DEBUG = (st.query_params.get("debug", "0") == "1")
except Exception:
    DEBUG = False

# ===========================
# CSS
# ===========================
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

html, body, [class*="stApp"] {{
  font-family: 'Poppins', sans-serif !important;
}}

.main {{ background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%); }}

h1 {{
    color: {PRIMARY} !important;
    font-weight: 800 !important;
    text-align: center !important;
    margin-bottom: 0.2rem !important;
}}
h2, h3 {{
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

/* ---- Bouton principal : texte bien visible ---- */
.stButton > button,
.stFormSubmitButton > button {{
    background: linear-gradient(135deg, {ACCENT} 0%, #ff5b66 100%) !important;
    color: white !important;
    font-weight: 900 !important;
    border-radius: 14px !important;
    border: none !important;
    padding: 1.1rem 1.2rem !important;
    font-size: 1.22rem !important;
    box-shadow: 0 10px 26px rgba(255, 126, 121, 0.35) !important;
    line-height: 1.3 !important;
}}
/* fix Streamlit wrapping le texte dans un <p> imbriqué */
.stFormSubmitButton > button > div > p,
.stFormSubmitButton > button > div,
.stButton > button > div > p,
.stButton > button > div {{
    font-size: 1.22rem !important;
    font-weight: 900 !important;
    letter-spacing: 0.01em !important;
    color: white !important;
}}

/* Bouton de RDV secondaire */
.booking-btn a {{
    display: block;
    text-align: center;
    background: linear-gradient(135deg, {PRIMARY} 0%, #0066aa 100%);
    color: white !important;
    font-weight: 800;
    font-size: 1.08rem;
    border-radius: 14px;
    padding: 1.0rem 1.5rem;
    text-decoration: none !important;
    box-shadow: 0 8px 22px rgba(0, 77, 127, 0.28);
    margin-top: 0.5rem;
    transition: opacity 0.2s;
}}
.booking-btn a:hover {{ opacity: 0.88; }}

.tension-box {{
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin: 0.6rem 0;
    border-left: 4px solid {ACCENT};
    background: #fff8f8;
    font-size: 0.96rem;
    line-height: 1.55;
}}
</style>
""",
    unsafe_allow_html=True,
)

# ===========================
# Helpers
# ===========================
def norm(s: str) -> str:
    return (s or "").strip().lower().replace("'", "'")

def eur(x: float) -> str:
    return f"{x:,.0f} €".replace(",", " ")

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dl / 2) ** 2
    return float(2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))

def get_effective_area() -> Tuple[str, Dict[str, str]]:
    if st.session_state.area_name in AREAS:
        a = st.session_state.area_name
        return a, AREAS[a]
    detected = st.session_state.get("detected_area")
    if detected in AREAS:
        return detected, AREAS[detected]
    return DEFAULT_AREA, AREAS[DEFAULT_AREA]

def normalize_query_to_area(q: str, city: str, postcode: str) -> str:
    q = (q or "").strip()
    if not q:
        return q
    low = norm(q)
    if postcode not in low and norm(city) not in low:
        q = f"{q}, {postcode} {city}, Oise, France"
    return q

def parse_display_choice(display_value: str) -> Tuple[Optional[str], str]:
    s = (display_value or "").strip()
    for sep in [" — ", "—", " - ", "-"]:
        if sep in s:
            a, lab = s.split(sep, 1)
            a, lab = a.strip(), lab.strip()
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

def normalize_type_local(x: Any) -> str:
    s = str(x or "").strip().lower().replace("'", "'")
    if "appart" in s:
        return "Appartement"
    if "maison" in s:
        return "Maison"
    return "Autre"

def tension_context_message(tscore: int) -> str:
    if tscore >= 75:
        return (
            "🔥 <b>Votre secteur est actuellement très recherché.</b> Les biens similaires partent vite "
            "et les prix se tiennent bien. C'est le bon moment pour vendre, à condition de bien positionner le prix dès le départ."
        )
    elif tscore >= 55:
        return (
            "⚡ <b>Le marché est actif sur votre secteur.</b> Les acheteurs sont présents, "
            "mais ils comparent. Une mise en valeur soignée et un prix juste feront toute la différence."
        )
    elif tscore >= 35:
        return (
            "🙂 <b>Le marché est équilibré.</b> Ni en surchauffe, ni en pause. "
            "Les biens bien présentés et correctement prix se vendent sans trop traîner."
        )
    else:
        return (
            "🧊 <b>Le marché est plus calme en ce moment.</b> Ça ne veut pas dire que votre bien ne se vendra pas, "
            "ça veut dire que la stratégie de prix et la présentation vont compter encore plus que d'habitude."
        )

# ===========================
# KIT (ConvertKit) intégration
# ===========================
def add_to_kit(prenom: str, email: str, area: str, bien_type: str, surface: float) -> bool:
    """
    Ajoute le contact dans KIT (ConvertKit) via l'API v3.
    Nécessite dans .streamlit/secrets.toml :
        KIT_API_KEY = "ton_api_key"
        KIT_FORM_ID = "ton_form_id"
    """
    try:
        api_key = st.secrets.get("KIT_API_KEY", "")
        form_id = st.secrets.get("KIT_FORM_ID", "")
        if not api_key or not form_id:
            return False

        url = f"https://api.convertkit.com/v3/forms/{form_id}/subscribe"
        payload = {
            "api_key": api_key,
            "email": email,
            "first_name": prenom,
            "fields": {
                "commune": area,
                "type_bien": bien_type,
                "surface": str(int(surface)),
                "source": "EstimeClermont",
            },
            "tags": ["EstimeClermont"],
        }
        r = requests.post(url, json=payload, timeout=8)
        return r.status_code == 200
    except Exception:
        return False

# ===========================
# Geocodage & DVF
# ===========================
@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
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

@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def load_dvf_local(_bust: str = DVF_CACHE_BUSTER) -> pd.DataFrame:
    if not DVF_LOCAL_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(DVF_LOCAL_PATH)
    df["date_mutation"] = pd.to_datetime(df.get("date_mutation"), errors="coerce")
    df["valeur_fonciere"] = pd.to_numeric(df.get("valeur_fonciere"), errors="coerce")
    df["surface_reelle_bati"] = pd.to_numeric(df.get("surface_reelle_bati"), errors="coerce")
    df["longitude"] = pd.to_numeric(df.get("longitude"), errors="coerce")
    df["latitude"] = pd.to_numeric(df.get("latitude"), errors="coerce")
    if "type_local" in df.columns:
        df["type_local_raw"] = df["type_local"]
    else:
        df["type_local_raw"] = None
        df["type_local"] = None
    df["type_local"] = df["type_local_raw"].apply(normalize_type_local)
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

    df["type_local"] = df["type_local"].apply(normalize_type_local)
    df = df[df["type_local"] == target_type].copy()
    if df.empty:
        return pd.DataFrame(), 0, 0.0

    lat_arr = df["latitude"].to_numpy(dtype=float)
    lon_arr = df["longitude"].to_numpy(dtype=float)
    lat0, lon0 = float(lat), float(lon)

    R = 6371000.0
    phi1 = np.radians(lat0)
    phi2 = np.radians(lat_arr)
    dphi = np.radians(lat_arr - lat0)
    dl = np.radians(lon_arr - lon0)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dl / 2) ** 2
    dist = 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    df["distance_m"] = dist

    radii = [600, 900, 1500, 2500, 3500]
    if target_type == "Appartement":
        tolerances = [0.20, 0.25, 0.30, 0.35]
        min_needed = 4
    else:
        tolerances = [0.25, 0.30, 0.40, 0.45]
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

def reliability_label(n: int) -> str:
    if n > 15:
        return "🟢 Très élevée"
    if n >= 8:
        return "🟢 Élevée"
    if n >= 4:
        return "🟡 Bonne"
    if n >= 2:
        return "🟠 Modérée"
    return "🔴 Faible"

def market_tension_index(df_local: pd.DataFrame, used_radius: int) -> Dict[str, Any]:
    if df_local is None or df_local.empty or used_radius <= 0:
        return {"score": 0, "label": "🔴 Inconnu", "detail": "Pas assez de données"}

    n = int(len(df_local))
    area_km2 = np.pi * (used_radius / 1000.0) ** 2
    density = n / max(1e-6, area_km2)

    last_date = pd.to_datetime(df_local["date_mutation"]).max()
    days_since = (pd.Timestamp.utcnow().tz_localize(None) - pd.to_datetime(last_date).tz_localize(None)).days
    days_since = int(max(0, days_since))

    pm2 = pd.to_numeric(df_local.get("prix_m2"), errors="coerce")
    pm2 = pm2.replace([np.inf, -np.inf], np.nan).dropna()
    if pm2.empty:
        iqr_ratio = 1.0
    else:
        q25 = float(pm2.quantile(0.25))
        q75 = float(pm2.quantile(0.75))
        iqr = max(1.0, q75 - q25)
        med = max(1.0, float(pm2.median()))
        iqr_ratio = iqr / med

    density_score = 100.0 * (1 - np.exp(-density / 18.0))
    recency_score = 100.0 * np.exp(-days_since / 95.0)
    dispersion_score = 100.0 * np.exp(-iqr_ratio / 0.18)

    score = 0.45 * density_score + 0.35 * recency_score + 0.20 * dispersion_score
    score = float(clamp(score, 0.0, 100.0))

    if score >= 75:
        label = "🔥 Très attractif"
    elif score >= 55:
        label = "⚡ Attractif"
    elif score >= 35:
        label = "🙂 Équilibré"
    else:
        label = "🧊 Plus calme"

    detail = f"Densité ~{density:.1f}/km² · Dernière vente {days_since}j · Dispersion IQR ~{iqr_ratio:.2f}"
    return {"score": int(round(score)), "label": label, "detail": detail}

def compute_adjustments(bien_type: str, surface: float, nb_pieces: int, nb_chambres: int, etat: str, distance_m: float) -> Dict[str, float]:
    etat_factor = {"À rénover": 0.88, "Moyen": 1.00, "Bon": 1.05, "Rénové": 1.10}.get(etat, 1.00)
    pieces_delta = (nb_pieces - 3) * 0.015
    chambres_delta = (nb_chambres - 2) * 0.02
    pieces_factor = float(clamp(1.0 + pieces_delta, 0.93, 1.08))
    chambres_factor = float(clamp(1.0 + chambres_delta, 0.94, 1.10))
    gare_factor = 1 + min(0.06, 0.45 / (1 + distance_m / 1000))
    if bien_type == "Appartement":
        scale = float(clamp(1.02 - (surface - 55) * 0.0009, 0.94, 1.06))
    else:
        scale = float(clamp(1.02 - (surface - 95) * 0.0007, 0.93, 1.06))
    return {"etat": etat_factor, "pieces": pieces_factor, "chambres": chambres_factor, "gare": float(gare_factor), "scale": scale}

def band_from_reliability_and_tension(n: int, tension_score: int, bien_type: str) -> Tuple[float, Tuple[float, float]]:
    if n > 15:
        pct = 0.060
    elif n >= 8:
        pct = 0.070
    elif n >= 4:
        pct = 0.085
    elif n >= 2:
        pct = 0.105
    else:
        pct = 0.140

    if tension_score >= 75:
        pct *= 0.90
    elif tension_score >= 55:
        pct *= 0.95
    elif tension_score >= 35:
        pct *= 1.00
    else:
        pct *= 1.08

    if normalize_type_local(bien_type) == "Appartement":
        abs_min, abs_max = 6500.0, 15000.0
    else:
        abs_min, abs_max = 9000.0, 22000.0

    return float(pct), (float(abs_min), float(abs_max))

def compute_micro_market_estimate(
    df_all: pd.DataFrame,
    lat: float,
    lon: float,
    bien_type: str,
    surface: float,
    nb_pieces: int,
    nb_chambres: int,
    etat: str,
) -> Dict[str, Any]:
    distance_m = haversine_m(lat, lon, GARE_LAT, GARE_LON)
    quartier = quartier_from_distance(distance_m)

    df_local, used_radius, used_tol = dvf_select_similaires_strict(df_all, lat, lon, bien_type, surface)

    target_type = normalize_type_local(bien_type)
    if not df_local.empty:
        df_local["type_local"] = df_local["type_local"].apply(normalize_type_local)
        df_local = df_local[df_local["type_local"] == target_type].copy()
        tol = float(used_tol or (0.35 if target_type == "Appartement" else 0.45))
        lo = surface * (1 - tol)
        hi = surface * (1 + tol)
        df_local = df_local[(df_local["surface_reelle_bati"] >= lo) & (df_local["surface_reelle_bati"] <= hi)].copy()
        df_local["prix_m2"] = df_local["valeur_fonciere"] / df_local["surface_reelle_bati"]
        df_local = df_local.replace([np.inf, -np.inf], np.nan).dropna(subset=["prix_m2"])
        df_local = df_local.drop_duplicates(
            subset=["date_mutation", "valeur_fonciere", "surface_reelle_bati", "type_local", "nom_commune"],
            keep="first",
        )

    n = int(len(df_local))
    rel = reliability_label(n)

    if n >= 2:
        pm2_med = float(df_local["prix_m2"].median())
    elif n == 1:
        pm2_med = float(df_local["prix_m2"].iloc[0])
    else:
        base_table = {
            "Centre-ville": {"Maison": 2100, "Appartement": 2500},
            "Nord (Gare)": {"Maison": 1950, "Appartement": 2200},
            "Sud (Résidentiel)": {"Maison": 2350, "Appartement": 2700},
            "Est (Pavillons)": {"Maison": 2000, "Appartement": 2300},
            "Ouest (Neuf)": {"Maison": 2450, "Appartement": 2800},
        }
        pm2_med = float(base_table[quartier][target_type])

    base_price = pm2_med * surface
    adj = compute_adjustments(target_type, surface, nb_pieces, nb_chambres, etat, distance_m)
    adj_factor = adj["etat"] * adj["pieces"] * adj["chambres"] * adj["gare"] * adj["scale"]

    tension = market_tension_index(df_local, used_radius if used_radius else 0)
    tscore = int(tension.get("score", 0))

    if tscore >= 75:
        tilt = 0.022
    elif tscore >= 55:
        tilt = 0.012
    elif tscore >= 35:
        tilt = 0.0
    else:
        tilt = -0.018

    center = base_price * adj_factor * (1.0 + tilt)

    band_pct, (abs_min, abs_max) = band_from_reliability_and_tension(n, tscore, target_type)
    full_width = max(1.0, center * band_pct)
    full_width = clamp(full_width, abs_min, abs_max)

    est_min = center - full_width / 2.0
    est_max = center + full_width / 2.0
    est_min = float(est_min)
    est_max = float(est_max)
    if not np.isfinite(est_min) or not np.isfinite(est_max):
        est_min, est_max = center * 0.93, center * 1.07
    if est_min > est_max:
        est_min, est_max = est_max, est_min

    max_date = df_all["date_mutation"].max()
    last_update = max_date.strftime("%B %Y") if pd.notna(max_date) else "—"

    # Preview + coordonnées GPS pour la carte
    preview = []
    map_points = []
    if not df_local.empty:
        prev = df_local.sort_values(["distance_m", "date_mutation"], ascending=[True, False]).head(6)
        for _, r in prev.iterrows():
            try:
                mois = pd.to_datetime(r["date_mutation"]).strftime("%m/%Y")
            except Exception:
                mois = "—"
            preview.append({
                "type_local": str(r.get("type_local", "")),
                "surface": int(round(float(r.get("surface_reelle_bati", 0)))),
                "prix": float(r.get("valeur_fonciere", 0)),
                "mois": mois,
                "commune": str(r.get("nom_commune", "Secteur")),
                "dist": int(round(float(r.get("distance_m", 0)) / 100.0) * 100),
            })
            # Points pour la mini-carte (légèrement floutés : ~50m aléatoire)
            rng = np.random.default_rng(seed=int(r.get("valeur_fonciere", 0)) % 9999)
            jitter_lat = rng.uniform(-0.0005, 0.0005)
            jitter_lon = rng.uniform(-0.0005, 0.0005)
            map_points.append({
                "lat": float(r["latitude"]) + jitter_lat,
                "lon": float(r["longitude"]) + jitter_lon,
            })

    return {
        "bien_type": target_type,
        "surface": float(surface),
        "quartier": quartier,
        "distance_gare_m": int(round(distance_m)),
        "pm2_med": float(pm2_med),
        "adj": adj,
        "adj_factor": float(adj_factor),
        "tilt": float(tilt),
        "est_min": float(est_min),
        "est_max": float(est_max),
        "n": int(n),
        "used_radius": int(used_radius or 0),
        "used_tol": float(used_tol or 0.0),
        "reliability": rel,
        "tension": tension,
        "last_update": last_update,
        "preview": preview,
        "map_points": map_points,
    }

# ===========================
# Debug tools
# ===========================
if DEBUG:
    with st.expander("🧹 Outils (debug)", expanded=False):
        cols = st.columns([1, 1])
        with cols[0]:
            if st.button("Vider le cache Streamlit"):
                st.cache_data.clear()
                st.success("Cache vidé. Rechargement…")
                st.rerun()
        with cols[1]:
            if st.button("Forcer reload DVF"):
                st.session_state["_dvf_bust_manual"] = str(time.time())
                st.cache_data.clear()
                st.success("DVF reload forcé.")
                st.rerun()
        st.caption(f"DVF cache buster: {DVF_CACHE_BUSTER}")

# ===========================
# Header
# ===========================
effective_area, effective_info = get_effective_area()
badge_label = f"{effective_area} ({effective_info['postcode']})"

st.markdown("<h1>Combien vaut vraiment votre bien à Clermont-de-l'Oise ?</h1>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center; margin-bottom:0.6rem;'>"
    "<span class='small-note'><b>Pas une estimation au doigt mouillé.</b> Une vraie fourchette, basée sur les ventes réelles de votre quartier.</span>"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div style='text-align:center; margin-bottom:0.6rem;'><span class='badge'>Secteur : {badge_label}</span></div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='card accent-top'><b>Objectif :</b> En 2 minutes, vous obtenez une estimation basée sur les dernières ventes de biens similaires "
    "dans votre secteur, pas sur un algorithme générique qui confond Clermont-de-l'Oise avec Clermont-Ferrand 😃</div>",
    unsafe_allow_html=True,
)
st.markdown("<hr/>", unsafe_allow_html=True)

# ===========================
# Layout
# ===========================
colL, colR = st.columns([1.25, 0.95], gap="large")

with colR:
    st.markdown("## Ce que vous recevez")
    st.markdown(
        "<div class='card accent-top'>"
        "✅ Une fourchette de prix réaliste, basée sur les ventes récentes de votre secteur<br/>"
        "✅ Le prix médian au m² pratiqué dans votre quartier ces 12 derniers mois<br/>"
        "✅ Des biens comparables au vôtre (même type, surface similaire, même zone)<br/>"
        "✅ Un indice d'attractivité de votre secteur (est-ce que les biens partent vite ?)<br/>"
        "✅ Une estimation affinée selon l'état, la surface, les pièces et la localisation"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='card soft'>"
        "🔎 <b>Une estimation honnête, pas magique.</b> Les données viennent des ventes officiellement enregistrées "
        "(source : data.gouv.fr, màj novembre 2025). Certaines infos comme le nombre de pièces ne sont pas toujours "
        "disponibles dans ces données, donc on croise avec ce que vous nous indiquez pour rester au plus juste. "
        "Pas de chiffre sorti du chapeau."
        "</div>",
        unsafe_allow_html=True,
    )

with colL:
    st.markdown("## Parlez-moi de votre bien")

    # Commune
    area_options = [AUTO_AREA] + list(AREAS.keys())
    st.selectbox("Votre commune", area_options, key="area_name")

    if st.session_state.area_name in AREAS:
        st.session_state.detected_area = st.session_state.area_name
        st.session_state.area_locked = True
    else:
        if st.session_state.get("detected_area") not in AREAS:
            st.session_state.detected_area = DEFAULT_AREA

    effective_area, ai = get_effective_area()
    st.markdown(
        f"<div class='card soft'><b>Commune utilisée :</b> {effective_area} — <b>CP :</b> {ai['postcode']}</div>",
        unsafe_allow_html=True,
    )

    # Adresse (hors form pour permettre le callback)
    st.markdown("### 📍 Adresse du bien")
    st.text_input("Adresse du bien", placeholder="Ex : 5 Rue du Chemin Blanc", key="addr_typed")

    typed = (st.session_state.addr_typed or "").strip()
    suggestions_display: List[str] = []

    if len(typed) >= 3:
        if st.session_state.area_name == AUTO_AREA:
            for area_name, info in AREAS.items():
                try:
                    labs = geopf_completion(typed, postcode=info["postcode"], city=info["city"], max_resp=5)
                except Exception:
                    labs = []
                for lab in labs:
                    suggestions_display.append(f"{area_name} — {lab}")
        else:
            try:
                labs = geopf_completion(typed, postcode=ai["postcode"], city=ai["city"], max_resp=8)
            except Exception:
                labs = []
            suggestions_display = labs[:]

    if suggestions_display:
        prev_display = st.session_state.get("addr_choice_display", "")
        default_index = suggestions_display.index(prev_display) if prev_display in suggestions_display else 0
        st.selectbox(
            "Suggestions",
            suggestions_display,
            index=default_index,
            key="addr_choice_display",
            on_change=on_addr_choice_display_change,
        )
    else:
        st.session_state.addr_choice_display = ""
        st.session_state.addr_choice = ""

    st.markdown("<hr/>", unsafe_allow_html=True)

    # Form principal
    with st.form("one_step_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            st.selectbox("Mon bien est...", ["Maison", "Appartement"], index=None, key="bien_type", placeholder="Choisir…")
            st.number_input("Surface habitable (m²)", min_value=0.0, max_value=500.0, step=1.0,
                            value=float(st.session_state.surface or 0.0), key="surface")
            st.selectbox("État général du bien", ["À rénover", "Moyen", "Bon", "Rénové"],
                         index=None, key="etat", placeholder="Choisir…")
        with c2:
            st.number_input("Nombre de pièces", min_value=0, max_value=12, step=1,
                            value=int(st.session_state.nb_pieces or 0), key="nb_pieces")
            st.number_input("Dont chambres", min_value=0, max_value=10, step=1,
                            value=int(st.session_state.nb_chambres or 0), key="nb_chambres")
            st.markdown(
                "<div class='small-note'>L'état influe sur le prix final. "
                "Promis, on ne vous juge pas si c'est \"à rénover\" 😄</div>",
                unsafe_allow_html=True,
            )

        st.markdown("### Où envoyer votre estimation ?")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.text_input("Votre prénom", key="prenom", placeholder="Ex : Marie")
        with cc2:
            st.text_input("Votre email", key="email", placeholder="exemple@mail.com")

        st.checkbox(
            "J'accepte de recevoir cette estimation par email et qu'Hakim me contacte si besoin pour l'affiner. "
            "Pas de spam, pas de relance tous les matins. Promis 🙂",
            key="consent",
        )

        submitted = st.form_submit_button(
            "✨ Voir l'estimation de mon bien →",
            use_container_width=True,
        )

    # Validation & calcul
    if submitted:
        missing = []
        if st.session_state.bien_type not in ["Maison", "Appartement"]:
            missing.append("Type de bien")
        if float(st.session_state.surface or 0) <= 0:
            missing.append("Surface habitable")
        if st.session_state.etat not in ["À rénover", "Moyen", "Bon", "Rénové"]:
            missing.append("État général")
        if int(st.session_state.nb_pieces or 0) <= 0:
            missing.append("Nombre de pièces")
        if not st.session_state.prenom:
            missing.append("Prénom")
        if not st.session_state.email or "@" not in st.session_state.email:
            missing.append("Email valide")
        if not st.session_state.consent:
            missing.append("Autorisation de contact")
        if not st.session_state.addr_choice_display:
            missing.append("Adresse (sélectionnez une suggestion dans la liste)")

        if missing:
            st.error("Il manque les éléments suivants : " + ", ".join(missing))
            st.stop()

        effective_area, ai = get_effective_area()
        detected_area, detected_label = parse_display_choice(st.session_state.get("addr_choice_display", ""))
        addr_label = detected_label if detected_label else (st.session_state.addr_choice or typed)

        if st.session_state.area_name == AUTO_AREA and detected_area:
            st.session_state.detected_area = detected_area
            st.session_state.area_locked = True
            effective_area, ai = get_effective_area()

        q = normalize_query_to_area(addr_label, city=ai["city"], postcode=ai["postcode"])
        try:
            geo = geopf_geocode_one(q)
        except Exception:
            geo = None

        if not geo:
            st.error("Impossible de localiser cette adresse. Choisis une suggestion précise (numéro + rue) et réessaie.")
            st.stop()

        label_low = norm(geo.get("label") or "")
        if ai["postcode"] not in label_low or norm(ai["city"]) not in label_low:
            st.error("Cette adresse ne correspond pas à la commune sélectionnée. Choisis une suggestion de la bonne zone.")
            st.stop()

        t0 = time.time()
        progress = st.progress(0, text="🔎 Analyse des ventes récentes autour de votre bien…")

        def progress_step(pct: int, txt: str, min_sleep: float = 0.35):
            progress.progress(pct, text=txt)
            time.sleep(min_sleep)

        try:
            progress_step(10, "📦 Chargement des ventes officielles (DVF)…", 0.65)
            df_all = load_dvf_local(st.session_state.get("_dvf_bust_manual", DVF_CACHE_BUSTER))
            if df_all.empty:
                st.warning("⚠️ Base DVF locale introuvable. Le fichier parquet est manquant.")
                st.markdown(
                    "**Vous pouvez me contacter directement pour une estimation personnalisée :**<br>"
                    "<a href='mailto:hakim@immoclermontoise.fr'>hakim@immoclermontoise.fr</a>",
                    unsafe_allow_html=True,
                )
                st.stop()

            progress_step(40, "🏡 Recherche de biens similaires dans votre secteur…", 1.1)
            progress_step(65, "📐 Calcul des ajustements (état, surface, localisation)…", 1.0)

            payload = compute_micro_market_estimate(
                df_all=df_all,
                lat=float(geo["lat"]),
                lon=float(geo["lon"]),
                bien_type=str(st.session_state.bien_type),
                surface=float(st.session_state.surface),
                nb_pieces=int(st.session_state.nb_pieces),
                nb_chambres=int(st.session_state.nb_chambres),
                etat=str(st.session_state.etat),
            )

            progress_step(82, "📊 Calcul de la fourchette et de l'attractivité du secteur…", 1.0)

            dt = time.time() - t0
            if dt < MIN_PROGRESS_SECONDS:
                time.sleep(MIN_PROGRESS_SECONDS - dt)

            progress.progress(100, text="✅ Votre estimation est prête !")
            time.sleep(0.3)

            st.session_state.geo = geo
            st.session_state.result_payload = payload

            # Envoi vers KIT
            add_to_kit(
                prenom=st.session_state.prenom,
                email=st.session_state.email,
                area=effective_area,
                bien_type=str(st.session_state.bien_type),
                surface=float(st.session_state.surface),
            )

        finally:
            progress.empty()

        st.success(f"Merci {st.session_state.prenom} ✅ Votre estimation est prête.")
        st.rerun()

# ===========================
# Résultats
# ===========================
if st.session_state.result_payload and st.session_state.geo:
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown("## ✨ Votre estimation")

    geo = st.session_state.geo
    hp = st.session_state.result_payload
    tens = hp.get("tension", {})
    tscore = int(tens.get("score", 0))

    # Métriques principales
    m1, m2, m3 = st.columns(3, gap="medium")
    with m1:
        st.markdown(
            f"<div class='metric'><p class='k'>Fourchette estimée</p><p class='v'>{eur(hp['est_min'])} – {eur(hp['est_max'])}</p></div>",
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f"<div class='metric'><p class='k'>Fiabilité des données</p><p class='v'>{hp['reliability']}</p></div>",
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f"<div class='metric'><p class='k'>Attractivité du secteur</p><p class='v'>{tens.get('label','—')} ({tscore}/100)</p></div>",
            unsafe_allow_html=True,
        )

    # Résumé technique
    st.markdown(
        f"<div class='card soft'>"
        f"<b>Adresse analysée :</b> {geo.get('label','')}<br/>"
        f"<b>Zone (proxy) :</b> {hp.get('quartier','—')} — <b>Distance gare :</b> {hp.get('distance_gare_m','—')} m<br/>"
        f"<b>Prix médian au m² (ventes réelles) :</b> ~{eur(hp.get('pm2_med',0))} / m²<br/>"
        f"<b>Biens comparables trouvés :</b> {hp.get('n',0)} ventes (12 mois glissants) — rayon max : {hp.get('used_radius','—')} m"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Message contextuel marché (personnalisé selon score de tension)
    st.markdown(
        f"<div class='tension-box'>{tension_context_message(tscore)}</div>",
        unsafe_allow_html=True,
    )

    # Mini-carte des comparables
    map_points = hp.get("map_points", [])
    if map_points:
        st.markdown("### 🗺️ Localisation des ventes comparables")
        st.caption("Les points représentent des biens vendus récemment près du vôtre (position légèrement floue pour respecter la vie privée des vendeurs).")
        map_df = pd.DataFrame(map_points)
        # Ajouter le bien estimé avec une couleur distincte
        bien_point = pd.DataFrame([{"lat": float(geo["lat"]), "lon": float(geo["lon"])}])
        st.map(pd.concat([bien_point, map_df], ignore_index=True), zoom=14)

    # Disclaimer
    st.markdown(
        "<div class='card accent-top'>"
        "<b>Important — ce que cette estimation ne peut pas mesurer sans visite :</b><br><br>"
        "– Les nuisances (route, voisinage, bruit, vis-à-vis…)<br>"
        "– La luminosité et l'exposition<br>"
        "– L'état réel et la qualité des finitions<br>"
        "– Les travaux déjà faits ou à prévoir, isolation, DPE<br>"
        "– L'agencement, les volumes, l'entretien<br>"
        "– Les extérieurs, cave, garage, stationnement, copropriété, charges…<br><br>"
        "Cette fourchette est une <b>base solide et honnête</b>. Mais pour un chiffre vraiment précis "
        "et des conseils adaptés à votre projet, rien ne vaut un échange de vive voix."
        "</div>",
        unsafe_allow_html=True,
    )

    # CTA prise de RDV
    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='booking-btn'>"
        f"<a href='{BOOKING_URL}' target='_blank'>"
        f"📞 Affiner cette estimation avec Hakim — RDV gratuit, sans engagement"
        f"</a></div>",
        unsafe_allow_html=True,
    )
    st.caption("Un échange de 20 minutes pour vous donner un chiffre vraiment précis et vous expliquer comment valoriser votre bien.")

    if tens.get("detail"):
        st.caption(f"📌 Données tension : {tens['detail']}")

    # Exemples de comparables
    if hp.get("preview"):
        with st.expander("🧾 Voir les exemples de biens comparables (position volontairement vague)"):
            for r in hp["preview"]:
                st.markdown(
                    f"- **{r['type_local']}** · **{r['surface']} m²** · **{eur(r['prix'])}** · "
                    f"**{r['mois']}** · **{r['commune']}** (~{r['dist']} m)"
                )

    if DEBUG:
        with st.expander("🧪 Debug payload", expanded=False):
            st.write(hp)
            st.write("geo:", geo)
