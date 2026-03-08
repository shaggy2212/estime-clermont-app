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

PRIMARY  = "#063970"
ACCENT   = "#FF7E79"
GOLD     = "#C9A96E"
SOFT     = "#EAF2FF"

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

BAN_SEARCH_URL     = "https://api-adresse.data.gouv.fr/search/"
BAN_COMPLETION_URL = "https://api-adresse.data.gouv.fr/search/"

DVF_LOCAL_PATH   = Path("data/dvf_local.parquet")
DVF_CACHE_BUSTER = "v9"

# ===========================
# Session state
# ===========================
_defaults = {
    "geo": None, "result_payload": None,
    "area_name": AUTO_AREA, "area_locked": False, "detected_area": DEFAULT_AREA,
    "bien_type": None, "surface": 0.0, "etat": None,
    "nb_pieces": 0, "nb_chambres": 0,
    "addr_typed": "", "addr_choice_display": "", "addr_choice": "",
    "prenom": "", "email": "", "consent": False,
    "_kit_result": None, "_kit_error": "", "_kit_response": "",
}
for k, v in _defaults.items():
    st.session_state.setdefault(k, v)

DEBUG = False
try:
    DEBUG = (st.query_params.get("debug", "0") == "1")
except Exception:
    DEBUG = False

# ===========================
# CSS — Design ludique clair
# ===========================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800;900&display=swap');

/* ═══ RESET & BASE ═══════════════════════════════════════════════════ */
html, body, [class*="stApp"] {{
    font-family: 'Poppins', sans-serif !important;
    font-size: 15px !important;
    background: #ffffff !important;
    color: #1e293b !important;
}}
.main .block-container {{
    background: #ffffff !important;
    padding-top: 1.5rem !important;
    max-width: 1280px !important;
}}
section[data-testid="stSidebar"] {{ display: none !important; }}

