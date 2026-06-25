import streamlit as st
import numpy as np
import pandas as pd
import requests
import time
import pydeck as pdk
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Import du module d'envoi d'email Brevo (fichier email_sender.py a cote de app.py)
from email_sender import send_estimation_email

# Import du module d'ajout de membres Ghost (fichier ghost_sender.py a cote de app.py)
from ghost_sender import add_to_ghost

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

# Branding : images lues depuis le dossier assets/ puis encodees en base64.
# Commit simplement assets/hakim-photo.jpg et assets/hakim-signature.png dans ton repo.
def _img_b64(path: str) -> str:
    try:
        return base64.b64encode(Path(path).read_bytes()).decode()
    except Exception:
        return ""

_photo_b64 = _img_b64("assets/hakim-photo.jpg")
_sign_b64  = _img_b64("assets/hakim-signature.png")
HAKIM_PHOTO_SRC = f"data:image/jpeg;base64,{_photo_b64}" if _photo_b64 else ""
HAKIM_SIGN_SRC  = f"data:image/png;base64,{_sign_b64}"  if _sign_b64  else ""

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
DVF_CACHE_BUSTER = "v10"

# ===========================
# Session state
# ===========================
_defaults = {
    "geo": None, "result_payload": None,
    "area_name": AUTO_AREA, "area_locked": False, "detected_area": DEFAULT_AREA,
    "bien_type": None, "surface": 0, "etat": None,
    "nb_pieces": 0, "nb_chambres": 0,
    "addr_typed": "", "addr_choice_display": "", "addr_choice": "",
    "prenom": "", "email": "", "consent": False,
    "_kit_result": None, "_kit_error": "", "_kit_response": "",
    "_brevo_result": None, "_brevo_error": "",
    "_ghost_result": None, "_ghost_error": "", "_ghost_response": "",
}
for k, v in _defaults.items():
    st.session_state.setdefault(k, v)

DEBUG = False
try:
    DEBUG = (st.query_params.get("debug", "0") == "1")
except Exception:
    DEBUG = False

# Détecte si l'app est embarquée dans Ghost (param maison ?ghost=1).
# On n'utilise PAS "embed" car Streamlit le consomme en interne et le retire
# de query_params, ce qui rendrait la détection inopérante dans l'iframe.
IS_EMBED = False
try:
    IS_EMBED = (st.query_params.get("ghost", "") == "1")
except Exception:
    IS_EMBED = False

# ===========================
# CSS — Design ludique clair
# ===========================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800;900&display=swap');

/* RESET & BASE */
html, body, [class*="stApp"] {{
    font-family: 'Poppins', sans-serif !important;
    font-size: 15px !important;
    background: #ffffff !important;
    color: #1e293b !important;
    overflow-x: hidden !important;
}}
.main .block-container {{
    background: #ffffff !important;
    padding-top: 1.5rem !important;
    max-width: 1280px !important;
}}
section[data-testid="stSidebar"] {{ display: none !important; }}

/* Cache les elements Streamlit Cloud (fork, menu, toolbar) */
#MainMenu {{ display: none !important; }}
header[data-testid="stHeader"] {{ display: none !important; }}
footer {{ display: none !important; }}
footer[data-testid="stFooter"] {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stStatusWidget"] {{ display: none !important; }}
[data-testid="stBottom"] {{ display: none !important; }}
.stDeployButton {{ display: none !important; }}
.viewerBadge_container__r5tak {{ display: none !important; }}
.viewerBadge_link__qRIco {{ display: none !important; }}
a[href*="streamlit.io"] {{ display: none !important; }}
a[href*="streamlit.app/cloud"] {{ display: none !important; }}

/* TYPOGRAPHIE */
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

/* CARD INFO (colonne gauche) */
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

/* CARTE HAKIM (branding / reassurance) */
.hakim-card {{
    background: white;
    border-radius: 20px;
    padding: 1.3rem 1.4rem;
    margin-top: 0.8rem;
    box-shadow: 0 4px 16px rgba(6,57,112,0.08);
    border: 1.5px solid #f1f5f9;
}}
.hakim-top {{
    display: flex; align-items: center; gap: 0.9rem;
    margin-bottom: 0.85rem;
}}
.hakim-photo {{
    width: 66px; height: 66px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
    border: 3px solid {ACCENT};
    box-shadow: 0 4px 12px rgba(255,126,121,0.30);
}}
.hakim-name {{
    font-family: 'Poppins', sans-serif !important;
    font-weight: 800 !important;
    font-size: 1.12rem !important;
    color: {PRIMARY} !important;
    margin: 0 !important;
    line-height: 1.2;
}}
.hakim-role {{
    font-size: 0.82rem !important;
    color: #94a3b8 !important;
    margin: 0.12rem 0 0 !important;
    font-weight: 600 !important;
}}
.hakim-words {{
    font-size: 0.93rem !important;
    color: #334155 !important;
    line-height: 1.6 !important;
    margin: 0 0 0.7rem !important;
    font-weight: 500 !important;
}}
.hakim-sign {{
    height: 50px; width: auto;
    display: block;
    opacity: 0.92;
}}

/* FORM WRAPPER (colonne droite) */
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

/* SECTION PILLS */
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

/* LABELS */
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

/* INPUT TEXT */
[data-testid="stTextInput"] > div,
[data-testid="stTextInput"] > div > div,
[data-testid="stTextInput"] > div > div > div,
[data-baseweb="base-input"],
[data-baseweb="input-container"] {{
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    outline: none !important;
}}
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
    outline: none !important;
    box-shadow: none !important;
    caret-color: {ACCENT} !important;
    transition: border-color 0.2s, box-shadow 0.2s, background 0.2s !important;
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

/* NUMBER INPUT */
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

/* SELECTBOX */
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

/* ANTI-CLIP */
[data-testid="stTextInput"],
[data-testid="stSelectbox"],
[data-testid="stNumberInput"],
[data-testid="stCheckbox"],
[data-testid="stTextInput"] > div,
[data-testid="stSelectbox"] > div {{
    overflow: visible !important;
}}

/* CHECKBOX */
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
[data-baseweb="checkbox"] > div:last-child,
[data-baseweb="checkbox"] > div:last-child *,
[data-baseweb="checkbox"] label,
[data-baseweb="checkbox"] label * {{
    background: transparent !important;
    background-color: transparent !important;
}}
[data-testid="stCheckbox"] input:checked + div {{
    background: {ACCENT} !important;
    border-color: {ACCENT} !important;
}}

/* ALIGNEMENT COLONNES CARACTERISTIQUES */
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] > div {{
    min-height: 58px !important;
}}

