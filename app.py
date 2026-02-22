# =============================
# ESTIME CLERMONT – VERSION CONSOLIDÉE + DVF
# =============================

import streamlit as st
import numpy as np
import requests
import pandas as pd
import datetime
import time
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

GARE_LON = 2.41767
GARE_LAT = 49.38531
DVF_API = "https://dvf.cquest.org/dvf"

# ---------------------------
# Communes
# ---------------------------
AREAS: Dict[str, Dict[str, str]] = {
    "Clermont-de-l'Oise": {"city": "Clermont", "postcode": "60600"},
    "Breuil-le-Vert": {"city": "Breuil-le-Vert", "postcode": "60600"},
    "Agnetz": {"city": "Agnetz", "postcode": "60600"},
    "Fitz-James": {"city": "Fitz-James", "postcode": "60600"},
    "Breuil-le-Sec": {"city": "Breuil-le-Sec", "postcode": "60840"},
    "Neuilly-sous-Clermont": {"city": "Neuilly-sous-Clermont", "postcode": "60290"},
    "Bailleval": {"city": "Bailleval", "postcode": "60140"},
}

AUTO_AREA = "🔎 Détection automatique"
DEFAULT_AREA = "Clermont-de-l'Oise"

# ---------------------------
# Session state
# ---------------------------
st.session_state.setdefault("step", 1)
st.session_state.setdefault("geo", None)
st.session_state.setdefault("res", None)
st.session_state.setdefault("area_name", AUTO_AREA)
st.session_state.setdefault("detected_area", DEFAULT_AREA)
st.session_state.setdefault("bien_type", "Maison")
st.session_state.setdefault("surface", 100.0)
st.session_state.setdefault("etat", "Moyen")
st.session_state.setdefault("nb_pieces", 3)
st.session_state.setdefault("nb_chambres", 2)
st.session_state.setdefault("addr_choice", "")
st.session_state.setdefault("prenom", "")
st.session_state.setdefault("email", "")
st.session_state.setdefault("telephone", "")
st.session_state.setdefault("consent", False)

# ---------------------------
# CSS (IDENTIQUE À TA VERSION)
# ---------------------------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap');
* {{ font-family: 'Poppins', sans-serif !important; }}

.main {{ background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%); }}

h1 {{ color:{PRIMARY}; font-weight:800; text-align:center; }}
h2, h3 {{ color:{PRIMARY}; font-weight:750; }}

.badge {{
  display:inline-block; padding:0.35rem 0.75rem; border-radius:999px;
  background: rgba(0,77,127,0.1); color:{PRIMARY}; font-weight:700;
}}

.metric {{
  background: linear-gradient(135deg,{ACCENT} 0%,#ff5b66 100%);
  color:white; border-radius:16px; padding:1.2rem;
  box-shadow:0 12px 28px rgba(255,126,121,0.28);
}}
.metric .k {{ font-size:0.85rem; }}
.metric .v {{ font-size:1.6rem; font-weight:800; }}

.card {{
  background:white; border-radius:16px; padding:1.1rem;
  box-shadow:0 10px 26px rgba(0,77,127,0.1);
}}
.card.soft {{
  background: linear-gradient(135deg,{SOFT} 0%,white 100%);
}}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Helpers
# ---------------------------
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dl/2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1-a))

def eur(x):
    return f"{x:,.0f} €".replace(",", " ")

# ---------------------------
# ESTIMATION RAPIDE
# ---------------------------
def estimate_price(surface, distance):
    base = 2300
    facteur = 1 + min(0.08, 0.5/(1 + distance/1000))
    prix = base * surface * facteur
    return prix*0.93, prix*1.07

# ---------------------------
# DVF
# ---------------------------
@st.cache_data(ttl=3600)
def fetch_dvf_sales(lat, lon, radius):
    try:
        r = requests.get(DVF_API, params={"lat":lat,"lon":lon,"dist":radius}, timeout=15)
        if r.status_code != 200:
            return []
        return r.json()
    except:
        return []