/* ═══ TYPOGRAPHIE ═════════════════════════════════════════════════════ */
h2 {{
    font-family: 'Poppins', sans-serif !important;
    color: {PRIMARY} !important;
    font-size: 1.85rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 1rem !important;
    line-height: 1.15 !important;
}}
h3 {{
    font-family: 'Poppins', sans-serif !important;
    color: #1e293b !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
}}
p, li, span, label, div {{ color: #334155 !important; }}

/* ═══ CARD INFO (colonne gauche) ═════════════════════════════════════ */
.info-card {{
    background: linear-gradient(145deg, {ACCENT} 0%, #e8635d 100%);
    border-radius: 24px;
    padding: 1.8rem 1.6rem;
    margin-bottom: 1rem;
    box-shadow: 0 8px 32px rgba(255,126,121,0.30);
    position: relative; overflow: hidden;
}}
.info-card::before {{
    content: "";
    position: absolute; top: -60px; right: -60px;
    width: 200px; height: 200px;
    background: rgba(255,255,255,0.10);
    border-radius: 50%; pointer-events: none;
}}
.info-card::after {{
    content: "";
    position: absolute; bottom: -50px; left: -40px;
    width: 160px; height: 160px;
    background: rgba(255,255,255,0.07);
    border-radius: 50%; pointer-events: none;
}}
.info-card ul {{
    list-style: none; padding: 0; margin: 1rem 0 0;
}}
.info-card ul li {{
    padding: 0.65rem 0;
    font-size: 1rem !important;
    color: white !important;
    display: flex; align-items: flex-start; gap: 0.85rem;
    border-bottom: 1px solid rgba(255,255,255,0.18);
    font-weight: 600 !important;
    line-height: 1.45;
}}
.info-card ul li:last-child {{ border-bottom: none; }}
.info-card ul li .check {{
    background: rgba(255,255,255,0.28);
    color: white !important;
    font-weight: 900;
    flex-shrink: 0;
    width: 26px; height: 26px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.85rem !important;
    margin-top: 1px;
}}
/* Force blanc sur TOUS les enfants de info-card contre le sélecteur global */
.info-card p, .info-card li, .info-card span, .info-card div {{
    color: white !important;
}}
.info-note {{
    background: white;
    border-left: 4px solid {PRIMARY};
    border-radius: 0 16px 16px 0;
    padding: 1rem 1.2rem;
    font-size: 0.93rem !important;
    line-height: 1.65;
    margin-top: 0.8rem;
    box-shadow: 0 2px 12px rgba(6,57,112,0.08);
}}
.info-note b {{ color: {PRIMARY} !important; font-weight: 700 !important; }}
.info-note span {{ color: #334155 !important; font-weight: 500 !important; }}

/* ═══ FORM WRAPPER (colonne droite) ══════════════════════════════════ */
.form-wrapper {{
    background: white;
    border-radius: 28px;
    padding: 0.3rem 1.8rem 2rem;
    box-shadow: 0 4px 24px rgba(6,57,112,0.08);
    position: relative;
    border: 1.5px solid #f1f5f9;
    overflow: visible;
}}
.form-wrapper::before, .form-wrapper::after {{ display: none; }}

/* ═══ SECTION PILLS ══════════════════════════════════════════════════ */
.section-pill {{
    display: inline-flex; align-items: center; gap: 0.55rem;
    background: #eff6ff;
    border: 2px solid rgba(6,57,112,0.15);
    border-radius: 999px;
    padding: 0.5rem 1.2rem;
    font-size: 0.92rem !important;
    font-weight: 800 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: {PRIMARY} !important;
    margin-bottom: 0.9rem;
}}

/* ═══ LABELS ═════════════════════════════════════════════════════════ */
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label {{
    font-size: 0.80rem !important;
    font-weight: 800 !important;
    color: #94a3b8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    margin-bottom: 0.25rem !important;
}}

/* ═══ INPUT TEXT ═════════════════════════════════════════════════════ */
[data-testid="stTextInput"] input {{
    height: 54px !important;
    background: #f8fafc !important;
    border: 2px solid #e2e8f0 !important;
    border-radius: 16px !important;
    color: #1e293b !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.97rem !important;
    font-weight: 600 !important;
    padding: 0 1.1rem !important;
    transition: border-color 0.2s, box-shadow 0.2s, background 0.2s !important;
    caret-color: {ACCENT} !important;
}}
[data-testid="stTextInput"] input:focus {{
    background: white !important;
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 4px rgba(255,126,121,0.12) !important;
    outline: none !important;
}}
[data-testid="stTextInput"] input::placeholder {{
    color: #94a3b8 !important;
    font-style: italic;
    font-weight: 400 !important;
}}

/* ═══ NUMBER INPUT ═══════════════════════════════════════════════════ */
[data-testid="stNumberInput"] > div {{
    background: #f8fafc !important;
    border: 2px solid #e2e8f0 !important;
    border-radius: 16px !important;
    padding: 0 0.3rem !important;
    min-height: 58px !important;
    display: flex !important;
    align-items: center !important;
}}
[data-testid="stNumberInput"] > div > div {{
    display: flex !important;
    align-items: center !important;
    height: 100% !important;
}}
[data-testid="stNumberInput"] input {{
    height: 40px !important;
    background: transparent !important;
    border: none !important;
    border-radius: 16px !important;
    color: #1e293b !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    padding: 0 0.8rem !important;
    text-align: center !important;
    transition: background 0.2s !important;
    caret-color: {ACCENT} !important;
    box-shadow: none !important;
}}
[data-testid="stNumberInput"] input:focus {{
    background: transparent !important;
    outline: none !important;
    box-shadow: none !important;
}}
[data-testid="stNumberInput"] button {{
    background: white !important;
    border: none !important;
    color: {PRIMARY} !important;
    border-radius: 8px !important;
    font-weight: 900 !important;
    font-size: 0.9rem !important;
    box-shadow: 0 1px 4px rgba(6,57,112,0.10) !important;
    margin: 3px !important;
    width: 32px !important;
    height: 32px !important;
    min-height: unset !important;
    flex-shrink: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    align-self: center !important;
}}
[data-testid="stNumberInput"] button:hover {{
    background: {ACCENT} !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(255,126,121,0.25) !important;
}}

/* ═══ SELECTBOX ══════════════════════════════════════════════════════ */
[data-testid="stSelectbox"] > div > div {{
    background: #f8fafc !important;
    border: 2px solid #e2e8f0 !important;
    border-radius: 16px !important;
    min-height: 54px !important;
    display: flex !important;
    align-items: center !important;
}}
[data-testid="stSelectbox"] > div > div > div {{
    background: transparent !important;
    border: none !important;
    min-height: unset !important;
    padding: 0 0.3rem !important;
}}
[data-testid="stSelectbox"] > div > div:focus-within {{
    background: white !important;
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 4px rgba(255,126,121,0.12) !important;
}}
[data-testid="stSelectbox"] span {{
    color: #1e293b !important;
    font-family: 'Poppins', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.97rem !important;
}}
[data-testid="stSelectbox"] svg {{ fill: #94a3b8 !important; }}

[data-testid="InputInstructions"],
[data-testid="InputInstructions"] *,
[data-testid="stNumberInputContainer"] ~ div,
[data-testid="stNumberInput"] > div ~ div {{
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
    pointer-events: none !important;
}}

/* ═══ ANTI-CLIP — empêche Streamlit de couper les champs ═════════════ */
[data-testid="stTextInput"],
[data-testid="stSelectbox"],
[data-testid="stNumberInput"],
[data-testid="stCheckbox"],
[data-testid="stTextInput"] > div,
[data-testid="stSelectbox"] > div {{
    overflow: visible !important;
}}

/* ═══ CHECKBOX ═══════════════════════════════════════════════════════ */
[data-testid="stCheckbox"] {{
    background: #f8fafc;
    border: 2px solid #e2e8f0;
    border-radius: 16px;
    padding: 0.8rem 1rem !important;
    margin-top: 0.8rem;
    transition: border-color 0.2s;
}}
[data-testid="stCheckbox"]:hover {{
    border-color: {ACCENT} !important;
}}
[data-testid="stCheckbox"] label p {{
    font-size: 0.87rem !important;
    color: #64748b !important;
    line-height: 1.55 !important;
    font-weight: 500 !important;
}}
/* Supprime TOUT fond sur le label et ses enfants, dans tous les états */
[data-baseweb="checkbox"] > div:last-child,
[data-baseweb="checkbox"] > div:last-child *,
[data-baseweb="checkbox"] label,
[data-baseweb="checkbox"] label * {{
    background: transparent !important;
    background-color: transparent !important;
}}
/* Carré cochable uniquement */
[data-testid="stCheckbox"] input:checked + div {{
    background: {ACCENT} !important;
    border-color: {ACCENT} !important;
}}

/* ═══ ALIGNEMENT COLONNES CARACTÉRISTIQUES ═══════════════════════════ */
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] > div {{
    min-height: 58px !important;
}}

/* ═══ ESPACEMENT CHAMPS CONTACT ══════════════════════════════════════ */
[data-testid="stTextInput"] {{
    margin-bottom: 0.6rem !important;
}}

/* ═══ CTA BUTTON ═════════════════════════════════════════════════════ */
.stButton > button {{
    width: 100% !important;
    min-height: 72px !important;
    background: {ACCENT} !important;
    color: white !important;
    border: none !important;
    border-radius: 18px !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 1.35rem !important;
    font-weight: 900 !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 8px 28px rgba(255,126,121,0.35) !important;
    transition: all 0.22s cubic-bezier(.34,1.56,.64,1) !important;
}}
.stButton > button *,
.stButton > button span,
.stButton > button p,
.stButton > button div {{
    font-size: 1.35rem !important;
    font-weight: 900 !important;
    color: white !important;
}}
.stButton > button:hover:not(:disabled) {{
    transform: translateY(-3px) scale(1.01) !important;
    box-shadow: 0 14px 36px rgba(255,126,121,0.42) !important;
}}
.stButton > button:disabled {{
    background: #e2e8f0 !important;
    box-shadow: none !important;
    transform: none !important;
}}
.stButton > button:disabled * {{
    color: #94a3b8 !important;
}}

/* ═══ SÉPARATEUR ═════════════════════════════════════════════════════ */
.form-sep {{
    border: none;
    border-top: 2px dashed #f1f5f9;
    margin: 1.3rem 0 1rem;
}}

/* ═══ HELPER ADRESSE ═════════════════════════════════════════════════ */
.addr-helper {{
    font-size: 0.82rem !important;
    color: #94a3b8 !important;
    margin-top: -0.15rem;
    margin-bottom: 0.65rem;
    font-style: italic;
    font-weight: 600 !important;
}}

/* ═══ STATUT FORMULAIRE ══════════════════════════════════════════════ */
.form-status {{
    text-align: center;
    font-size: 0.86rem !important;
    color: #94a3b8 !important;
    font-weight: 700 !important;
    margin-top: 0.5rem;
    padding: 0.4rem;
}}
.form-status.ready {{
    color: #22c55e !important;
}}

/* ═══ MÉTRIQUES RÉSULTATS ════════════════════════════════════════════ */
.result-metric {{
    background: white;
    border-radius: 20px;
    padding: 1.3rem 1.2rem;
    box-shadow: 0 4px 20px rgba(6,57,112,0.08);
    position: relative; overflow: hidden;
    margin-bottom: 0.8rem;
}}
.result-metric::before {{
    content: ""; position: absolute;
    top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, {PRIMARY}, {ACCENT});
    border-radius: 20px 20px 0 0;
}}
.result-metric .mk {{
    font-size: 0.75rem !important; color: #94a3b8 !important;
    text-transform: uppercase; letter-spacing: 0.09em;
    margin: 0; font-weight: 800 !important;
}}
.result-metric .mv {{
    font-size: 1.4rem !important; font-weight: 900 !important;
    color: {PRIMARY} !important; margin: 0.25rem 0 0;
    letter-spacing: -0.02em;
}}

/* ═══ CARD RÉSULTATS ═════════════════════════════════════════════════ */
.result-card {{
    background: white;
    border-radius: 18px;
    padding: 1.2rem 1.3rem;
    margin-bottom: 0.8rem;
    box-shadow: 0 4px 16px rgba(6,57,112,0.07);
    border-left: 4px solid {PRIMARY};
}}
.result-card b {{ color: #334155 !important; font-weight: 800 !important; }}

/* ═══ TENSION BOX ════════════════════════════════════════════════════ */
.tension-box {{
    background: #fff7f7;
    border-left: 4px solid {ACCENT};
    border-radius: 0 18px 18px 0;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
    font-size: 0.94rem !important;
    line-height: 1.65;
    color: #334155 !important;
}}

/* ═══ DISCLAIMER LIST ════════════════════════════════════════════════ */
.disclaimer-list {{
    list-style: none; padding: 0; margin: 0.7rem 0 1rem;
}}
.disclaimer-list li {{
    padding: 0.32rem 0;
    font-size: 0.93rem !important;
    color: #64748b !important;
    display: flex; align-items: flex-start; gap: 0.55rem;
    font-weight: 600 !important;
}}
.disclaimer-list li::before {{
    content: "→";
    color: {ACCENT} !important;
    font-weight: 900; flex-shrink: 0;
}}

/* ═══ BOUTON RDV ═════════════════════════════════════════════════════ */
.booking-btn a {{
    display: block; text-align: center;
    background: {PRIMARY};
    color: white !important;
    font-family: 'Poppins', sans-serif !important;
    font-weight: 900 !important;
    font-size: 1rem !important;
    border-radius: 18px;
    padding: 1.1rem 1.5rem;
    text-decoration: none !important;
    box-shadow: 0 8px 28px rgba(6,57,112,0.22);
    margin-top: 0.5rem;
    transition: all 0.22s cubic-bezier(.34,1.56,.64,1);
    letter-spacing: 0.01em;
}}
.booking-btn a:hover {{
    transform: translateY(-2px) scale(1.01);
    box-shadow: 0 14px 36px rgba(6,57,112,0.28);
}}

/* ═══ HR ═════════════════════════════════════════════════════════════ */
hr {{
    border: none;
    border-top: 2px dashed #e2e8f0;
    margin: 1.5rem 0;
}}

/* ═══ PROGRESS BAR ═══════════════════════════════════════════════════ */
[data-testid="stProgress"] > div > div {{
    background: linear-gradient(90deg, {PRIMARY}, {ACCENT}) !important;
    border-radius: 999px !important;
}}

/* ═══ ALERTS ═════════════════════════════════════════════════════════ */
[data-testid="stAlert"] {{
    background: #f0fdf4 !important;
    border: 2px solid #bbf7d0 !important;
    border-radius: 16px !important;
    color: #16a34a !important;
}}

/* ═══ EXPANDER ═══════════════════════════════════════════════════════ */
[data-testid="stExpander"] {{
    background: white !important;
    border: 2px solid #f1f5f9 !important;
    border-radius: 16px !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04) !important;
}}
[data-testid="stExpander"] summary {{
    color: #64748b !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
}}

/* ═══ MAP ════════════════════════════════════════════════════════════ */
[data-testid="stDeckGlJsonChart"], iframe {{
    border-radius: 20px !important;
    overflow: hidden;
    border: 2px solid #f1f5f9 !important;
    box-shadow: 0 4px 16px rgba(6,57,112,0.07) !important;
}}

/* ═══ CAPTIONS ═══════════════════════════════════════════════════════ */
[data-testid="stCaptionContainer"] p {{
    color: #94a3b8 !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
}}

/* ═══ SCROLLBAR ══════════════════════════════════════════════════════ */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: #f1f5f9; }}
::-webkit-scrollbar-thumb {{ background: rgba(6,57,112,0.15); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {ACCENT}; }}
</style>
""", unsafe_allow_html=True)


# ===========================
# Helpers
# ===========================
def norm(s: str) -> str:
    return (s or "").strip().lower().replace("'", "'")

def eur(x: float) -> str:
    return f"{x:,.0f} €".replace(",", "\u202f")

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
    geo_map = st.session_state.get("_suggestion_geo_map", {})
    geo = geo_map.get(display_val, {})
    st.session_state.addr_choice = display_val
    area = geo.get("_area")
    if area and area in AREAS:
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
        return "🔥 <b>Votre secteur est actuellement très recherché.</b> Les biens similaires partent vite et les prix se tiennent bien. C'est le bon moment pour vendre, à condition de bien positionner le prix dès le départ."
    elif tscore >= 55:
        return "⚡ <b>Le marché est actif sur votre secteur.</b> Les acheteurs sont présents, mais ils comparent. Une mise en valeur soignée et un prix juste feront toute la différence."
    elif tscore >= 35:
        return "🙂 <b>Le marché est équilibré.</b> Ni en surchauffe, ni en pause. Les biens bien présentés et correctement positionnés se vendent sans trop traîner."
    else:
        return "🧊 <b>Le marché est plus calme en ce moment.</b> Ça ne veut pas dire que votre bien ne se vendra pas — ça veut dire que la stratégie de prix et la présentation vont compter encore plus que d'habitude."

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
# KIT
# ===========================
def add_to_kit(prenom: str, email: str, area: str, bien_type: str, surface: float) -> bool:
    try:
        api_key = st.secrets.get("KIT_API_KEY", "")
        form_id = st.secrets.get("KIT_FORM_ID", "")
        if not api_key or not form_id:
            st.session_state["_kit_result"] = False
            st.session_state["_kit_error"]  = f"Secrets manquants — api_key={'OK' if api_key else 'VIDE'}, form_id={'OK' if form_id else 'VIDE'}"
            return False
        url = f"https://api.convertkit.com/v3/forms/{form_id}/subscribe"
        payload = {
            "api_key": api_key, "email": email, "first_name": prenom,
            "fields": {"commune": area, "type_bien": bien_type, "surface": str(int(surface)), "source": "EstimeClermont"},
        }
        r = requests.post(url, json=payload, timeout=10)
        st.session_state["_kit_result"]   = r.status_code in (200, 201)
        st.session_state["_kit_response"] = f"Status {r.status_code} — {r.text[:400]}"
        st.session_state["_kit_error"]    = "" if r.status_code in (200, 201) else r.text[:200]
        return r.status_code in (200, 201)
    except Exception as e:
        st.session_state["_kit_result"] = False
        st.session_state["_kit_error"]  = str(e)
        return False


# ===========================
# BAN Geocodage
# ===========================
@st.cache_data(ttl=3600, show_spinner=False)
def ban_completion(text: str, postcode: str, limit: int = 6) -> List[Dict[str, Any]]:
    if not text or len(text.strip()) < 2:
        return []
    try:
        r = requests.get(BAN_COMPLETION_URL,
                         params={"q": text.strip(), "postcode": postcode, "limit": limit, "autocomplete": 1},
                         timeout=5)
        r.raise_for_status()
        results = []
        for f in r.json().get("features", []):
            props  = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates", [])
            if len(coords) < 2:
                continue
            results.append({"label": props.get("label",""), "lat": float(coords[1]),
                             "lon": float(coords[0]), "city": props.get("city",""),
                             "postcode": props.get("postcode","")})
        return results
    except Exception:
        return []

@st.cache_data(ttl=86400, show_spinner=False)
def ban_geocode(query: str, postcode: str) -> Optional[Dict[str, Any]]:
    if not query:
        return None
    try:
        r = requests.get(BAN_SEARCH_URL, params={"q": query, "postcode": postcode, "limit": 1}, timeout=8)
        r.raise_for_status()
        feats = r.json().get("features", [])
        if not feats:
            return None
        f0     = feats[0]
        props  = f0.get("properties", {})
        coords = f0.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            return None
        return {"lat": float(coords[1]), "lon": float(coords[0]),
                "label": props.get("label", query), "postcode": props.get("postcode", postcode),
                "city": props.get("city","")}
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
    if df_all.empty: return pd.DataFrame(), 0, 0.0
    target_type = normalize_type_local(bien_type)
    surface     = float(surface)
    max_date    = df_all["date_mutation"].max()
    if pd.isna(max_date): return pd.DataFrame(), 0, 0.0
    df = df_all[df_all["date_mutation"] >= max_date - pd.Timedelta(days=365)].copy()
    if df.empty: return pd.DataFrame(), 0, 0.0
    df["type_local"] = df["type_local"].apply(normalize_type_local)
    df = df[df["type_local"] == target_type].copy()
    if df.empty: return pd.DataFrame(), 0, 0.0
    lat0, lon0 = float(lat), float(lon)
    R    = 6371000.0
    phi1 = np.radians(lat0)
    phi2 = np.radians(df["latitude"].to_numpy(float))
    dphi = np.radians(df["latitude"].to_numpy(float)  - lat0)
    dl   = np.radians(df["longitude"].to_numpy(float) - lon0)
    a    = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dl/2)**2
    df["distance_m"] = 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    radii      = [600, 900, 1500, 2500, 3500]
    tolerances = [0.20,0.25,0.30,0.35] if target_type=="Appartement" else [0.25,0.30,0.40,0.45]
    min_needed = 4
    best = pd.DataFrame(); used_radius = 0; used_tol = 0.0
    for rad in radii:
        df_r = df[df["distance_m"] <= rad].copy()
        if df_r.empty: continue
        for tol in tolerances:
            lo, hi = surface*(1-tol), surface*(1+tol)
            df_s = df_r[(df_r["surface_reelle_bati"]>=lo)&(df_r["surface_reelle_bati"]<=hi)].copy()
            if df_s.empty: continue
            df_s["prix_m2"] = df_s["valeur_fonciere"] / df_s["surface_reelle_bati"]
            df_s = df_s.replace([np.inf,-np.inf], np.nan).dropna(subset=["prix_m2"])
            if len(df_s) >= 10:
                q10, q90 = df_s["prix_m2"].quantile(0.10), df_s["prix_m2"].quantile(0.90)
                df_s = df_s[(df_s["prix_m2"]>=q10)&(df_s["prix_m2"]<=q90)]
            if len(df_s) >= min_needed:
                best = df_s; used_radius = rad; used_tol = tol; break
        if not best.empty: break
    if best.empty:
        tol = tolerances[-1]; rad = radii[-1]; lo, hi = surface*(1-tol), surface*(1+tol)
        df_fb = df[(df["distance_m"]<=rad)&(df["surface_reelle_bati"]>=lo)&(df["surface_reelle_bati"]<=hi)].copy()
        if df_fb.empty: return pd.DataFrame(), 0, 0.0
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
        0, 100))
    label = ("🔥 Très attractif" if score>=75 else "⚡ Attractif" if score>=55
             else "🙂 Équilibré" if score>=35 else "🧊 Plus calme")
    return {"score": int(round(score)), "label": label,
            "detail": f"Densité ~{density:.1f}/km² · Dernière vente {days_since}j · IQR ~{iqr_ratio:.2f}"}

def compute_adjustments(bien_type, surface, nb_pieces, nb_chambres, etat, distance_m):
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
    return float(pct), ((6500.0,15000.0) if normalize_type_local(bien_type)=="Appartement" else (9000.0,22000.0))

def compute_micro_market_estimate(df_all, lat, lon, bien_type, surface, nb_pieces, nb_chambres, etat):
    distance_m  = haversine_m(lat, lon, GARE_LAT, GARE_LON)
    quartier    = quartier_from_distance(distance_m)
    df_local, used_radius, used_tol = dvf_select_similaires_strict(df_all, lat, lon, bien_type, surface)
    target_type = normalize_type_local(bien_type)
    if not df_local.empty:
        df_local["type_local"] = df_local["type_local"].apply(normalize_type_local)
        df_local = df_local[df_local["type_local"]==target_type].copy()
        tol = float(used_tol or (0.35 if target_type=="Appartement" else 0.45))
        df_local = df_local[(df_local["surface_reelle_bati"]>=surface*(1-tol))&(df_local["surface_reelle_bati"]<=surface*(1+tol))].copy()
        df_local["prix_m2"] = df_local["valeur_fonciere"] / df_local["surface_reelle_bati"]
        df_local = df_local.replace([np.inf,-np.inf], np.nan).dropna(subset=["prix_m2"])
        df_local = df_local.drop_duplicates(subset=["date_mutation","valeur_fonciere","surface_reelle_bati","type_local","nom_commune"], keep="first")
    n   = int(len(df_local))
    rel = reliability_label(n)
    if n >= 2:   pm2_med = float(df_local["prix_m2"].median())
    elif n == 1: pm2_med = float(df_local["prix_m2"].iloc[0])
    else:
        pm2_med = float({"Centre-ville":{"Maison":2100,"Appartement":2500},"Nord (Gare)":{"Maison":1950,"Appartement":2200},
            "Sud (Résidentiel)":{"Maison":2350,"Appartement":2700},"Est (Pavillons)":{"Maison":2000,"Appartement":2300},
            "Ouest (Neuf)":{"Maison":2450,"Appartement":2800}}[quartier][target_type])
    adj        = compute_adjustments(target_type, surface, nb_pieces, nb_chambres, etat, distance_m)
    adj_factor = adj["etat"]*adj["pieces"]*adj["chambres"]*adj["gare"]*adj["scale"]
    tension    = market_tension_index(df_local, used_radius if used_radius else 0)
    tscore     = int(tension.get("score", 0))
    tilt       = 0.022 if tscore>=75 else 0.012 if tscore>=55 else 0.0 if tscore>=35 else -0.018
    center     = pm2_med * surface * adj_factor * (1.0+tilt)
    band_pct, (abs_min, abs_max) = band_from_reliability_and_tension(n, tscore, target_type)
    full_width = clamp(max(1.0, center*band_pct), abs_min, abs_max)
    est_min, est_max = float(center-full_width/2), float(center+full_width/2)
    if not np.isfinite(est_min) or not np.isfinite(est_max): est_min, est_max = center*0.93, center*1.07
    if est_min > est_max: est_min, est_max = est_max, est_min
    max_date    = df_all["date_mutation"].max()
    last_update = max_date.strftime("%B %Y") if pd.notna(max_date) else "—"
    preview = []; map_points = []
    if not df_local.empty:
        df_prev = df_local.sort_values(["distance_m","date_mutation"], ascending=[True,False]).head(6).copy()
        for _, r in df_prev.iterrows():
            try: mois = pd.to_datetime(r["date_mutation"]).strftime("%m/%Y")
            except: mois = "—"
            preview.append({"type_local":str(r.get("type_local","")),
                "surface":int(round(float(r.get("surface_reelle_bati",0)))),
                "prix":float(r.get("valeur_fonciere",0)),"mois":mois,
                "commune":str(r.get("nom_commune","Secteur")),
                "dist":int(round(float(r.get("distance_m",0))/100)*100)})
            rng = np.random.default_rng(seed=int(r.get("valeur_fonciere",0)) % 9999)
            map_points.append({"lat":float(r["latitude"])+rng.uniform(-0.00025,0.00025),
                               "lon":float(r["longitude"])+rng.uniform(-0.00025,0.00025)})
    return {"bien_type":target_type,"surface":float(surface),"quartier":quartier,
        "distance_gare_m":int(round(distance_m)),"pm2_med":float(pm2_med),"adj":adj,
        "adj_factor":float(adj_factor),"tilt":float(tilt),"est_min":est_min,"est_max":est_max,
        "n":n,"used_radius":int(used_radius or 0),"used_tol":float(used_tol or 0),
        "reliability":rel,"tension":tension,"last_update":last_update,"preview":preview,"map_points":map_points}


# ===========================
# Debug
# ===========================
if DEBUG:
    with st.expander("🧹 Debug", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Vider cache"): st.cache_data.clear(); st.rerun()
        with c2:
            if st.button("Reload DVF"):
                st.session_state["_dvf_bust_manual"] = str(time.time())
                st.cache_data.clear(); st.rerun()
        api_key = st.secrets.get("KIT_API_KEY",""); form_id = st.secrets.get("KIT_FORM_ID","")
        st.write(f"KIT_API_KEY : {'✅ ' + api_key[:6] + '...' if api_key else '❌ MANQUANTE'}")
        st.write(f"KIT_FORM_ID : {'✅ ' + form_id if form_id else '❌ MANQUANT'}")
        if st.session_state.get("_kit_result") is not None:
            st.write("Dernier envoi KIT :", "✅ OK" if st.session_state["_kit_result"] else "❌ Échec")
        if st.session_state.get("_kit_error"):
            st.error(f"Erreur KIT : {st.session_state['_kit_error']}")
        if st.session_state.get("_kit_response"):
            st.write("Réponse KIT :", st.session_state["_kit_response"])


# ===========================
# LAYOUT
# ===========================
colInfo, colForm = st.columns([0.88, 1.28], gap="large")

# ── Colonne Info ─────────────────────────────────────────────────────
with colInfo:
    st.markdown("""
    <div class="info-card">
      <p style="font-family:'Poppins',sans-serif; font-size:1.6rem; font-weight:800; color:white !important; margin:0 0 0.2rem; letter-spacing:-0.02em; line-height:1.2">Ce que vous recevez</p>
      <ul>
        <li><span class="check">✓</span> Une fourchette de prix réaliste, basée sur les ventes récentes de votre secteur</li>
        <li><span class="check">✓</span> Le prix médian au m² pratiqué dans votre quartier ces 12 derniers mois</li>
        <li><span class="check">✓</span> Des biens comparables au vôtre — même type, surface similaire, même zone</li>
        <li><span class="check">✓</span> Un indice d'attractivité de votre secteur (est-ce que les biens partent vite ?)</li>
        <li><span class="check">✓</span> Une estimation affinée selon l'état, la surface, les pièces et la localisation</li>
      </ul>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="info-note">
      🔎 <b style="color:#063970 !important; font-weight:700">Une estimation honnête, pas magique.</b><br>
      <span style="color:#334155 !important">Les données viennent des ventes officiellement enregistrées (source : data.gouv.fr, màj novembre 2025).
      On croise avec ce que vous indiquez pour rester au plus juste. Pas de chiffre sorti du chapeau.</span>
    </div>
    """, unsafe_allow_html=True)

# ── Colonne Formulaire ───────────────────────────────────────────────
with colForm:
    st.markdown("<h2 style='font-family:Poppins,sans-serif;color:#063970;font-size:1.85rem;font-weight:800;margin:0 0 1rem;letter-spacing:-0.02em;line-height:1.15'>Parlez-moi de votre bien</h2>", unsafe_allow_html=True)

    # Commune
    st.markdown("<span class='section-pill'>📍 Localisation</span>", unsafe_allow_html=True)
    area_options = [AUTO_AREA] + list(AREAS.keys())
    st.selectbox("Votre commune", area_options, key="area_name", label_visibility="collapsed")

    if st.session_state.area_name in AREAS:
        st.session_state.detected_area = st.session_state.area_name
        st.session_state.area_locked   = True
    elif st.session_state.get("detected_area") not in AREAS:
        st.session_state.detected_area = DEFAULT_AREA
    effective_area, ai = get_effective_area()

    # Adresse
    st.text_input("", placeholder="🏠  Adresse du bien — ex : 5 Rue de la République", key="addr_typed")
    st.markdown("<div class='addr-helper'>📍 App 100% locale — seules les adresses de Clermont-de-l'Oise et ses communes voisines sont disponibles.</div>",
                unsafe_allow_html=True)

    typed = (st.session_state.addr_typed or "").strip()
    suggestions_display: List[str] = []
    suggestion_geo_map: Dict[str, Dict] = {}

    if len(typed) >= 2:
        seen_labels = set()
        allowed_cities = {info["city"].lower() for info in AREAS.values()}
        if st.session_state.area_name == AUTO_AREA:
            for area_name, info in AREAS.items():
                for res in ban_completion(typed, postcode=info["postcode"], limit=5):
                    if res.get("city", "").lower() not in allowed_cities:
                        continue
                    label = res["label"]
                    if label not in seen_labels:
                        seen_labels.add(label)
                        suggestions_display.append(label)
                        suggestion_geo_map[label] = {**res, "_area": area_name}
        else:
            for res in ban_completion(typed, postcode=ai["postcode"], limit=10):
                if res.get("city", "").lower() not in allowed_cities:
                    continue
                label = res["label"]
                if label not in seen_labels:
                    seen_labels.add(label)
                    suggestions_display.append(label)
                    suggestion_geo_map[label] = res
                suggestion_geo_map[res["label"]] = res

    st.session_state["_suggestion_geo_map"] = suggestion_geo_map

    if suggestions_display:
        prev_display  = st.session_state.get("addr_choice_display","")
        default_index = suggestions_display.index(prev_display) if prev_display in suggestions_display else 0
        st.selectbox("", suggestions_display, index=default_index,
                     key="addr_choice_display", on_change=on_addr_choice_display_change,
                     label_visibility="collapsed")
    elif len(typed) >= 2:
        st.caption("Aucune adresse trouvée — vérifiez l'orthographe.")
        st.session_state.addr_choice_display = ""
        st.session_state.addr_choice         = ""
    else:
        st.session_state.addr_choice_display = ""
        st.session_state.addr_choice         = ""

    st.markdown("<hr class='form-sep'/>", unsafe_allow_html=True)

    # Caractéristiques
    st.markdown("<span class='section-pill'>🏡 Caractéristiques</span>", unsafe_allow_html=True)

    # Ligne 1 : Type de bien (pleine largeur)
    st.selectbox("Type de bien", ["Maison", "Appartement"], index=None, key="bien_type", placeholder="Maison ou Appartement ?")

    # Ligne 2 : Surface | Nb. pièces
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("Surface (m²)", min_value=0.0, max_value=500.0, step=1.0,
                        value=float(st.session_state.surface or 0.0), key="surface")
    with c2:
        st.number_input("Nb. de pièces", min_value=0, max_value=12, step=1,
                        value=int(st.session_state.nb_pieces or 0), key="nb_pieces")

    # Ligne 3 : État général | Dont chambres
    c3, c4 = st.columns(2)
    with c3:
        st.selectbox("État général", ["À rénover", "Moyen", "Bon", "Rénové"],
                     index=None, key="etat", placeholder="État du bien…")
        st.markdown(
            "<div style='margin-top:0.3rem; font-size:0.82rem; color:#94a3b8; font-style:italic; line-height:1.5'>"
            "L'état influe sur l'estimation. Promis, on ne vous juge pas si c'est \"à rénover\" 😄"
            "</div>", unsafe_allow_html=True)
    with c4:
        st.number_input("Dont chambres", min_value=0, max_value=10, step=1,
                        value=int(st.session_state.nb_chambres or 0), key="nb_chambres")

    st.markdown("<hr class='form-sep'/>", unsafe_allow_html=True)

    # Coordonnées
    st.markdown("<span class='section-pill'>✉️ Recevoir l'estimation</span>", unsafe_allow_html=True)
    cc1, cc2 = st.columns(2)
    with cc1:
        st.text_input("", key="prenom", placeholder="👤  Votre prénom")
    with cc2:
        st.text_input("", key="email", placeholder="✉️  Votre email")

    st.checkbox(
        "J'accepte de recevoir cette estimation par email et qu'Hakim me contacte pour l'affiner si besoin. "
        "Pas de spam, pas de relance tous les matins. Promis 🙂",
        key="consent",
    )
    # MutationObserver ciblé : efface le background inline du label BaseWeb + autocomplete off sur number inputs
    st.components.v1.html("""
    <script>
    (function() {
        function fixLabel() {
            var root = window.parent.document;
            root.querySelectorAll('[data-baseweb="checkbox"]').forEach(function(cb) {
                var label = cb.querySelector('div:last-child');
                if (label) {
                    label.style.setProperty('background', 'transparent', 'important');
                    label.style.setProperty('background-color', 'transparent', 'important');
                }
            });
        }
        function fixNumberInputs() {
            var root = window.parent.document;
            root.querySelectorAll('[data-testid="stNumberInput"] input').forEach(function(inp) {
                inp.setAttribute('autocomplete', 'new-password');
                inp.setAttribute('list', 'autocompleteOff');
                inp.setAttribute('name', 'search_' + Math.random());
            });
            // Cache les instructions / popovers natifs
            root.querySelectorAll('[data-testid="InputInstructions"]').forEach(function(el) {
                el.style.setProperty('display', 'none', 'important');
            });
        }
        // Observer dédié pour tuer InputInstructions dès qu'il apparaît dans le DOM
        function watchInputInstructions() {
            var root = window.parent.document.body;
            if (!root) { setTimeout(watchInputInstructions, 200); return; }
            new MutationObserver(function(mutations) {
                mutations.forEach(function(m) {
                    m.addedNodes.forEach(function(node) {
                        if (node.nodeType !== 1) return;
                        // Ciblage direct
                        if (node.dataset && node.dataset.testid === 'InputInstructions') {
                            node.style.setProperty('display', 'none', 'important');
                        }
                        // Ciblage dans les enfants
                        node.querySelectorAll && node.querySelectorAll('[data-testid="InputInstructions"]').forEach(function(el) {
                            el.style.setProperty('display', 'none', 'important');
                        });
                    });
                });
            }).observe(root, { childList: true, subtree: true });
        }
        watchInputInstructions();
        function attachObservers() {
            var root = window.parent.document;
            var checkboxes = root.querySelectorAll('[data-baseweb="checkbox"]');
            if (!checkboxes.length) { setTimeout(attachObservers, 200); return; }
            checkboxes.forEach(function(cb) {
                fixLabel();
                new MutationObserver(fixLabel).observe(cb, {
                    attributes: true, subtree: true, attributeFilter: ['style']
                });
            });
            fixNumberInputs();
        }
        attachObservers();
    })();
    </script>
    """, height=0)

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    # CTA
    ready, filled_count = is_form_ready()
    submitted = st.button("✨  Voir l'estimation de mon bien →", disabled=not ready, use_container_width=True)

    if not ready:
        remaining = 8 - filled_count
        st.markdown(
            f"<div class='form-status'>Il reste {remaining} champ{'s' if remaining>1 else ''} à remplir.</div>",
            unsafe_allow_html=True)
    else:
        st.markdown(
            "<div class='form-status ready'>✅ Tout est renseigné — cliquez pour lancer l'estimation !</div>",
            unsafe_allow_html=True)

    # ── Traitement ───────────────────────────────────────────────────
    if submitted:
        effective_area, ai = get_effective_area()
        geo_map   = st.session_state.get("_suggestion_geo_map", {})
        chosen    = st.session_state.get("addr_choice_display","")
        geo_data  = geo_map.get(chosen)

        if not geo_data:
            detected_area, detected_label = parse_display_choice(chosen)
            addr_label = detected_label if detected_label else chosen
            q = normalize_query_to_area(addr_label, city=ai["city"], postcode=ai["postcode"])
            geo_data = ban_geocode(q, postcode=ai["postcode"])

        if not geo_data:
            st.error("Impossible de localiser cette adresse. Sélectionnez une suggestion dans la liste et réessayez.")
            st.stop()

        addr_postcode  = geo_data.get("postcode","")
        valid_postcodes = {info["postcode"] for info in AREAS.values()}
        if addr_postcode and addr_postcode not in valid_postcodes:
            st.error("Cette adresse ne semble pas être dans le secteur couvert.")
            st.stop()

        if st.session_state.area_name == AUTO_AREA:
            detected_area, _ = parse_display_choice(chosen)
            if not detected_area:
                for aname, ainfo in AREAS.items():
                    if ainfo["postcode"] == addr_postcode:
                        detected_area = aname; break
            if detected_area:
                st.session_state.detected_area = detected_area
                st.session_state.area_locked   = True
                effective_area, ai = get_effective_area()

        geo = {"lat": geo_data["lat"], "lon": geo_data["lon"], "label": geo_data.get("label", chosen)}

        t0       = time.time()
        progress = st.progress(0, text="🔎 Analyse des ventes récentes autour de votre bien…")

        def step(pct, txt, sleep=0.35):
            progress.progress(pct, text=txt); time.sleep(sleep)

        try:
            step(10, "📦 Chargement des ventes officielles (DVF)…", 0.65)
            df_all = load_dvf_local(st.session_state.get("_dvf_bust_manual", DVF_CACHE_BUSTER))
            if df_all.empty:
                st.warning("⚠️ Base DVF locale introuvable.")
                st.markdown("<a href='mailto:hakim@immoclermontoise.fr'>Contactez Hakim →</a>", unsafe_allow_html=True)
                st.stop()

            step(40, "🏡 Recherche de biens similaires dans votre secteur…", 1.1)
            step(65, "📐 Calcul des ajustements (état, surface, localisation)…", 1.0)

            payload = compute_micro_market_estimate(
                df_all=df_all, lat=float(geo["lat"]), lon=float(geo["lon"]),
                bien_type=str(st.session_state.bien_type), surface=float(st.session_state.surface),
                nb_pieces=int(st.session_state.nb_pieces), nb_chambres=int(st.session_state.nb_chambres),
                etat=str(st.session_state.etat))

            step(82, "📊 Calcul de la fourchette et de l'attractivité du secteur…", 1.0)

            dt = time.time() - t0
            if dt < MIN_PROGRESS_SECONDS: time.sleep(MIN_PROGRESS_SECONDS - dt)
            progress.progress(100, text="✅ Votre estimation est prête !")
            time.sleep(0.3)

            st.session_state.geo            = geo
            st.session_state.result_payload = payload

            add_to_kit(prenom=st.session_state.prenom, email=st.session_state.email,
                       area=effective_area, bien_type=str(st.session_state.bien_type),
                       surface=float(st.session_state.surface))
        finally:
            progress.empty()

        st.success(f"Merci {st.session_state.prenom} ✅ Votre estimation est prête.")
        st.rerun()


# ===========================
# RÉSULTATS
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
        st.markdown(f"<div class='result-metric'><p class='mk'>Fourchette estimée</p>"
                    f"<p class='mv'>{eur(hp['est_min'])} – {eur(hp['est_max'])}</p></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='result-metric'><p class='mk'>Fiabilité des données</p>"
                    f"<p class='mv'>{hp['reliability']}</p></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='result-metric'><p class='mk'>Attractivité du secteur</p>"
                    f"<p class='mv'>{tens.get('label','—')} ({tscore}/100)</p></div>", unsafe_allow_html=True)

    st.markdown(
        f"<div class='result-card'>"
        f"<b>Adresse analysée :</b> {geo.get('label','')}<br/>"
        f"<b>Zone (proxy) :</b> {hp.get('quartier','—')} — <b>Distance gare :</b> {hp.get('distance_gare_m','—')} m<br/>"
        f"<b>Prix médian au m² :</b> ~{eur(hp.get('pm2_med',0))} / m²<br/>"
        f"<b>Biens comparables :</b> {hp.get('n',0)} ventes (12 mois) — rayon max : {hp.get('used_radius','—')} m"
        f"</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='tension-box'>{tension_context_message(tscore)}</div>", unsafe_allow_html=True)

    map_points = hp.get("map_points", [])
    if map_points:
        st.markdown("### 🗺️ Localisation des ventes comparables")
        st.caption("Position légèrement floue pour respecter la vie privée des vendeurs.")
        bien_point = pd.DataFrame([{"lat": float(geo["lat"]), "lon": float(geo["lon"])}])
        st.map(pd.concat([bien_point, pd.DataFrame(map_points)], ignore_index=True), zoom=14)

    st.markdown(
        "<div class='result-card'>"
        "<b style='color:#94a3b8'>Ce que les données ne peuvent pas voir à votre place :</b>"
        "<ul class='disclaimer-list'>"
        "<li>Les nuisances (route, voisinage, bruit, vis-à-vis…)</li>"
        "<li>La luminosité et l'exposition</li>"
        "<li>L'état réel et la qualité des finitions</li>"
        "<li>Les travaux faits ou à prévoir, isolation, DPE</li>"
        "<li>L'agencement, les volumes, l'entretien</li>"
        "<li>Les extérieurs, cave, garage, stationnement, charges de copropriété…</li>"
        "</ul>"
        "<span style='color:#64748b; font-size:0.92rem'>Cette fourchette est une <b style='color:#94a3b8'>base solide et honnête</b>. "
        "Mais pour un chiffre vraiment précis et des conseils adaptés à votre projet, rien ne vaut un échange de vive voix.</span>"
        "</div>", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='booking-btn'><a href='{BOOKING_URL}' target='_blank'>"
        f"📞 Affiner cette estimation avec Hakim — RDV gratuit, sans engagement"
        f"</a></div>", unsafe_allow_html=True)
    st.caption("Un échange de 20 minutes pour un chiffre précis et des conseils pour valoriser votre bien.")

    if tens.get("detail"):
        st.caption(f"📌 {tens['detail']}")

    if hp.get("preview"):
        with st.expander("🧾 Voir les biens comparables (localisation volontairement vague)"):
            for r in hp["preview"]:
                st.markdown(
                    f"- **{r['type_local']}** · **{r['surface']} m²** · **{eur(r['prix'])}** · "
                    f"**{r['mois']}** · **{r['commune']}** (~{r['dist']} m)")

    if DEBUG:
        with st.expander("🧪 Debug payload"):
            st.write(hp); st.write("geo:", geo)