/* ESPACEMENT CHAMPS CONTACT */
[data-testid="stTextInput"] {{
    margin-bottom: 0.6rem !important;
}}

/* CTA BUTTON */
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

/* SEPARATEUR */
.form-sep {{
    border: none;
    border-top: 2px dashed #f1f5f9;
    margin: 1.3rem 0 1rem;
}}

/* HELPER ADRESSE */
.addr-helper {{
    font-size: 0.82rem !important;
    color: #94a3b8 !important;
    margin-top: -0.15rem;
    margin-bottom: 0.65rem;
    font-style: italic;
    font-weight: 600 !important;
}}

/* STATUT FORMULAIRE (barre de progression) */
.ico-progress-track {{
    background: #f1f5f9;
    border-radius: 999px;
    height: 12px;
    overflow: hidden;
}}
.ico-progress-fill {{
    height: 12px;
    border-radius: 999px;
    transition: width 0.45s cubic-bezier(.34,1.56,.64,1);
}}
.ico-progress-msg {{
    text-align: center;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.92rem !important;
    font-weight: 700 !important;
    margin: 0.55rem 0 0 !important;
}}

/* METRIQUES RESULTATS */
.result-metric {{
    background: linear-gradient(135deg, #063970, #0a5cb8);
    border-radius: 20px;
    padding: 1.3rem 1.2rem;
    box-shadow: 0 4px 20px rgba(6,57,112,0.25);
    position: relative; overflow: hidden;
    margin-bottom: 0.8rem;
}}
.result-metric::before {{
    content: ""; position: absolute;
    top: 0; left: 0; right: 0; height: 4px;
    background: rgba(255,255,255,0.35);
    border-radius: 20px 20px 0 0;
}}
.result-metric .mk {{
    font-size: 0.75rem !important; color: rgba(255,255,255,0.80) !important;
    text-transform: uppercase; letter-spacing: 0.09em;
    margin: 0; font-weight: 800 !important;
}}
.result-metric .mv {{
    font-size: 1.4rem !important; font-weight: 900 !important;
    color: white !important; margin: 0.25rem 0 0;
    letter-spacing: -0.02em;
}}

/* CARD RESULTATS */
.result-card {{
    background: white;
    border-radius: 18px;
    padding: 1.2rem 1.3rem;
    margin-bottom: 0.8rem;
    box-shadow: 0 4px 16px rgba(6,57,112,0.07);
    border-left: 4px solid {ACCENT};
}}
.result-card b {{ color: #334155 !important; font-weight: 800 !important; }}

/* TENSION BOX */
.tension-box {{
    background: #fff7f7;
    border-left: 4px solid {ACCENT};
    border-radius: 0 18px 18px 0;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
    font-size: 1.05rem !important;
    line-height: 1.65;
    color: #334155 !important;
}}

/* DISCLAIMER LIST */
.disclaimer-list {{
    list-style: none; padding: 0; margin: 0.7rem 0 1rem;
}}
.disclaimer-list li {{
    padding: 0.32rem 0;
    font-size: 1.05rem !important;
    color: #64748b !important;
    display: flex; align-items: flex-start; gap: 0.55rem;
    font-weight: 600 !important;
}}
.disclaimer-list li::before {{
    content: "→";
    color: {ACCENT} !important;
    font-weight: 900; flex-shrink: 0;
}}

/* BOUTON RDV */
.booking-btn a {{
    display: block; text-align: center;
    background: {ACCENT};
    color: white !important;
    font-family: 'Poppins', sans-serif !important;
    font-weight: 900 !important;
    font-size: 1.25rem !important;
    border-radius: 20px;
    padding: 1.5rem 2rem;
    min-height: 80px;
    display: flex; align-items: center; justify-content: center;
    text-decoration: none !important;
    box-shadow: 0 10px 36px rgba(255,126,121,0.40);
    margin-top: 0.5rem;
    transition: all 0.22s cubic-bezier(.34,1.56,.64,1);
    letter-spacing: 0.01em;
}}
.booking-btn a:hover {{
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 18px 48px rgba(255,126,121,0.55);
    background: #ff6b65;
}}

/* HR */
hr {{
    border: none;
    border-top: 2px dashed #e2e8f0;
    margin: 1.5rem 0;
}}

/* ALERTS */
[data-testid="stAlert"] {{
    background: #f0fdf4 !important;
    border: 2px solid #bbf7d0 !important;
    border-radius: 16px !important;
    color: #16a34a !important;
}}

/* EXPANDER */
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

/* MAP */
[data-testid="stDeckGlJsonChart"], iframe {{
    border-radius: 20px !important;
    overflow: hidden;
    border: 2px solid #f1f5f9 !important;
    box-shadow: 0 4px 16px rgba(6,57,112,0.07) !important;
}}

/* CAPTIONS */
[data-testid="stCaptionContainer"] p {{
    color: #94a3b8 !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
}}

/* SCROLLBAR */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: #f1f5f9; }}
::-webkit-scrollbar-thumb {{ background: rgba(6,57,112,0.15); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {ACCENT}; }}

/* MOBILE, anti-debordement horizontal */
@media (max-width: 640px) {{
    html, body, [class*="stApp"], .main, .main .block-container {{
        overflow-x: hidden !important;
        max-width: 100% !important;
    }}
    .main .block-container {{
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
    }}
    [data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap !important;
        gap: 0.5rem !important;
    }}
    [data-testid="stHorizontalBlock"] > [data-testid="column"],
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
        flex: 1 1 100% !important;
        min-width: 100% !important;
        width: 100% !important;
    }}
    [data-testid="stTextInput"], [data-testid="stSelectbox"],
    [data-testid="stNumberInput"], [data-testid="stNumberInput"] > div {{
        max-width: 100% !important;
        min-width: 0 !important;
    }}
    .info-card, .info-note, .hakim-card, .result-card, .result-metric, .tension-box {{
        max-width: 100% !important;
    }}
}}
</style>
""", unsafe_allow_html=True)

# CSS "pas de scroll interne" : UNIQUEMENT en mode embarqué (iframe Ghost).
# En accès direct (icostim.streamlit.app), on laisse Streamlit gérer son scroll
# normalement, sinon le bas de page devient inaccessible.
if IS_EMBED:
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    section.main, .main, .main .block-container {
        height: auto !important;
        min-height: 0 !important;
        max-height: none !important;
        overflow: visible !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ===========================
# Helpers
# ===========================
def norm(s: str) -> str:
    return (s or "").strip().lower().replace("\u2019", "'")

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
    s = str(x or "").strip().lower().replace("\u2019", "'")
    if "appart" in s: return "Appartement"
    if "maison" in s: return "Maison"
    return "Autre"

def tension_context_message(tscore: int) -> str:
    if tscore >= 65:
        return "🔥 <b>Votre secteur est actuellement très recherché.</b> Les biens similaires partent vite et les prix se tiennent bien. C'est le bon moment pour vendre, à condition de bien positionner le prix dès le départ."
    elif tscore >= 45:
        return "⚡ <b>Le marché est actif sur votre secteur.</b> Les acheteurs sont présents, mais ils comparent. Une mise en valeur soignée et un prix juste feront toute la différence."
    elif tscore >= 28:
        return "🙂 <b>Le marché est équilibré.</b> Ni en surchauffe, ni en pause. Les biens bien présentés et correctement positionnés se vendent sans trop traîner."
    else:
        return "📈 <b>Le marché est stable sur votre secteur.</b> Les transactions se font à un rythme posé, ce qui veut dire que le prix de départ et la présentation du bien sont les deux leviers les plus importants pour vendre dans de bonnes conditions."

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
def add_to_kit(prenom: str, email: str, area: str, bien_type: str, surface: float,
               est_min: float = 0, est_max: float = 0, pm2: float = 0,
               reliability: str = "", tension_label: str = "", tension_score: int = 0,
               adresse: str = "") -> bool:
    try:
        api_key = st.secrets.get("KIT_API_KEY", "")
        form_id = st.secrets.get("KIT_FORM_ID", "")
        if not api_key or not form_id:
            st.session_state["_kit_result"] = False
            st.session_state["_kit_error"]  = f"Secrets manquants, api_key={'OK' if api_key else 'VIDE'}, form_id={'OK' if form_id else 'VIDE'}"
            return False
        url = f"https://api.convertkit.com/v3/forms/{form_id}/subscribe"
        payload = {
            "api_key": api_key,
            "email": email,
            "first_name": prenom,
            "fields": {
                "commune":          area,
                "type_bien":        bien_type,
                "surface":          str(int(surface)),
                "source":           "EstimeClermont",
                "adresse":          adresse,
                "estimation_min":   str(int(est_min)),
                "estimation_max":   str(int(est_max)),
                "prix_m2":          str(int(pm2)),
                "fiabilite":        reliability,
                "attractivite":     f"{tension_label} ({tension_score}/100)",
            },
        }
        r = requests.post(url, json=payload, timeout=10)
        st.session_state["_kit_result"]   = r.status_code in (200, 201)
        st.session_state["_kit_response"] = f"Status {r.status_code} : {r.text[:400]}"
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
    # nb_pieces : on le rend numerique si present, sinon on cree la colonne vide
    if "nb_pieces" in df.columns:
        df["nb_pieces"] = pd.to_numeric(df["nb_pieces"], errors="coerce")
    else:
        df["nb_pieces"] = np.nan
    df["type_local_raw"] = df.get("type_local")
    df["type_local"]     = df["type_local_raw"].apply(normalize_type_local)
    df = df.dropna(subset=["date_mutation","valeur_fonciere","surface_reelle_bati","longitude","latitude","type_local"])
    df = df[df["type_local"].isin(["Maison","Appartement"])]
    df = df[(df["valeur_fonciere"] > 1000) & (df["surface_reelle_bati"] >= 10)]
    return df

def dvf_select_similaires_strict(df_all, lat, lon, bien_type, surface, nb_pieces=0) -> Tuple[pd.DataFrame, int, float, int]:
    """
    Selectionne les ventes comparables avec elargissement progressif sur 3 axes :
      1. fenetre temporelle : 12 mois, puis 18, puis 24 (on garde la donnee la plus fraiche possible)
      2. rayon geographique : 600m vers 3500m
      3. surface : tolerances croissantes
      4. nombre de pieces : +/-1, puis +/-2, puis ignore (les ventes sans nb_pieces ne sont jamais exclues)
    Retourne (df, rayon_utilise, tolerance_surface_utilisee, fenetre_mois_utilisee).
    """
    if df_all.empty: return pd.DataFrame(), 0, 0.0, 0
    target_type = normalize_type_local(bien_type)
    surface     = float(surface)
    max_date    = df_all["date_mutation"].max()
    if pd.isna(max_date): return pd.DataFrame(), 0, 0.0, 0

    windows_months = [12, 18, 24]
    radii          = [600, 900, 1500, 2500, 3500]
    tolerances     = [0.20,0.25,0.30,0.35] if target_type=="Appartement" else [0.25,0.30,0.40,0.45]
    # Tolerance sur le nb de pieces, du plus serre au plus large.
    # None = on ignore completement le critere (dernier filet de securite).
    pieces_tols    = [1, 2, None] if int(nb_pieces or 0) > 0 else [None]
    min_needed     = 4

    best = pd.DataFrame(); used_radius = 0; used_tol = 0.0; used_window = 0

    for win in windows_months:
        df = df_all[df_all["date_mutation"] >= max_date - pd.Timedelta(days=int(win*30.4))].copy()
        if df.empty: continue
        df["type_local"] = df["type_local"].apply(normalize_type_local)
        df = df[df["type_local"] == target_type].copy()
        if df.empty: continue

        lat0, lon0 = float(lat), float(lon)
        R    = 6371000.0
        phi1 = np.radians(lat0)
        phi2 = np.radians(df["latitude"].to_numpy(float))
        dphi = np.radians(df["latitude"].to_numpy(float)  - lat0)
        dl   = np.radians(df["longitude"].to_numpy(float) - lon0)
        a    = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dl/2)**2
        df["distance_m"] = 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        for rad in radii:
            df_r = df[df["distance_m"] <= rad].copy()
            if df_r.empty: continue
            for tol in tolerances:
                lo, hi = surface*(1-tol), surface*(1+tol)
                df_s_base = df_r[(df_r["surface_reelle_bati"]>=lo)&(df_r["surface_reelle_bati"]<=hi)].copy()
                if df_s_base.empty: continue
                for ptol in pieces_tols:
                    df_s = df_s_base.copy()
                    # On ne filtre sur les pieces que si on a un nb cible ET que la donnee existe.
                    # Les ventes sans nb_pieces (NaN) sont toujours conservees pour ne pas vider le marche.
                    if ptol is not None and "nb_pieces" in df_s.columns:
                        p = pd.to_numeric(df_s["nb_pieces"], errors="coerce")
                        df_s = df_s[(p.isna()) | ((p >= nb_pieces - ptol) & (p <= nb_pieces + ptol))]
                    if df_s.empty: continue
                    df_s["prix_m2"] = df_s["valeur_fonciere"] / df_s["surface_reelle_bati"]
                    df_s = df_s.replace([np.inf,-np.inf], np.nan).dropna(subset=["prix_m2"])
                    if len(df_s) >= 10:
                        q10, q90 = df_s["prix_m2"].quantile(0.10), df_s["prix_m2"].quantile(0.90)
                        df_s = df_s[(df_s["prix_m2"]>=q10)&(df_s["prix_m2"]<=q90)]
                    if len(df_s) >= min_needed:
                        best = df_s; used_radius = rad; used_tol = tol; used_window = win; break
                if not best.empty: break
            if not best.empty: break
        if not best.empty: break

    if best.empty:
        # Fallback ultime : sur 24 mois, on prend les 3 biens les plus proches repondant a la surface,
        # sans contrainte de pieces ni de volume minimum.
        df = df_all[df_all["date_mutation"] >= max_date - pd.Timedelta(days=int(24*30.4))].copy()
        if df.empty:
            return pd.DataFrame(), 0, 0.0, 0
        df["type_local"] = df["type_local"].apply(normalize_type_local)
        df = df[df["type_local"] == target_type].copy()
        if df.empty:
            return pd.DataFrame(), 0, 0.0, 0
        lat0, lon0 = float(lat), float(lon)
        R    = 6371000.0
        phi1 = np.radians(lat0)
        phi2 = np.radians(df["latitude"].to_numpy(float))
        dphi = np.radians(df["latitude"].to_numpy(float)  - lat0)
        dl   = np.radians(df["longitude"].to_numpy(float) - lon0)
        a    = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dl/2)**2
        df["distance_m"] = 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        tol = tolerances[-1]; rad = radii[-1]; lo, hi = surface*(1-tol), surface*(1+tol)
        df_fb = df[(df["distance_m"]<=rad)&(df["surface_reelle_bati"]>=lo)&(df["surface_reelle_bati"]<=hi)].copy()
        if df_fb.empty:
            return pd.DataFrame(), 0, 0.0, 0
        df_fb["prix_m2"] = df_fb["valeur_fonciere"] / df_fb["surface_reelle_bati"]
        df_fb = df_fb.replace([np.inf,-np.inf], np.nan).dropna(subset=["prix_m2"])
        return df_fb.sort_values(["distance_m","date_mutation"], ascending=[True,False]).head(3), rad, tol, 24

    return best.sort_values(["distance_m","date_mutation"], ascending=[True,False]).copy(), used_radius, used_tol, used_window

def reliability_label(n: int) -> str:
    if n > 15: return "🟢 Très élevée"
    if n >= 8:  return "🟢 Élevée"
    if n >= 4:  return "🟡 Bonne"
    if n >= 2:  return "🟠 Modérée"
    return "🔴 Faible"

def market_tension_index(df_local: pd.DataFrame, used_radius: int, used_window: int = 12) -> Dict[str, Any]:
    if df_local is None or df_local.empty or used_radius <= 0:
        return {"score": 0, "label": "🔴 Inconnu", "detail": "Pas assez de données"}
    n          = int(len(df_local))
    area_km2   = np.pi * (used_radius/1000.0)**2

    # On ramene le nombre de ventes a un RYTHME ANNUEL equivalent.
    # Sinon, elargir la fenetre a 24 mois gonflerait artificiellement l'attractivite.
    win = max(1, int(used_window or 12))
    n_annual   = n * (12.0 / win)
    density    = n_annual / max(1e-6, area_km2)

    # Score densite : calibre pour un petit marche (1-3/km2/an = normal, 5+/km2/an = actif)
    s_density  = 100 * (1 - np.exp(-density / 4))

    # Score fraicheur : derniere vente < 90j = tres bon, < 180j = correct
    last_date  = pd.to_datetime(df_local["date_mutation"]).max()
    days_since = int(max(0,(pd.Timestamp.utcnow().tz_localize(None)-pd.to_datetime(last_date).tz_localize(None)).days))
    s_recency  = 100 * np.exp(-days_since / 120)

    # Score volume brut : bonus si plus de 4 ventes dans le rayon min (800m), ramene au rythme annuel
    df_close   = df_local[df_local.get("distance_m", pd.Series([used_radius]*n)) <= 800] if "distance_m" in df_local.columns else df_local
    n_close_annual = len(df_close) * (12.0 / win)
    s_volume   = float(clamp(n_close_annual / 8 * 100, 0, 100))

    # Score homogeneite prix (IQR faible = marche stable et lisible)
    pm2 = pd.to_numeric(df_local.get("prix_m2"), errors="coerce").replace([np.inf,-np.inf], np.nan).dropna()
    iqr_ratio = 1.0
    if not pm2.empty:
        iqr_ratio = (float(pm2.quantile(0.75)) - float(pm2.quantile(0.25))) / max(1.0, float(pm2.median()))
    s_homo = 100 * np.exp(-iqr_ratio / 0.25)

    # Score global pondere
    score = float(clamp(
        0.40 * s_density + 0.30 * s_recency + 0.20 * s_volume + 0.10 * s_homo,
        0, 100))

    label = ("🔥 Très attractif" if score >= 65 else "⚡ Attractif" if score >= 45
             else "🙂 Équilibré" if score >= 28 else "📈 Marché stable")
    detail_win = "" if win == 12 else f" · données sur {win} mois"
    return {"score": int(round(score)), "label": label,
            "detail": f"Densité ~{density:.1f}/km2/an · Dernière vente {days_since}j · IQR ~{iqr_ratio:.2f}{detail_win}"}

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
    pct *= 0.90 if tension_score>=65 else 0.95 if tension_score>=45 else 1.00 if tension_score>=28 else 1.08
    return float(pct), ((6500.0,15000.0) if normalize_type_local(bien_type)=="Appartement" else (9000.0,22000.0))

def compute_micro_market_estimate(df_all, lat, lon, bien_type, surface, nb_pieces, nb_chambres, etat):
    distance_m  = haversine_m(lat, lon, GARE_LAT, GARE_LON)
    quartier    = quartier_from_distance(distance_m)
    df_local, used_radius, used_tol, used_window = dvf_select_similaires_strict(df_all, lat, lon, bien_type, surface, nb_pieces)
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
    tension    = market_tension_index(df_local, used_radius if used_radius else 0, used_window)
    tscore     = int(tension.get("score", 0))
    tilt       = 0.022 if tscore>=65 else 0.012 if tscore>=45 else 0.0 if tscore>=28 else -0.018
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
            try:
                _nbp = int(float(r.get("nb_pieces")))
            except (TypeError, ValueError):
                _nbp = 0
            preview.append({"type_local":str(r.get("type_local","")),
                "surface":int(round(float(r.get("surface_reelle_bati",0)))),
                "nb_pieces":_nbp,
                "prix":float(r.get("valeur_fonciere",0)),"mois":mois,
                "commune":str(r.get("nom_commune","Secteur")),
                "dist":int(round(float(r.get("distance_m",0))/100)*100)})
            rng = np.random.default_rng(seed=int(r.get("valeur_fonciere",0)) % 9999)
            map_points.append({"lat":float(r["latitude"])+rng.uniform(-0.00025,0.00025),
                               "lon":float(r["longitude"])+rng.uniform(-0.00025,0.00025)})
    return {"bien_type":target_type,"surface":float(surface),"quartier":quartier,
        "distance_gare_m":int(round(distance_m)),"pm2_med":float(pm2_med),"adj":adj,
        "adj_factor":float(adj_factor),"tilt":float(tilt),"est_min":est_min,"est_max":est_max,
        "n":n,"used_radius":int(used_radius or 0),"used_tol":float(used_tol or 0),"used_window":int(used_window or 0),
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
        st.write(f"KIT_API_KEY : {'OK ' + api_key[:6] + '...' if api_key else 'MANQUANTE'}")
        st.write(f"KIT_FORM_ID : {'OK ' + form_id if form_id else 'MANQUANT'}")
        if st.session_state.get("_kit_result") is not None:
            st.write("Dernier envoi KIT :", "OK" if st.session_state["_kit_result"] else "Échec")
        if st.session_state.get("_kit_error"):
            st.error(f"Erreur KIT : {st.session_state['_kit_error']}")
        if st.session_state.get("_kit_response"):
            st.write("Réponse KIT :", st.session_state["_kit_response"])

        st.markdown("---")
        smtp_user = st.secrets.get("BREVO_SMTP_USER", "")
        smtp_pass = st.secrets.get("BREVO_SMTP_PASS", "")
        from_email = st.secrets.get("BREVO_FROM_EMAIL", "")
        st.write(f"BREVO_SMTP_USER  : {'OK ' + smtp_user if smtp_user else 'MANQUANT'}")
        st.write(f"BREVO_SMTP_PASS  : {'OK (' + str(len(smtp_pass)) + ' caractères)' if smtp_pass else 'MANQUANT'}")
        st.write(f"BREVO_FROM_EMAIL : {'OK ' + from_email if from_email else 'MANQUANT'}")
        if st.session_state.get("_brevo_result") is not None:
            st.write("Dernier envoi Brevo :", "OK" if st.session_state["_brevo_result"] else "Échec")
        if st.session_state.get("_brevo_error"):
            st.error(f"Erreur Brevo : {st.session_state['_brevo_error']}")

        st.markdown("---")
        ghost_url = st.secrets.get("GHOST_ADMIN_URL", "")
        ghost_key = st.secrets.get("GHOST_ADMIN_KEY", "")
        st.write(f"GHOST_ADMIN_URL : {'OK ' + ghost_url if ghost_url else 'MANQUANT'}")
        st.write(f"GHOST_ADMIN_KEY : {'OK (' + str(len(ghost_key)) + ' caractères)' if ghost_key else 'MANQUANTE'}")
        if st.session_state.get("_ghost_result") is not None:
            st.write("Dernier ajout Ghost :", "OK" if st.session_state["_ghost_result"] else "Échec")
        if st.session_state.get("_ghost_error"):
            st.error(f"Erreur Ghost : {st.session_state['_ghost_error']}")
        if st.session_state.get("_ghost_response"):
            st.write("Réponse Ghost :", st.session_state["_ghost_response"])


# ===========================
# LAYOUT
# ===========================
colInfo, colForm = st.columns([0.88, 1.28], gap="large")

# Colonne Info
with colInfo:
    st.markdown("""
    <div class="info-card">
      <p style="font-family:'Poppins',sans-serif; font-size:1.6rem; font-weight:800; color:white !important; margin:0 0 0.2rem; letter-spacing:-0.02em; line-height:1.2">Ce que vous recevez</p>
      <ul>
        <li><span class="check">✓</span> Une fourchette de prix réaliste, basée sur les ventes récentes de votre secteur</li>
        <li><span class="check">✓</span> Le prix médian au m² pratiqué dans votre quartier ces 12 derniers mois</li>
        <li><span class="check">✓</span> Des biens comparables au vôtre, même type, surface similaire, même zone</li>
        <li><span class="check">✓</span> Un indice d'attractivité de votre secteur (est-ce que les biens partent vite ?)</li>
        <li><span class="check">✓</span> Une estimation affinée selon l'état, la surface, les pièces et la localisation</li>
      </ul>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="info-note">
      🔎 <b style="color:#063970 !important; font-weight:700">Une estimation honnête, pas magique.</b><br>
      <span style="color:#334155 !important">Les données viennent des ventes officiellement enregistrées (source : data.gouv.fr, màj avril 2026).
      On croise avec ce que vous indiquez pour rester au plus juste. Pas de chiffre sorti du chapeau.<br><br>
      ⚠️ Les prix affichés sur LeBonCoin ou SeLoger, c'est ce que les vendeurs demandent. Pas ce que les acheteurs paient vraiment. Nuance.</span>
    </div>
    """, unsafe_allow_html=True)

    # Carte Hakim (branding + reassurance)
    st.markdown(f"""
    <div class="hakim-card">
      <div class="hakim-top">
        <img class="hakim-photo" src="{HAKIM_PHOTO_SRC}" alt="Hakim Saber" />
        <div>
          <p class="hakim-name">Hakim Saber</p>
          <p class="hakim-role">Conseiller immobilier, Clermont-de-l'Oise</p>
        </div>
      </div>
      <p class="hakim-words">Derrière cette estimation, il y a moi. Pas un algorithme anonyme qui n'a jamais mis les pieds dans le coin. Vos infos restent chez moi, et je vous recontacte seulement si vous le voulez.</p>
      <img class="hakim-sign" src="{HAKIM_SIGN_SRC}" alt="Signature Hakim Saber" />
    </div>
    """, unsafe_allow_html=True)

# Colonne Formulaire
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
    st.text_input("", placeholder="🏠  Adresse du bien, ex : 5 Rue de la République", key="addr_typed")
    st.markdown("<div class='addr-helper'>📍 App 100% locale, seules les adresses de Clermont-de-l'Oise et ses communes voisines sont disponibles.</div>",
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
        st.caption("Aucune adresse trouvée, vérifiez l'orthographe.")
        st.session_state.addr_choice_display = ""
        st.session_state.addr_choice         = ""
    else:
        st.session_state.addr_choice_display = ""
        st.session_state.addr_choice         = ""

    st.markdown("<hr class='form-sep'/>", unsafe_allow_html=True)

    # Caracteristiques
    st.markdown("<span class='section-pill'>🏡 Caractéristiques</span>", unsafe_allow_html=True)

    # Ligne 1 : Type de bien (pleine largeur)
    st.selectbox("Type de bien", ["Maison", "Appartement"], index=None, key="bien_type", placeholder="Maison ou Appartement ?")

    # Ligne 2+3
    ca, cb = st.columns(2)
    with ca:
        st.number_input("Surface (m²)", min_value=0, max_value=500, step=1,
                        value=int(st.session_state.surface or 0), key="surface")
        st.selectbox("État général", ["À rénover", "Moyen", "Bon", "Rénové"],
                     index=None, key="etat", placeholder="État du bien…")
        st.markdown(
            "<div style='font-size:0.82rem; color:#94a3b8; font-style:italic; line-height:1.5; margin-top:0.2rem'>"
            "L'état influe sur l'estimation. Promis, on ne vous juge pas si c'est \"à rénover\" 😄"
            "</div>", unsafe_allow_html=True)
    with cb:
        st.number_input("Nb. de pièces", min_value=0, max_value=12, step=1,
                        value=int(st.session_state.nb_pieces or 0), key="nb_pieces")
        st.number_input("Dont chambres", min_value=0, max_value=10, step=1,
                        value=int(st.session_state.nb_chambres or 0), key="nb_chambres")

    st.markdown("<hr class='form-sep'/>", unsafe_allow_html=True)

    # Coordonnees
    st.markdown("<span class='section-pill'>✉️ Recevoir l'estimation</span>", unsafe_allow_html=True)
    cc1, cc2 = st.columns(2)
    with cc1:
        st.text_input("", key="prenom", placeholder="👤  Votre prénom")
    with cc2:
        st.text_input("", key="email", placeholder="✉️  Votre email")

    st.checkbox(
        "J'accepte de recevoir mon estimation par email. "
        "Vos données sont en sécurité, pas de spam ni de relance quotidienne, promis 🙂",
        key="consent",
    )
    # MutationObserver cible : efface le background inline du label BaseWeb + autocomplete off sur number inputs
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
            root.querySelectorAll('[data-testid="InputInstructions"]').forEach(function(el) {
                el.style.setProperty('display', 'none', 'important');
            });
        }
        function watchInputInstructions() {
            var root = window.parent.document.body;
            if (!root) { setTimeout(watchInputInstructions, 200); return; }
            new MutationObserver(function(mutations) {
                mutations.forEach(function(m) {
                    m.addedNodes.forEach(function(node) {
                        if (node.nodeType !== 1) return;
                        if (node.dataset && node.dataset.testid === 'InputInstructions') {
                            node.style.setProperty('display', 'none', 'important');
                        }
                        node.querySelectorAll && node.querySelectorAll('[data-testid="InputInstructions"]').forEach(function(el) {
                            el.style.setProperty('display', 'none', 'important');
                        });
                    });
                });
            }).observe(root, { childList: true, subtree: true });
        }
        watchInputInstructions();

        function killStreamlitBranding() {
            var doc = window.parent.document;
            if (!doc || !doc.body) { setTimeout(killStreamlitBranding, 300); return; }
            function nuke() {
                doc.querySelectorAll('footer, [data-testid="stBottom"], [data-testid="stFooter"]').forEach(function(el) {
                    el.style.setProperty('display', 'none', 'important');
                });
                doc.querySelectorAll('a[href*="streamlit.io"], a[href*="streamlit.app/cloud"], .viewerBadge_container__r5tak, .viewerBadge_link__qRIco').forEach(function(el) {
                    el.style.setProperty('display', 'none', 'important');
                });
                doc.querySelectorAll('span, p, div, a').forEach(function(el) {
                    if (el.children.length === 0 && el.innerText && (
                        el.innerText.toLowerCase().includes('streamlit') ||
                        el.innerText.toLowerCase().includes('hosted with')
                    )) {
                        var parent = el.closest('[data-testid]') || el.parentElement;
                        if (parent) parent.style.setProperty('display', 'none', 'important');
                    }
                });
            }
            nuke();
            new MutationObserver(nuke).observe(doc.body, { childList: true, subtree: true });
        }
        killStreamlitBranding();
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

        function blockMapScroll() {
            var root = window.parent.document;
            var canvases = root.querySelectorAll('canvas');
            canvases.forEach(function(el) {
                el.addEventListener('wheel', function(e) {
                    e.stopPropagation();
                    e.preventDefault();
                }, { passive: false });
            });
            new MutationObserver(function() {
                root.querySelectorAll('canvas').forEach(function(el) {
                    if (!el._scrollBlocked) {
                        el._scrollBlocked = true;
                        el.addEventListener('wheel', function(e) {
                            e.stopPropagation();
                            e.preventDefault();
                        }, { passive: false });
                    }
                });
            }).observe(root.body, { childList: true, subtree: true });
        }
        setTimeout(blockMapScroll, 1000);
    })();
    </script>
    """, height=0)

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    # Barre de progression (on motive vers la fin, on ne decourage pas au depart)
    ready, filled_count = is_form_ready()
    total_fields = 8
    remaining    = total_fields - filled_count
    pct          = 100 if ready else int(round(filled_count / total_fields * 100))

    if ready:
        prog_msg, prog_color = "C'est tout bon, lancez l'estimation 🚀", "#22c55e"
    elif remaining == 1:
        prog_msg, prog_color = "Plus qu'une info et votre estimation s'affiche 🙂", "#FF7E79"
    else:
        prog_msg, prog_color = f"Plus que {remaining} infos et votre estimation s'affiche.", "#FF7E79"

    st.markdown(f"""
<div style="margin-bottom:0.9rem;">
  <div class="ico-progress-track">
    <div class="ico-progress-fill" style="width:{pct}%; background:{prog_color};"></div>
  </div>
  <p class="ico-progress-msg" style="color:{prog_color};">{prog_msg}</p>
</div>
""", unsafe_allow_html=True)

    # CTA
    submitted = st.button("✨  Voir l'estimation de mon bien →", disabled=not ready, use_container_width=True)

    # Traitement
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
        prog_slot = st.empty()

        def render_progress(pct: int, txt: str):
            prog_slot.markdown(f"""
<div style="margin: 1.2rem 0 0.5rem;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
        <span style="font-family:'Poppins',sans-serif; font-size:0.88rem; font-weight:600; color:#063970;">{txt}</span>
        <span style="font-family:'Poppins',sans-serif; font-size:0.95rem; font-weight:800; color:#FF7E79;">{pct}%</span>
    </div>
    <div style="background:#f1f5f9; border-radius:999px; height:10px; overflow:hidden;">
        <div style="width:{pct}%; background:#FF7E79; height:10px; border-radius:999px; transition:width 0.4s ease;"></div>
    </div>
    <p style="margin:0.6rem 0 0; font-family:'Poppins',sans-serif; font-size:0.82rem; color:#94a3b8; text-align:center;">⬇️ Votre estimation s'affichera juste en dessous, pas besoin d'ouvrir une nouvelle page.</p>
</div>
""", unsafe_allow_html=True)

        def step(pct, txt, sleep=0.35):
            render_progress(pct, txt); time.sleep(sleep)

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
            render_progress(100, "✅ Votre estimation est prête !")
            time.sleep(0.4)

            st.session_state.geo            = geo
            st.session_state.result_payload = payload

            add_to_kit(
                prenom=st.session_state.prenom,
                email=st.session_state.email,
                area=effective_area,
                bien_type=str(st.session_state.bien_type),
                surface=float(st.session_state.surface),
                est_min=float(payload.get("est_min", 0)),
                est_max=float(payload.get("est_max", 0)),
                pm2=float(payload.get("pm2_med", 0)),
                reliability=str(payload.get("reliability", "")),
                tension_label=str(payload.get("tension", {}).get("label", "")),
                tension_score=int(payload.get("tension", {}).get("score", 0)),
                adresse=str(geo.get("label", ""))
            )

            # Envoi de l'email d'estimation via Brevo SMTP
            send_estimation_email(
                to_email=st.session_state.email,
                prenom=st.session_state.prenom,
                adresse=str(geo.get("label", "")),
                bien_type=str(st.session_state.bien_type),
                surface=float(st.session_state.surface),
                est_min=float(payload.get("est_min", 0)),
                est_max=float(payload.get("est_max", 0)),
                pm2=float(payload.get("pm2_med", 0)),
                fiabilite=str(payload.get("reliability", "")),
                attractivite=f"{payload.get('tension', {}).get('label', '')} ({int(payload.get('tension', {}).get('score', 0))}/100)",
            )

            # Ajout du contact dans Ghost (membres du blog)
            add_to_ghost(
                email=st.session_state.email,
                prenom=st.session_state.prenom,
                note=f"Estimation : {geo.get('label', '')}, {st.session_state.bien_type} {int(float(st.session_state.surface))}m²",
            )
        finally:
            prog_slot.empty()

        st.success(f"Merci {st.session_state.prenom} ✅ Votre estimation est prête.")
        st.rerun()


