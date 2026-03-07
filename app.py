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
ACCENT  = "#FF7E79"
SOFT    = "#EAF2FF"

MIN_PROGRESS_SECONDS = 5.2

GARE_LON = 2.41767
GARE_LAT = 49.38531

BOOKING_URL = "https://hakimremax.youcanbook.me/"

AREAS: Dict[str, Dict[str, str]] = {
    "Clermont-de-l'Oise":    {"city": "Clermont",             "postcode": "60600", "insee": "60157"},
    "Breuil-le-Vert":        {"city": "Breuil-le-Vert",       "postcode": "60600", "insee": "60107"},
    "Agnetz":                {"city": "Agnetz",                "postcode": "60600", "insee": "60007"},
    "Fitz-James":            {"city": "Fitz-James",            "postcode": "60600", "insee": "60234"},
    "Breuil-le-Sec":         {"city": "Breuil-le-Sec",         "postcode": "60840", "insee": "60106"},
    "Neuilly-sous-Clermont": {"city": "Neuilly-sous-Clermont", "postcode": "60290", "insee": "60451"},
    "Bailleval":             {"city": "Bailleval",             "postcode": "60140", "insee": "60042"},
}

AUTO_AREA    = "🔎 Détection automatique"
DEFAULT_AREA = "Clermont-de-l'Oise"

# ── Géocodage : on utilise l'API BAN (plus rapide et fiable que Géoplateforme IGN)
BAN_SEARCH_URL     = "https://api-adresse.data.gouv.fr/search/"
BAN_COMPLETION_URL = "https://api-adresse.data.gouv.fr/search/"

DVF_LOCAL_PATH   = Path("data/dvf_local.parquet")
DVF_CACHE_BUSTER = "v9"

# ===========================
# Session state defaults
# ===========================
_defaults = {
    "geo": None, "result_payload": None,
    "area_name": AUTO_AREA, "area_locked": False, "detected_area": DEFAULT_AREA,
    "bien_type": None, "surface": 0.0, "etat": None,
    "nb_pieces": 0, "nb_chambres": 0,
    "addr_typed": "", "addr_choice_display": "", "addr_choice": "",
    "prenom": "", "email": "", "consent": False,
}
for k, v in _defaults.items():
    st.session_state.setdefault(k, v)

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
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

html, body, [class*="stApp"] {{
    font-family: 'Poppins', sans-serif !important;
    font-size: 16px !important;
}}
.main {{ background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%); }}

/* ── Titres de section (h2) — plus grands ── */
h2 {{
    color: {PRIMARY} !important;
    font-weight: 800 !important;
    font-size: 1.75rem !important;
    margin-bottom: 0.8rem !important;
}}
h3 {{
    color: {PRIMARY} !important;
    font-weight: 700 !important;
    font-size: 1.25rem !important;
}}

