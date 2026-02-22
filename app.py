import streamlit as st
import numpy as np
import pandas as pd
import requests
import datetime
import time

st.set_page_config(page_title="EstimeClermont", page_icon="🏠", layout="wide")

PRIMARY = "#004D7F"
ACCENT = "#FF7E79"

GARE_LON = 2.41767
GARE_LAT = 49.38531

DVF_API = "https://dvf.cquest.org/dvf"

# -------------------------------------------------
# CSS
# -------------------------------------------------
st.markdown(f"""
<style>
body {{ font-family: 'Poppins', sans-serif; }}
h1, h2, h3 {{ color: {PRIMARY}; font-weight: 700; }}
.metric-card {{
    background: linear-gradient(135deg, {ACCENT} 0%, #ff5b66 100%);
    color: white;
    padding: 1rem;
    border-radius: 14px;
}}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dl/2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1-a))

def estimate_simple(surface, distance):
    base = 2300
    facteur = 1 + min(0.08, 0.5/(1 + distance/1000))
    prix = base * surface * facteur
    return prix * 0.93, prix * 1.07

# -------------------------------------------------
# DVF FUNCTIONS
# -------------------------------------------------
def fetch_dvf_sales(lat, lon, radius):
    params = {"lat": lat, "lon": lon, "dist": radius}
    r = requests.get(DVF_API, params=params, timeout=15)
    if r.status_code != 200:
        return []
    return r.json()

def filter_comparables(data, bien_type, surface):
    df = pd.DataFrame(data)
    if df.empty:
        return df

    df["date_mutation"] = pd.to_datetime(df["date_mutation"])
    one_year = datetime.datetime.now() - datetime.timedelta(days=365)
    df = df[df["date_mutation"] >= one_year]

    type_map = "Maison" if bien_type == "Maison" else "Appartement"
    df = df[df["type_local"] == type_map]

    df = df[(df["surface_reelle_bati"] >= surface * 0.75) &
            (df["surface_reelle_bati"] <= surface * 1.25)]

    df["prix_m2"] = df["valeur_fonciere"] / df["surface_reelle_bati"]
    return df

def clean_outliers(df):
    if len(df) < 5:
        return df
    low = df["prix_m2"].quantile(0.10)
    high = df["prix_m2"].quantile(0.90)
    return df[(df["prix_m2"] >= low) & (df["prix_m2"] <= high)]

def compute_dvf_estimation(df, surface):
    if df.empty:
        return None
    median = df["prix_m2"].median()
    prix = median * surface

    n = len(df)
    if n > 10:
        marge = 0.05
    elif n >= 5:
        marge = 0.07
    else:
        marge = 0.10

    return {
        "count": n,
        "median_m2": median,
        "estimation": prix,
        "min": prix*(1-marge),
        "max": prix*(1+marge)
    }

# -------------------------------------------------
# STATE
# -------------------------------------------------
if "step" not in st.session_state:
    st.session_state.step = 1

# -------------------------------------------------
# STEP 1
# -------------------------------------------------
if st.session_state.step == 1:

    st.title("🏠 Estimation Immobilière Locale")

    surface = st.number_input("Surface (m²)", min_value=20, max_value=400, value=100)
    bien_type = st.selectbox("Type", ["Maison", "Appartement"])

    lat = 49.38531
    lon = 2.41767

    distance = haversine_m(lat, lon, GARE_LAT, GARE_LON)

    if st.button("🚀 Obtenir ma fourchette"):
        min_price, max_price = estimate_simple(surface, distance)

        st.session_state.simple_min = min_price
        st.session_state.simple_max = max_price
        st.session_state.surface = surface
        st.session_state.bien_type = bien_type
        st.session_state.lat = lat
        st.session_state.lon = lon
        st.session_state.step = 2
        st.rerun()

# -------------------------------------------------
# STEP 2
# -------------------------------------------------
if st.session_state.step == 2:

    st.header("✨ Première estimation")

    col1, col2 = st.columns(2)
    col1.metric("Fourchette", f"{st.session_state.simple_min:,.0f} € - {st.session_state.simple_max:,.0f} €".replace(",", " "))
    col2.metric("Méthode", "Algorithme local")

    st.divider()

    st.subheader("🔓 Débloquer l’estimation DVF (12 mois glissants)")

    with st.form("contact"):
        email = st.text_input("Votre email")
        consent = st.checkbox("J’accepte d’être recontacté")
        submit = st.form_submit_button("Obtenir l’estimation affinée")

    if submit and consent and email:

        progress = st.progress(0)
        status = st.empty()

        status.text("🔎 Analyse des ventes locales…")
        progress.progress(20)
        time.sleep(0.6)

        sales = fetch_dvf_sales(st.session_state.lat, st.session_state.lon, 1000)

        if len(sales) < 5:
            status.text("📍 Extension du rayon de recherche…")
            progress.progress(35)
            sales = fetch_dvf_sales(st.session_state.lat, st.session_state.lon, 2000)

        status.text("🧹 Filtrage des biens similaires…")
        progress.progress(55)
        df = filter_comparables(sales, st.session_state.bien_type, st.session_state.surface)

        status.text("📊 Nettoyage statistique…")
        progress.progress(75)
        df = clean_outliers(df)

        status.text("🧠 Calcul de l’estimation affinée…")
        progress.progress(95)
        result = compute_dvf_estimation(df, st.session_state.surface)

        progress.progress(100)
        time.sleep(0.5)
        progress.empty()
        status.empty()

        if result:
            st.success(f"Basé sur {result['count']} ventes comparables")

            col1, col2 = st.columns(2)
            col1.metric("Valeur affinée", f"{result['estimation']:,.0f} €".replace(",", " "))
            col2.metric("Fourchette réaliste", 
                        f"{result['min']:,.0f} € - {result['max']:,.0f} €".replace(",", " "))

            st.subheader("🏘️ Exemples de biens comparables (localisation partielle)")
            for _, row in df.head(5).iterrows():
                st.markdown(
                    f"- {row['type_local']} | {int(row['surface_reelle_bati'])} m²  \n"
                    f"  Vente {row['date_mutation'].strftime('%m/%Y')}  \n"
                    f"  ~{int(row.get('distance',0))} m  \n"
                    f"  {int(row['valeur_fonciere']):,} €".replace(",", " ")
                )
        else:
            st.warning("Pas assez de ventes comparables récentes.")