# ===========================
# RESULTATS
# ===========================
if st.session_state.result_payload and st.session_state.geo:
    # Signale a la page parente d'agrandir l'iframe
    st.components.v1.html("""
    <script>
    try {
        var target = window.parent && window.parent.parent ? window.parent.parent : window.parent;
        target.postMessage({ type: "icostim:resultsReady" }, "*");
    } catch(e) {}
    </script>
    """, height=0)

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

    # Mention discrete si l'estimation s'appuie sur une fenetre elargie (> 12 mois)
    _uw = int(hp.get("used_window", 0) or 0)
    _window_note = ""
    if _uw > 12:
        _window_note = (f"<br/><span style='color:#94a3b8; font-size:0.92rem'>"
                        f"ℹ️ Peu de ventes très récentes sur ce micro-secteur : l'analyse remonte jusqu'à {_uw} mois "
                        f"pour rester fiable.</span>")

    st.markdown(
        f"<div class='result-card'>"
        f"<b>Adresse analysée :</b> {geo.get('label','')}<br/>"
        f"<b>Zone (proxy) :</b> {hp.get('quartier','—')}, <b>Distance gare :</b> {hp.get('distance_gare_m','—')} m<br/>"
        f"<b>Prix médian au m² :</b> ~{eur(hp.get('pm2_med',0))} / m²<br/>"
        f"<b>Biens comparables :</b> {hp.get('n',0)} ventes, rayon max : {hp.get('used_radius','—')} m"
        f"{_window_note}"
        f"</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='tension-box'>{tension_context_message(tscore)}</div>", unsafe_allow_html=True)

    map_points = hp.get("map_points", [])
    if map_points:
        st.markdown(
            f"<h2 style='color:{PRIMARY}; font-family:Poppins,sans-serif; font-weight:800; margin-top:1.5rem; font-size:1.6rem'>🗺️ Localisation des ventes comparables</h2>",
            unsafe_allow_html=True)
        st.caption("Position légèrement floue pour respecter la vie privée des vendeurs.")

        comp_data = [{"lat": float(p["lat"]), "lon": float(p["lon"])} for p in map_points]
        layer_comp = pdk.Layer(
            "ScatterplotLayer",
            data=comp_data,
            get_position=["lon", "lat"],
            get_fill_color=[255, 126, 121, 160],
            get_radius=60,
            pickable=False)

        bien_data = [{"lat": float(geo["lat"]), "lon": float(geo["lon"])}]
        layer_bien = pdk.Layer(
            "ScatterplotLayer",
            data=bien_data,
            get_position=["lon", "lat"],
            get_fill_color=[6, 57, 112, 255],
            get_line_color=[255, 255, 255, 255],
            get_radius=25,
            stroked=True,
            line_width_min_pixels=2,
            pickable=False)

        view = pdk.ViewState(
            latitude=float(geo["lat"]),
            longitude=float(geo["lon"]),
            zoom=14, pitch=0)

        st.pydeck_chart(pdk.Deck(
            layers=[layer_comp, layer_bien],
            initial_view_state=view,
            views=[pdk.View(type="MapView", controller={"scrollZoom": False})],
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            tooltip=False),
            use_container_width=True)

        st.components.v1.html("""
        <script>
        (function() {
            function blockScroll() {
                var parent = window.parent.document;
                parent.querySelectorAll('iframe').forEach(function(iframe) {
                    try {
                        var doc = iframe.contentDocument || iframe.contentWindow.document;
                        doc.querySelectorAll('canvas').forEach(function(canvas) {
                            if (!canvas._wBlocked) {
                                canvas._wBlocked = true;
                                canvas.addEventListener('wheel', function(e) {
                                    e.stopImmediatePropagation();
                                    e.preventDefault();
                                }, { passive: false, capture: true });
                            }
                        });
                    } catch(e) {}
                });
            }
            [500, 1000, 2000, 3500].forEach(function(d) {
                setTimeout(blockScroll, d);
            });
        })();
        </script>
        """, height=0)

        st.markdown(
            "<div style='display:flex; gap:1.5rem; margin-top:0.5rem; font-size:0.85rem; color:#64748b; font-family:Poppins,sans-serif'>"
            "<span><span style='display:inline-block;width:12px;height:12px;border-radius:50%;background:#063970;margin-right:5px;vertical-align:middle'></span>Votre bien</span>"
            "<span><span style='display:inline-block;width:12px;height:12px;border-radius:50%;background:#FF7E79;opacity:0.65;margin-right:5px;vertical-align:middle'></span>Ventes comparables</span>"
            "</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)

    st.markdown(
        "<div class='result-card'>"
        "<p style='font-style:italic; color:#94a3b8; font-size:1.05rem; margin:0 0 1rem 0; font-weight:400;'>Estimer votre maison à distance c'est bien, mais la voir en vrai c'est mieux 😃</p>"
        "<b style='color:#334155; font-size:1.1rem'>Ce que les données ne peuvent pas voir à votre place :</b>"
        "<ul class='disclaimer-list'>"
        "<li>Les nuisances (route, voisinage, bruit, vis-à-vis…)</li>"
        "<li>La luminosité et l'exposition</li>"
        "<li>L'état réel et la qualité des finitions</li>"
        "<li>Les travaux faits ou à prévoir, isolation, DPE</li>"
        "<li>L'agencement, les volumes, l'entretien</li>"
        "<li>Les extérieurs, cave, garage, stationnement, charges de copropriété…</li>"
        "</ul>"
        "<span style='color:#64748b; font-size:1.05rem'>Ça en fait des choses qu'on ne peut pas voir à distance. Cette fourchette est basée sur de vraies ventes, c'est solide, mais pour un chiffre vraiment précis et des conseils adaptés à votre projet, rien ne vaut un vrai échange. Cliquez sur le bouton ci-dessous pour réserver un appel avec moi.</span>"
        "</div>", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='booking-btn'><a href='{BOOKING_URL}' target='_blank'>"
        f"📞 Affiner cette estimation avec Hakim, RDV gratuit, sans engagement"
        f"</a></div>", unsafe_allow_html=True)
    st.caption("Un échange téléphonique de 20 minutes pour un chiffre précis et des conseils pour valoriser votre bien.")

    if tens.get("detail"):
        st.caption(f"📌 {tens['detail']}")

    if hp.get("preview"):
        with st.expander("🧾 Voir les biens comparables (localisation volontairement vague)"):
            for r in hp["preview"]:
                pieces_txt = f" · **{r['nb_pieces']} p.**" if r.get("nb_pieces") else ""
                st.markdown(
                    f"- **{r['type_local']}** · **{r['surface']} m²**{pieces_txt} · **{eur(r['prix'])}** · "
                    f"**{r['mois']}** · **{r['commune']}** (~{r['dist']} m)")

    if DEBUG:
        with st.expander("🧪 Debug payload"):
            st.write(hp); st.write("geo:", geo)


# ===========================
# Hauteur dynamique → Ghost
# L'app mesure sa vraie hauteur (mesure robuste) et l'envoie à TOUS les niveaux parents.
# Seuil de 40px pour éviter les rétrécissements en cascade dus au min-height:0 du CSS.
# ===========================
st.components.v1.html("""
<script>
(function() {
    var streamlitDoc = window.parent.document;
    var last = 0;

    function broadcast(h) {
        var msg = { type: "icostim:height", height: h };
        try { window.parent.postMessage(msg, "*"); } catch(e) {}
        try { window.parent.parent.postMessage(msg, "*"); } catch(e) {}
        try { window.top.postMessage(msg, "*"); } catch(e) {}
    }

    function measureHeight() {
        var body = streamlitDoc.body;
        var html = streamlitDoc.documentElement;
        // Mesure classique
        var h1 = Math.max(
            body.scrollHeight, body.offsetHeight,
            html.scrollHeight, html.offsetHeight
        );
        // Mesure robuste : bas du dernier bloc réel de l'app
        var h2 = 0;
        try {
            var app = streamlitDoc.querySelector('[data-testid="stAppViewContainer"]')
                   || streamlitDoc.querySelector('.main')
                   || body;
            var rect = app.getBoundingClientRect();
            h2 = rect.bottom + (streamlitDoc.defaultView.scrollY || 0);
        } catch(e) {}
        return Math.max(h1, h2);
    }

    function sendHeight() {
        try {
            var h = measureHeight();
            // On n'envoie que si la variation est significative (> 40px),
            // pour éviter les micro-tassements en cascade.
            if (h && Math.abs(h - last) > 40) {
                last = h;
                broadcast(h);
            }
        } catch(e) {}
    }

    sendHeight();
    [100, 400, 800, 1500, 3000].forEach(function(ms) { setTimeout(sendHeight, ms); });

    try {
        var ro = new ResizeObserver(function() { sendHeight(); });
        ro.observe(streamlitDoc.body);
    } catch(e) {}

    try {
        var mo = new MutationObserver(function() { sendHeight(); });
        mo.observe(streamlitDoc.body, { childList: true, subtree: true, attributes: true });
    } catch(e) {}
})();
</script>
""", height=0)