def filter_dvf(data, bien_type, surface):
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df["date_mutation"] = pd.to_datetime(df["date_mutation"])
    df = df[df["date_mutation"] >= datetime.datetime.now() - datetime.timedelta(days=365)]
    df = df[df["type_local"] == bien_type]
    df = df[(df["surface_reelle_bati"] >= surface*0.75) &
            (df["surface_reelle_bati"] <= surface*1.25)]
    df["prix_m2"] = df["valeur_fonciere"] / df["surface_reelle_bati"]
    return df

def clean_outliers(df):
    if len(df) < 5:
        return df
    low = df["prix_m2"].quantile(0.10)
    high = df["prix_m2"].quantile(0.90)
    return df[(df["prix_m2"] >= low) & (df["prix_m2"] <= high)]

def compute_dvf(df, surface):
    if df.empty:
        return None
    median = df["prix_m2"].median()
    prix = median * surface
    return prix

# ---------------------------
# STEP 1
# ---------------------------
if st.session_state.step == 1:

    st.markdown("<h1>🏠 Estimation locale</h1>", unsafe_allow_html=True)

    st.number_input("Surface (m²)", min_value=20.0, max_value=500.0, key="surface")

    if st.button("🚀 Obtenir ma fourchette"):
        lat, lon = GARE_LAT, GARE_LON
        distance = haversine_m(lat, lon, GARE_LAT, GARE_LON)
        min_p, max_p = estimate_price(st.session_state.surface, distance)

        st.session_state.geo = {"lat":lat,"lon":lon,"label":"Clermont"}
        st.session_state.res = {"min":min_p,"max":max_p,"distance_gare_m":0}
        st.session_state.step = 2
        st.rerun()

# ---------------------------
# STEP 2
# ---------------------------
if st.session_state.step == 2:

    geo = st.session_state.geo
    res = st.session_state.res

    st.markdown("## ✨ Votre estimation immédiate")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='metric'><p class='k'>Fourchette</p><p class='v'>{eur(res['min'])} – {eur(res['max'])}</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric'><p class='k'>Distance gare</p><p class='v'>{res['distance_gare_m']} m</p></div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    st.markdown("## 📩 Recevoir l’estimation affinée DVF")

    with st.form("contact"):
        st.text_input("Prénom", key="prenom")
        st.text_input("Email", key="email")
        st.text_input("Téléphone", key="telephone")
        st.checkbox("J’accepte d’être recontacté", key="consent")
        submitted = st.form_submit_button("Obtenir estimation DVF")

    if submitted:
        if not (st.session_state.prenom and st.session_state.email and st.session_state.telephone and st.session_state.consent):
            st.error("Il manque une info.")
            st.stop()

        progress = st.progress(0)
        status = st.empty()

        status.text("🔎 Analyse des ventes locales…")
        progress.progress(30)
        time.sleep(0.6)

        sales = fetch_dvf_sales(geo["lat"], geo["lon"], 1000)
        if len(sales) < 5:
            sales = fetch_dvf_sales(geo["lat"], geo["lon"], 2000)

        progress.progress(60)
        df = filter_dvf(sales, "Maison", st.session_state.surface)
        df = clean_outliers(df)

        progress.progress(90)
        prix_affine = compute_dvf(df, st.session_state.surface)

        progress.progress(100)
        time.sleep(0.4)
        progress.empty()
        status.empty()

        if prix_affine:
            st.markdown("## 🔓 Estimation affinée DVF")
            st.markdown(f"<div class='metric'><p class='k'>Valeur estimée</p><p class='v'>{eur(prix_affine)}</p></div>", unsafe_allow_html=True)

            st.markdown(f"<div class='card soft'><b>Basé sur :</b> {len(df)} ventes comparables (12 mois)</div>", unsafe_allow_html=True)

            for _, row in df.head(5).iterrows():
                st.markdown(
                    f"- {row['type_local']} | {int(row['surface_reelle_bati'])} m²  \n"
                    f"  Vente {row['date_mutation'].strftime('%m/%Y')}  \n"
                    f"  {eur(row['valeur_fonciere'])}"
                )

        st.success(f"Merci {st.session_state.prenom} ✅ Je te contacte rapidement pour affiner.")