p, li, span, label {{ font-size: 1rem !important; }}
.small-note {{ color: #4b5563; font-size: 0.93rem !important; line-height: 1.5; }}

.badge {{
    display: inline-block; padding: 0.35rem 0.85rem; border-radius: 999px;
    background: rgba(0,77,127,0.10); color: {PRIMARY};
    font-weight: 700; font-size: 0.88rem !important;
}}

/* ── Cards ── */
.card {{
    background: white; border-radius: 16px; padding: 1.2rem 1.3rem;
    box-shadow: 0 10px 26px rgba(0,77,127,0.10);
    border: 1px solid rgba(0,0,0,0.06); overflow: hidden; margin-bottom: 0.9rem;
}}
.card.accent-top {{ border-top: 4px solid {ACCENT}; }}
.card.soft {{
    background: linear-gradient(135deg, {SOFT} 0%, #ffffff 100%);
    border: 1px solid rgba(0,77,127,0.10);
}}
.card ul {{ margin: 0.5rem 0 0 0; padding-left: 0; list-style: none; }}
.card ul li {{ padding: 0.32rem 0; font-size: 0.97rem !important; }}

/* ── Disclaimer avec flèches saumon ── */
.disclaimer-list {{
    list-style: none; padding-left: 0; margin: 0.6rem 0 1rem 0;
}}
.disclaimer-list li {{
    padding: 0.28rem 0;
    font-size: 0.97rem !important;
    display: flex; align-items: flex-start; gap: 0.5rem;
}}
.disclaimer-list li::before {{
    content: "→";
    color: {ACCENT};
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 0.05rem;
}}

/* ── Métriques résultats ── */
.metric {{
    background: linear-gradient(135deg, {ACCENT} 0%, #ff5b66 100%);
    color: white; border-radius: 16px; padding: 1.2rem 1.3rem;
    box-shadow: 0 12px 28px rgba(255,126,121,0.28); margin-bottom: 0.8rem;
}}
.metric .k {{ font-size: 0.88rem !important; opacity: 0.95; margin: 0; }}
.metric .v {{ font-size: 1.55rem !important; font-weight: 850; margin: 0.15rem 0 0 0; letter-spacing: -0.02em; }}

hr {{ border: none; border-top: 1px solid rgba(0,0,0,0.08); margin: 1.3rem 0; }}
.form-divider {{ border: none; border-top: 1px solid #e5e7eb; margin: 1.3rem 0 1.1rem 0; }}

/* ── Inputs redesignés ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {{
    height: 50px !important;
    font-size: 1rem !important;
    padding: 0 1rem !important;
    line-height: 50px !important;
    border-radius: 12px !important;
    border: 2px solid #e5e7eb !important;
    background: white !important;
    color: #111827 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
    transition: border-color 0.18s, box-shadow 0.18s !important;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {{
    border-color: {PRIMARY} !important;
    box-shadow: 0 0 0 3px rgba(0,77,127,0.13) !important;
    outline: none !important;
}}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stNumberInput"] input::placeholder {{
    color: #9ca3af !important;
    font-size: 0.93rem !important;
}}

/* Masque "Press Enter to submit" */
[data-testid="InputInstructions"] {{ display: none !important; }}

/* ── Selectbox redesigné ── */
[data-testid="stSelectbox"] > div > div > div {{
    min-height: 50px !important;
    border-radius: 12px !important;
    font-size: 1rem !important;
    border: 2px solid #e5e7eb !important;
    background: white !important;
    color: #111827 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
    display: flex !important;
    align-items: center !important;
    padding: 0 0.9rem !important;
}}

/* ── Labels widgets ── */
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label {{
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: #374151 !important;
    margin-bottom: 0.25rem !important;
}}

/* ── Checkbox ── */
[data-testid="stCheckbox"] label p {{ font-size: 0.93rem !important; color: #4b5563 !important; }}

/* ── Bouton CTA — texte vraiment visible ── */
.stButton > button {{
    background: linear-gradient(135deg, {ACCENT} 0%, #ff5b66 100%) !important;
    color: white !important;
    border-radius: 14px !important;
    border: none !important;
    padding: 0.95rem 1.4rem !important;
    box-shadow: 0 10px 26px rgba(255,126,121,0.35) !important;
    transition: opacity 0.2s, transform 0.1s !important;
    width: 100%;
    min-height: 58px !important;
}}
/* Cible TOUS les niveaux de wrapping que Streamlit peut créer */
.stButton > button,
.stButton > button *,
.stButton > button span,
.stButton > button p,
.stButton > button div {{
    font-size: 1.18rem !important;
    font-weight: 900 !important;
    letter-spacing: 0.01em !important;
    color: white !important;
    line-height: 1.3 !important;
}}
.stButton > button:hover:not(:disabled) {{
    opacity: 0.92 !important;
    transform: translateY(-1px) !important;
}}
.stButton > button:disabled,
.stButton > button:disabled *,
.stButton > button:disabled span,
.stButton > button:disabled p,
.stButton > button:disabled div {{
    background: linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%) !important;
    box-shadow: none !important;
    cursor: not-allowed !important;
    transform: none !important;
    color: white !important;
}}

/* ── Bouton RDV ── */
.booking-btn a {{
    display: block; text-align: center;
    background: linear-gradient(135deg, {PRIMARY} 0%, #0066aa 100%);
    color: white !important; font-weight: 800; font-size: 1.08rem !important;
    border-radius: 14px; padding: 1.0rem 1.5rem;
    text-decoration: none !important;
    box-shadow: 0 8px 22px rgba(0,77,127,0.28);
    margin-top: 0.5rem; transition: opacity 0.2s;
}}
.booking-btn a:hover {{ opacity: 0.88; }}

.tension-box {{
    border-radius: 12px; padding: 1rem 1.2rem; margin: 0.6rem 0;
    border-left: 4px solid {ACCENT}; background: #fff8f8;
    font-size: 0.97rem !important; line-height: 1.6;
}}

.form-section-label {{
    font-size: 0.82rem !important; font-weight: 700 !important;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: #9ca3af; margin-bottom: 0.7rem; display: block;
}}

.addr-helper {{
    font-size: 0.85rem !important; color: #6b7280;
    margin-top: -0.3rem; margin-bottom: 0.6rem;
}}

.fields-status {{ font-size: 0.87rem !important; color: #6b7280; text-align: center; margin-top: 0.5rem; }}
.fields-status.ready {{ color: #059669 !important; font-weight: 600 !important; }}
</style>
""", unsafe_allow_html=True)


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
    dl   = np.radians(lon2 - lon1)
    a    = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dl/2)**2
    return float(2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))

def get_effective_area() -> Tuple[str, Dict[str, str]]:
    if st.session_state.area_name in AREAS:
        return st.session_state.area_name, AREAS[st.session_state.area_name]
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
        st.session_state.area_locked   = True

def quartier_from_distance(distance_m: float) -> str:
    if distance_m < 500:  return "Nord (Gare)"
    if distance_m < 1500: return "Centre-ville"
    if distance_m < 2500: return "Sud (Résidentiel)"
    if distance_m < 3500: return "Est (Pavillons)"
    return "Ouest (Neuf)"

def normalize_type_local(x: Any) -> str:
    s = str(x or "").strip().lower().replace("'", "'")
    if "appart" in s: return "Appartement"
    if "maison" in s: return "Maison"
    return "Autre"

def tension_context_message(tscore: int) -> str:
    if tscore >= 75:
        return ("🔥 <b>Votre secteur est actuellement très recherché.</b> Les biens similaires partent vite "
                "et les prix se tiennent bien. C'est le bon moment pour vendre, à condition de bien positionner le prix dès le départ.")
    elif tscore >= 55:
        return ("⚡ <b>Le marché est actif sur votre secteur.</b> Les acheteurs sont présents, "
                "mais ils comparent. Une mise en valeur soignée et un prix juste feront toute la différence.")
    elif tscore >= 35:
        return ("🙂 <b>Le marché est équilibré.</b> Ni en surchauffe, ni en pause. "
                "Les biens bien présentés et correctement positionnés se vendent sans trop traîner.")
    else:
        return ("🧊 <b>Le marché est plus calme en ce moment.</b> Ça ne veut pas dire que votre bien ne se vendra pas — "
                "ça veut dire que la stratégie de prix et la présentation vont compter encore plus que d'habitude.")

def is_form_ready() -> Tuple[bool, int]:
    checks = [
        st.session_state.bien_type in ["Maison", "Appartement"],
        float(st.session_state.surface or 0) > 0,
        st.session_state.etat in ["À rénover", "Moyen", "Bon", "Rénové"],
        int(st.session_state.nb_pieces or 0) > 0,
        bool(st.session_state.addr_choice_display),
        bool(st.session_state.prenom),
        bool(st.session_state.email) and "@" in (st.session_state.email or ""),
        bool(st.session_state.consent),
    ]
    return all(checks), sum(checks)


# ===========================
# KIT (ConvertKit)
# ===========================
def add_to_kit(prenom: str, email: str, area: str, bien_type: str, surface: float) -> bool:
    """
    Envoie le contact dans KIT via l'API v3.
    Prérequis dans .streamlit/secrets.toml (et Streamlit Cloud → Settings → Secrets) :
        KIT_API_KEY = "ta_cle_api"
        KIT_FORM_ID = "ton_form_id"

    IMPORTANT : les custom fields 'commune', 'type_bien', 'surface', 'source'
    doivent être créés manuellement dans KIT → Subscribers → Custom Fields
    AVANT que l'API puisse les remplir.
    """
    try:
        api_key = st.secrets.get("KIT_API_KEY", "")
        form_id = st.secrets.get("KIT_FORM_ID", "")
        if not api_key or not form_id:
            if DEBUG:
                st.warning("KIT : clé API ou form ID manquants dans les secrets.")
            return False

        url = f"https://api.convertkit.com/v3/forms/{form_id}/subscribe"
        payload = {
            "api_key": api_key,
            "email": email,
            "first_name": prenom,
            "fields": {
                "commune":   area,
                "type_bien": bien_type,
                "surface":   str(int(surface)),
                "source":    "EstimeClermont",
            },
        }
        r = requests.post(url, json=payload, timeout=10)
        if DEBUG:
            st.write(f"KIT response {r.status_code}:", r.text[:300])
        return r.status_code in (200, 201)
    except Exception as e:
        if DEBUG:
            st.warning(f"KIT erreur : {e}")
        return False


# ===========================
# Géocodage — API BAN (Base Adresse Nationale)
# Beaucoup plus rapide que Géoplateforme IGN pour les adresses françaises
# ===========================
@st.cache_data(ttl=3600, show_spinner=False)
def ban_completion(text: str, postcode: str, limit: int = 6) -> List[Dict[str, Any]]:
    """
    Autocomplétion via l'API BAN.
    Retourne une liste de dicts {label, lat, lon, city, postcode}.
    """
    if not text or len(text.strip()) < 2:
        return []
    try:
        params = {
            "q":          text.strip(),
            "postcode":   postcode,
            "limit":      limit,
            "autocomplete": 1,
        }
        r = requests.get(BAN_COMPLETION_URL, params=params, timeout=5)
        r.raise_for_status()
        feats = r.json().get("features", [])
        results = []
        for f in feats:
            props  = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates", [])
            if len(coords) < 2:
                continue
            results.append({
                "label":    props.get("label", ""),
                "lat":      float(coords[1]),
                "lon":      float(coords[0]),
                "city":     props.get("city", ""),
                "postcode": props.get("postcode", ""),
            })
        return results
    except Exception:
        return []

@st.cache_data(ttl=86400, show_spinner=False)
def ban_geocode(query: str, postcode: str) -> Optional[Dict[str, Any]]:
    """Géocode une adresse complète via BAN."""
    if not query:
        return None
    try:
        params = {"q": query, "postcode": postcode, "limit": 1}
        r = requests.get(BAN_SEARCH_URL, params=params, timeout=8)
        r.raise_for_status()
        feats = r.json().get("features", [])
        if not feats:
            return None
        f0     = feats[0]
        props  = f0.get("properties", {})
        coords = f0.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            return None
        return {
            "lat":      float(coords[1]),
            "lon":      float(coords[0]),
            "label":    props.get("label", query),
            "postcode": props.get("postcode", postcode),
            "city":     props.get("city", ""),
        }
    except Exception:
        return None


# ===========================
# DVF
# ===========================
@st.cache_data(ttl=6*3600, show_spinner=False)
def load_dvf_local(_bust: str = DVF_CACHE_BUSTER) -> pd.DataFrame:
    if not DVF_LOCAL_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(DVF_LOCAL_PATH)
    for col, fn in [
        ("date_mutation",       lambda x: pd.to_datetime(x, errors="coerce")),
        ("valeur_fonciere",     lambda x: pd.to_numeric(x, errors="coerce")),
        ("surface_reelle_bati", lambda x: pd.to_numeric(x, errors="coerce")),
        ("longitude",           lambda x: pd.to_numeric(x, errors="coerce")),
        ("latitude",            lambda x: pd.to_numeric(x, errors="coerce")),
    ]:
        df[col] = fn(df.get(col))
    df["type_local_raw"] = df.get("type_local")
    df["type_local"]     = df["type_local_raw"].apply(normalize_type_local)
    df = df.dropna(subset=["date_mutation","valeur_fonciere","surface_reelle_bati","longitude","latitude","type_local"])
    df = df[df["type_local"].isin(["Maison","Appartement"])]
    df = df[(df["valeur_fonciere"] > 1000) & (df["surface_reelle_bati"] >= 10)]
    return df

def dvf_select_similaires_strict(df_all, lat, lon, bien_type, surface) -> Tuple[pd.DataFrame, int, float]:
    if df_all.empty:
        return pd.DataFrame(), 0, 0.0
    target_type = normalize_type_local(bien_type)
    surface     = float(surface)
    max_date    = df_all["date_mutation"].max()
    if pd.isna(max_date):
        return pd.DataFrame(), 0, 0.0
    df = df_all[df_all["date_mutation"] >= max_date - pd.Timedelta(days=365)].copy()
    if df.empty:
        return pd.DataFrame(), 0, 0.0
    df["type_local"] = df["type_local"].apply(normalize_type_local)
    df = df[df["type_local"] == target_type].copy()
    if df.empty:
        return pd.DataFrame(), 0, 0.0
    lat0, lon0 = float(lat), float(lon)
    R    = 6371000.0
    phi1 = np.radians(lat0)
    phi2 = np.radians(df["latitude"].to_numpy(float))
    dphi = np.radians(df["latitude"].to_numpy(float)  - lat0)
    dl   = np.radians(df["longitude"].to_numpy(float) - lon0)
    a    = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dl/2)**2
    df["distance_m"] = 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    radii      = [600, 900, 1500, 2500, 3500]
    tolerances = [0.20, 0.25, 0.30, 0.35] if target_type == "Appartement" else [0.25, 0.30, 0.40, 0.45]
    min_needed = 4
    best = pd.DataFrame(); used_radius = 0; used_tol = 0.0
    for rad in radii:
        df_r = df[df["distance_m"] <= rad].copy()
        if df_r.empty:
            continue
        for tol in tolerances:
            lo, hi = surface*(1-tol), surface*(1+tol)
            df_s = df_r[(df_r["surface_reelle_bati"]>=lo)&(df_r["surface_reelle_bati"]<=hi)].copy()
            if df_s.empty:
                continue
            df_s["prix_m2"] = df_s["valeur_fonciere"] / df_s["surface_reelle_bati"]
            df_s = df_s.replace([np.inf,-np.inf], np.nan).dropna(subset=["prix_m2"])
            if len(df_s) >= 10:
                q10, q90 = df_s["prix_m2"].quantile(0.10), df_s["prix_m2"].quantile(0.90)
                df_s = df_s[(df_s["prix_m2"]>=q10)&(df_s["prix_m2"]<=q90)]
            if len(df_s) >= min_needed:
                best = df_s; used_radius = rad; used_tol = tol; break
        if not best.empty:
            break
    if best.empty:
        tol = tolerances[-1]; rad = radii[-1]; lo, hi = surface*(1-tol), surface*(1+tol)
        df_fb = df[(df["distance_m"]<=rad)&(df["surface_reelle_bati"]>=lo)&(df["surface_reelle_bati"]<=hi)].copy()
        if df_fb.empty:
            return pd.DataFrame(), 0, 0.0
        df_fb["prix_m2"] = df_fb["valeur_fonciere"] / df_fb["surface_reelle_bati"]
        df_fb = df_fb.replace([np.inf,-np.inf], np.nan).dropna(subset=["prix_m2"])
        return df_fb.sort_values(["distance_m","date_mutation"], ascending=[True,False]).head(3), rad, tol
    return best.sort_values(["distance_m","date_mutation"], ascending=[True,False]).copy(), used_radius, used_tol

def reliability_label(n: int) -> str:
    if n > 15: return "🟢 Très élevée"
    if n >= 8:  return "🟢 Élevée"
    if n >= 4:  return "🟡 Bonne"
    if n >= 2:  return "🟠 Modérée"
    return "🔴 Faible"

def market_tension_index(df_local: pd.DataFrame, used_radius: int) -> Dict[str, Any]:
    if df_local is None or df_local.empty or used_radius <= 0:
        return {"score": 0, "label": "🔴 Inconnu", "detail": "Pas assez de données"}
    n          = int(len(df_local))
    area_km2   = np.pi * (used_radius/1000.0)**2
    density    = n / max(1e-6, area_km2)
    last_date  = pd.to_datetime(df_local["date_mutation"]).max()
    days_since = int(max(0,(pd.Timestamp.utcnow().tz_localize(None)-pd.to_datetime(last_date).tz_localize(None)).days))
    pm2 = pd.to_numeric(df_local.get("prix_m2"), errors="coerce").replace([np.inf,-np.inf], np.nan).dropna()
    iqr_ratio = 1.0
    if not pm2.empty:
        iqr_ratio = max(1.0, float(pm2.quantile(0.75))-float(pm2.quantile(0.25))) / max(1.0, float(pm2.median()))
    score = float(clamp(
        0.45*100*(1-np.exp(-density/18)) + 0.35*100*np.exp(-days_since/95) + 0.20*100*np.exp(-iqr_ratio/0.18),
        0, 100
    ))
    label = ("🔥 Très attractif" if score>=75 else "⚡ Attractif" if score>=55
             else "🙂 Équilibré" if score>=35 else "🧊 Plus calme")
    return {"score": int(round(score)), "label": label,
            "detail": f"Densité ~{density:.1f}/km² · Dernière vente {days_since}j · IQR ~{iqr_ratio:.2f}"}

def compute_adjustments(bien_type, surface, nb_pieces, nb_chambres, etat, distance_m) -> Dict[str, float]:
    etat_factor     = {"À rénover":0.88,"Moyen":1.00,"Bon":1.05,"Rénové":1.10}.get(etat, 1.00)
    pieces_factor   = float(clamp(1.0+(nb_pieces-3)*0.015, 0.93, 1.08))
    chambres_factor = float(clamp(1.0+(nb_chambres-2)*0.02, 0.94, 1.10))
    gare_factor     = 1 + min(0.06, 0.45/(1+distance_m/1000))
    scale = float(clamp(1.02-(surface-55)*0.0009, 0.94, 1.06)) if bien_type=="Appartement" \
            else float(clamp(1.02-(surface-95)*0.0007, 0.93, 1.06))
    return {"etat":etat_factor,"pieces":pieces_factor,"chambres":chambres_factor,"gare":float(gare_factor),"scale":scale}

def band_from_reliability_and_tension(n, tension_score, bien_type):
    pct  = 0.060 if n>15 else 0.070 if n>=8 else 0.085 if n>=4 else 0.105 if n>=2 else 0.140
    pct *= 0.90 if tension_score>=75 else 0.95 if tension_score>=55 else 1.00 if tension_score>=35 else 1.08
    return float(pct), ((6500.0, 15000.0) if normalize_type_local(bien_type)=="Appartement" else (9000.0, 22000.0))

def compute_micro_market_estimate(df_all, lat, lon, bien_type, surface, nb_pieces, nb_chambres, etat) -> Dict[str, Any]:
    distance_m  = haversine_m(lat, lon, GARE_LAT, GARE_LON)
    quartier    = quartier_from_distance(distance_m)
    df_local, used_radius, used_tol = dvf_select_similaires_strict(df_all, lat, lon, bien_type, surface)
    target_type = normalize_type_local(bien_type)
    if not df_local.empty:
        df_local["type_local"] = df_local["type_local"].apply(normalize_type_local)
        df_local = df_local[df_local["type_local"]==target_type].copy()
        tol = float(used_tol or (0.35 if target_type=="Appartement" else 0.45))
        df_local = df_local[
            (df_local["surface_reelle_bati"]>=surface*(1-tol)) &
            (df_local["surface_reelle_bati"]<=surface*(1+tol))
        ].copy()
        df_local["prix_m2"] = df_local["valeur_fonciere"] / df_local["surface_reelle_bati"]
        df_local = df_local.replace([np.inf,-np.inf], np.nan).dropna(subset=["prix_m2"])
        df_local = df_local.drop_duplicates(
            subset=["date_mutation","valeur_fonciere","surface_reelle_bati","type_local","nom_commune"], keep="first")
    n   = int(len(df_local))
    rel = reliability_label(n)
    if n >= 2:   pm2_med = float(df_local["prix_m2"].median())
    elif n == 1: pm2_med = float(df_local["prix_m2"].iloc[0])
    else:
        pm2_med = float({
            "Centre-ville":      {"Maison":2100,"Appartement":2500},
            "Nord (Gare)":       {"Maison":1950,"Appartement":2200},
            "Sud (Résidentiel)": {"Maison":2350,"Appartement":2700},
            "Est (Pavillons)":   {"Maison":2000,"Appartement":2300},
            "Ouest (Neuf)":      {"Maison":2450,"Appartement":2800},
        }[quartier][target_type])
    adj        = compute_adjustments(target_type, surface, nb_pieces, nb_chambres, etat, distance_m)
    adj_factor = adj["etat"]*adj["pieces"]*adj["chambres"]*adj["gare"]*adj["scale"]
    tension    = market_tension_index(df_local, used_radius if used_radius else 0)
    tscore     = int(tension.get("score", 0))
    tilt       = 0.022 if tscore>=75 else 0.012 if tscore>=55 else 0.0 if tscore>=35 else -0.018
    center     = pm2_med * surface * adj_factor * (1.0+tilt)
    band_pct, (abs_min, abs_max) = band_from_reliability_and_tension(n, tscore, target_type)
    full_width = clamp(max(1.0, center*band_pct), abs_min, abs_max)
    est_min, est_max = float(center-full_width/2), float(center+full_width/2)
    if not np.isfinite(est_min) or not np.isfinite(est_max):
        est_min, est_max = center*0.93, center*1.07
    if est_min > est_max:
        est_min, est_max = est_max, est_min
    max_date    = df_all["date_mutation"].max()
    last_update = max_date.strftime("%B %Y") if pd.notna(max_date) else "—"

    # ── Preview + carte : on prend exactement les mêmes lignes, même nombre ──
    preview    = []
    map_points = []
    if not df_local.empty:
        # On trie et on limite à 6 biens MAX — même slice pour preview et carte
        df_preview = df_local.sort_values(
            ["distance_m","date_mutation"], ascending=[True,False]
        ).head(6).copy()

        for _, r in df_preview.iterrows():
            try:
                mois = pd.to_datetime(r["date_mutation"]).strftime("%m/%Y")
            except Exception:
                mois = "—"
            preview.append({
                "type_local": str(r.get("type_local","")),
                "surface":    int(round(float(r.get("surface_reelle_bati",0)))),
                "prix":       float(r.get("valeur_fonciere",0)),
                "mois":       mois,
                "commune":    str(r.get("nom_commune","Secteur")),
                "dist":       int(round(float(r.get("distance_m",0)) / 100) * 100),
            })
            # Jitter ~30m max pour flouter légèrement sans dénaturer la carte
            rng = np.random.default_rng(seed=int(r.get("valeur_fonciere",0)) % 9999)
            map_points.append({
                "lat": float(r["latitude"])  + rng.uniform(-0.00025, 0.00025),
                "lon": float(r["longitude"]) + rng.uniform(-0.00025, 0.00025),
            })

    return {
        "bien_type": target_type, "surface": float(surface), "quartier": quartier,
        "distance_gare_m": int(round(distance_m)), "pm2_med": float(pm2_med),
        "adj": adj, "adj_factor": float(adj_factor), "tilt": float(tilt),
        "est_min": est_min, "est_max": est_max, "n": n,
        "used_radius": int(used_radius or 0), "used_tol": float(used_tol or 0),
        "reliability": rel, "tension": tension, "last_update": last_update,
        "preview": preview, "map_points": map_points,
    }


# ===========================
# Debug tools
# ===========================
if DEBUG:
    with st.expander("🧹 Outils debug", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Vider le cache"):
                st.cache_data.clear(); st.rerun()
        with c2:
            if st.button("Forcer reload DVF"):
                st.session_state["_dvf_bust_manual"] = str(time.time())
                st.cache_data.clear(); st.rerun()


# ===========================
# Layout principal
# ===========================
colInfo, colForm = st.columns([0.90, 1.25], gap="large")

# ────────────────────────────────────────
# Colonne Info
# ────────────────────────────────────────
with colInfo:
    st.markdown("## Ce que vous recevez")
    st.markdown(
        "<div class='card accent-top'><ul>"
        "<li>✅ Une fourchette de prix réaliste, basée sur les ventes récentes de votre secteur</li>"
        "<li>✅ Le prix médian au m² pratiqué dans votre quartier ces 12 derniers mois</li>"
        "<li>✅ Des biens comparables au vôtre (même type, surface similaire, même zone)</li>"
        "<li>✅ Un indice d'attractivité de votre secteur (est-ce que les biens partent vite ?)</li>"
        "<li>✅ Une estimation affinée selon l'état, la surface, les pièces et la localisation</li>"
        "</ul></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='card soft'>"
        "🔎 <b>Une estimation honnête, pas magique.</b> Les données viennent des ventes officiellement "
        "enregistrées (source : data.gouv.fr, màj novembre 2025). On croise avec ce que vous indiquez "
        "pour rester au plus juste. Pas de chiffre sorti du chapeau."
        "</div>",
        unsafe_allow_html=True,
    )

# ────────────────────────────────────────
# Colonne Formulaire
# ────────────────────────────────────────
with colForm:
    st.markdown("## Parlez-moi de votre bien")

    # Commune
    area_options = [AUTO_AREA] + list(AREAS.keys())
    st.selectbox("Votre commune", area_options, key="area_name")

    if st.session_state.area_name in AREAS:
        st.session_state.detected_area = st.session_state.area_name
        st.session_state.area_locked   = True
    elif st.session_state.get("detected_area") not in AREAS:
        st.session_state.detected_area = DEFAULT_AREA

    effective_area, ai = get_effective_area()

    # ── Adresse (BAN — rapide) ────────────────────────────────────────
    st.text_input(
        "Adresse du bien",
        placeholder="Ex : 5 Rue de la République",
        key="addr_typed",
    )
    st.markdown(
        "<div class='addr-helper'>💡 Les suggestions apparaissent automatiquement — pas besoin d'appuyer sur Entrée.</div>",
        unsafe_allow_html=True,
    )

    typed = (st.session_state.addr_typed or "").strip()
    suggestions_display: List[str] = []
    suggestion_geo_map: Dict[str, Dict] = {}   # label affiché → données geo

    if len(typed) >= 2:
        if st.session_state.area_name == AUTO_AREA:
            # On cherche dans toutes les communes du secteur
            for area_name, info in AREAS.items():
                results = ban_completion(typed, postcode=info["postcode"], limit=3)
                for res in results:
                    display = f"{area_name} — {res['label']}"
                    suggestions_display.append(display)
                    suggestion_geo_map[display] = res
        else:
            results = ban_completion(typed, postcode=ai["postcode"], limit=7)
            for res in results:
                suggestions_display.append(res["label"])
                suggestion_geo_map[res["label"]] = res

    # Stocker la map geo en session pour récupération au submit
    st.session_state["_suggestion_geo_map"] = suggestion_geo_map

    if suggestions_display:
        prev_display  = st.session_state.get("addr_choice_display", "")
        default_index = suggestions_display.index(prev_display) if prev_display in suggestions_display else 0
        st.selectbox(
            "Sélectionnez votre adresse dans la liste",
            suggestions_display,
            index=default_index,
            key="addr_choice_display",
            on_change=on_addr_choice_display_change,
        )
    elif len(typed) >= 2:
        st.caption("Aucune adresse trouvée — vérifiez l'orthographe ou précisez le numéro.")
        st.session_state.addr_choice_display = ""
        st.session_state.addr_choice         = ""
    else:
        st.session_state.addr_choice_display = ""
        st.session_state.addr_choice         = ""

    st.markdown("<hr class='form-divider'/>", unsafe_allow_html=True)

    # Caractéristiques
    st.markdown("<span class='form-section-label'>Caractéristiques du bien</span>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Mon bien est…", ["Maison", "Appartement"], index=None, key="bien_type", placeholder="Choisir…")
        st.number_input("Surface habitable (m²)", min_value=0.0, max_value=500.0, step=1.0,
                        value=float(st.session_state.surface or 0.0), key="surface")
        st.selectbox("État général", ["À rénover", "Moyen", "Bon", "Rénové"],
                     index=None, key="etat", placeholder="Choisir…")
    with c2:
        st.number_input("Nombre de pièces", min_value=0, max_value=12, step=1,
                        value=int(st.session_state.nb_pieces or 0), key="nb_pieces")
        st.number_input("Dont chambres", min_value=0, max_value=10, step=1,
                        value=int(st.session_state.nb_chambres or 0), key="nb_chambres")
        st.markdown(
            "<div class='small-note' style='margin-top:0.5rem'>L'état influe sur l'estimation. "
            "Promis, on ne vous juge pas si c'est \"à rénover\" 😄</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='form-divider'/>", unsafe_allow_html=True)

    # Coordonnées
    st.markdown("<span class='form-section-label'>Où envoyer votre estimation ?</span>", unsafe_allow_html=True)
    cc1, cc2 = st.columns(2)
    with cc1:
        st.text_input("Votre prénom", key="prenom", placeholder="Entrez votre prénom ici")
    with cc2:
        st.text_input("Votre email", key="email", placeholder="exemple@mail.com")

    st.checkbox(
        "J'accepte de recevoir cette estimation par email et qu'Hakim me contacte pour l'affiner si besoin. "
        "Pas de spam, pas de relance tous les matins. Promis 🙂",
        key="consent",
    )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # Bouton CTA
    ready, filled_count = is_form_ready()
    submitted = st.button(
        "✨ Voir l'estimation de mon bien →",
        disabled=not ready,
        use_container_width=True,
    )

    if not ready:
        remaining = 8 - filled_count
        st.markdown(
            f"<div class='fields-status'>Il reste {remaining} champ{'s' if remaining > 1 else ''} à remplir pour activer l'estimation.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='fields-status ready'>✅ Tout est bon — cliquez pour lancer l'estimation !</div>",
            unsafe_allow_html=True,
        )

    # ── Traitement soumission ────────────────────────────────────────
    if submitted:
        effective_area, ai = get_effective_area()

        # Récupérer les coordonnées directement depuis la suggestion (pas de géocodage supplémentaire)
        geo_map   = st.session_state.get("_suggestion_geo_map", {})
        chosen    = st.session_state.get("addr_choice_display", "")
        geo_data  = geo_map.get(chosen)

        # Fallback : géocoder si les données ne sont plus en session
        if not geo_data:
            detected_area, detected_label = parse_display_choice(chosen)
            addr_label = detected_label if detected_label else chosen
            q = normalize_query_to_area(addr_label, city=ai["city"], postcode=ai["postcode"])
            geo_data = ban_geocode(q, postcode=ai["postcode"])

        if not geo_data:
            st.error("Impossible de localiser cette adresse. Sélectionnez une suggestion dans la liste et réessayez.")
            st.stop()

        # Vérifier que l'adresse est bien dans le secteur
        addr_postcode = geo_data.get("postcode", "")
        valid_postcodes = {info["postcode"] for info in AREAS.values()}
        if addr_postcode and addr_postcode not in valid_postcodes:
            st.error("Cette adresse ne semble pas être dans le secteur couvert. Choisissez une suggestion de la bonne zone.")
            st.stop()

        # Si AUTO_AREA, détecter la commune depuis le code postal
        if st.session_state.area_name == AUTO_AREA:
            detected_area, _ = parse_display_choice(chosen)
            if not detected_area:
                # Déduction depuis le code postal retourné par BAN
                for aname, ainfo in AREAS.items():
                    if ainfo["postcode"] == addr_postcode:
                        detected_area = aname
                        break
            if detected_area:
                st.session_state.detected_area = detected_area
                st.session_state.area_locked   = True
                effective_area, ai = get_effective_area()

        geo = {
            "lat":   geo_data["lat"],
            "lon":   geo_data["lon"],
            "label": geo_data.get("label", chosen),
        }

        t0       = time.time()
        progress = st.progress(0, text="🔎 Analyse des ventes récentes autour de votre bien…")

        def step(pct, txt, sleep=0.35):
            progress.progress(pct, text=txt); time.sleep(sleep)

        try:
            step(10, "📦 Chargement des ventes officielles (DVF)…", 0.65)
            df_all = load_dvf_local(st.session_state.get("_dvf_bust_manual", DVF_CACHE_BUSTER))
            if df_all.empty:
                st.warning("⚠️ Base DVF locale introuvable.")
                st.markdown("<a href='mailto:hakim@immoclermontoise.fr'>Contactez Hakim directement →</a>",
                            unsafe_allow_html=True)
                st.stop()

            step(40, "🏡 Recherche de biens similaires dans votre secteur…", 1.1)
            step(65, "📐 Calcul des ajustements (état, surface, localisation)…", 1.0)

            payload = compute_micro_market_estimate(
                df_all=df_all,
                lat=float(geo["lat"]), lon=float(geo["lon"]),
                bien_type=str(st.session_state.bien_type),
                surface=float(st.session_state.surface),
                nb_pieces=int(st.session_state.nb_pieces),
                nb_chambres=int(st.session_state.nb_chambres),
                etat=str(st.session_state.etat),
            )

            step(82, "📊 Calcul de la fourchette et de l'attractivité du secteur…", 1.0)

            dt = time.time() - t0
            if dt < MIN_PROGRESS_SECONDS:
                time.sleep(MIN_PROGRESS_SECONDS - dt)

            progress.progress(100, text="✅ Votre estimation est prête !")
            time.sleep(0.3)

            st.session_state.geo            = geo
            st.session_state.result_payload = payload

            # Envoi KIT
            kit_ok = add_to_kit(
                prenom=st.session_state.prenom,
                email=st.session_state.email,
                area=effective_area,
                bien_type=str(st.session_state.bien_type),
                surface=float(st.session_state.surface),
            )
            if DEBUG:
                st.write("KIT envoi :", "✅ OK" if kit_ok else "❌ Échec")

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

    geo    = st.session_state.geo
    hp     = st.session_state.result_payload
    tens   = hp.get("tension", {})
    tscore = int(tens.get("score", 0))

    m1, m2, m3 = st.columns(3, gap="medium")
    with m1:
        st.markdown(f"<div class='metric'><p class='k'>Fourchette estimée</p>"
                    f"<p class='v'>{eur(hp['est_min'])} – {eur(hp['est_max'])}</p></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric'><p class='k'>Fiabilité des données</p>"
                    f"<p class='v'>{hp['reliability']}</p></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='metric'><p class='k'>Attractivité du secteur</p>"
                    f"<p class='v'>{tens.get('label','—')} ({tscore}/100)</p></div>", unsafe_allow_html=True)

    st.markdown(
        f"<div class='card soft'>"
        f"<b>Adresse analysée :</b> {geo.get('label','')}<br/>"
        f"<b>Zone (proxy) :</b> {hp.get('quartier','—')} — "
        f"<b>Distance gare :</b> {hp.get('distance_gare_m','—')} m<br/>"
        f"<b>Prix médian au m² (ventes réelles) :</b> ~{eur(hp.get('pm2_med',0))} / m²<br/>"
        f"<b>Biens comparables trouvés :</b> {hp.get('n',0)} ventes (12 mois glissants) "
        f"— rayon max : {hp.get('used_radius','—')} m"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown(f"<div class='tension-box'>{tension_context_message(tscore)}</div>", unsafe_allow_html=True)

    # Carte — même nombre de points que dans preview
    map_points = hp.get("map_points", [])
    if map_points:
        st.markdown("### 🗺️ Localisation des ventes comparables")
        st.caption("Position légèrement floue pour respecter la vie privée des vendeurs.")
        bien_point = pd.DataFrame([{"lat": float(geo["lat"]), "lon": float(geo["lon"])}])
        st.map(pd.concat([bien_point, pd.DataFrame(map_points)], ignore_index=True), zoom=14)

    # Disclaimer avec flèches saumon
    st.markdown(
        "<div class='card accent-top'>"
        "<b>Ce que les données ne peuvent pas voir à votre place :</b>"
        "<ul class='disclaimer-list'>"
        "<li>Les nuisances (route, voisinage, bruit, vis-à-vis…)</li>"
        "<li>La luminosité et l'exposition</li>"
        "<li>L'état réel et la qualité des finitions</li>"
        "<li>Les travaux faits ou à prévoir, isolation, DPE</li>"
        "<li>L'agencement, les volumes, l'entretien</li>"
        "<li>Les extérieurs, cave, garage, stationnement, charges de copropriété…</li>"
        "</ul>"
        "Cette fourchette est une <b>base solide et honnête</b>. Mais pour un chiffre vraiment précis "
        "et des conseils adaptés à votre projet, rien ne vaut un échange de vive voix."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='booking-btn'><a href='{BOOKING_URL}' target='_blank'>"
        f"📞 Affiner cette estimation avec Hakim — RDV gratuit, sans engagement"
        f"</a></div>",
        unsafe_allow_html=True,
    )
    st.caption("Un échange de 20 minutes pour un chiffre précis et des conseils pour valoriser votre bien.")

    if tens.get("detail"):
        st.caption(f"📌 {tens['detail']}")

    if hp.get("preview"):
        with st.expander("🧾 Voir les biens comparables utilisés (localisation volontairement vague)"):
            for r in hp["preview"]:
                st.markdown(
                    f"- **{r['type_local']}** · **{r['surface']} m²** · **{eur(r['prix'])}** · "
                    f"**{r['mois']}** · **{r['commune']}** (~{r['dist']} m)"
                )

    if DEBUG:
        with st.expander("🧪 Debug payload"):
            st.write(hp); st.write("geo:", geo)
