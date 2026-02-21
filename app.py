import streamlit as st
import numpy as np
import pandas as pd
import requests
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

# ---------------------------
# Config
# ---------------------------
st.set_page_config(page_title="EstimeClermont", page_icon="🏠", layout="wide", initial_sidebar_state="collapsed")

PRIMARY = "#004D7F"
ACCENT = "#FF7E79"

# Coordonnées gare Clermont-de-l'Oise (SNCF Gares & Connexions : POINT (lon lat))
GARE_LON = 2.41767
GARE_LAT = 49.38531

# Géoplateforme (IGN) - endpoints
GEOPF_COMPLETION_URL = "https://data.geopf.fr/geocodage/completion/"
GEOPF_SEARCH_URL = "https://data.geopf.fr/geocodage/search"

# ---------------------------
# UI style (léger)
# ---------------------------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
* {{ font-family: 'Poppins', sans-serif !important; }}
.main {{ background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%); }}

h1 {{ color: {PRIMARY} !important; font-weight: 800 !important; text-align:center; }}
h2 {{ color: {PRIMARY} !important; font-weight: 700 !important; }}
.small-note {{ color:#4b5563; font-size:0.9rem; }}

.card {{
  background: white; border-radius: 14px; padding: 1.1rem;
  box-shadow: 0 6px 18px rgba(0, 77, 127, 0.10);
  border-top: 4px solid {ACCENT};
}}

.metric {{
  background: linear-gradient(135deg, {ACCENT} 0%, #ff5b66 100%);
  color: white; border-radius: 14px; padding: 1.2rem;
  box-shadow: 0 6px 20px rgba(255, 126, 121, 0.30);
}}
.metric .k {{ font-size:0.85rem; opacity:0.95; margin:0; }}
.metric .v {{ font-size:1.6rem; font-weight:800; margin:0.1rem 0 0 0; }}

.stButton > button {{
    background: linear-gradient(135deg, {ACCENT} 0%, #ff5b66 100%) !important;
    color: white !important; font-weight: 900 !important;
    border-radius: 12px !important; border: none !important;
    padding: 1.1rem 1.2rem !important; font-size: 1.15rem !important;
    box-shadow: 0 6px 18px rgba(255, 126, 121, 0.35);
}}
.stButton > button:hover {{ box-shadow: 0 10px 26px rgba(255, 126, 121, 0.45); }}

hr {{ border: none; border-top: 1px solid rgba(0,0,0,0.08); margin: 1.3rem 0; }}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Helpers
# ---------------------------
def haversine_m(lat1, lon1, lat2, lon2) -> float:
    """Distance en mètres entre 2 points."""
    R = 6371000.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dl/2)**2
    return float(2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))

@st.cache_data(ttl=60*60)  # 1h
def geopf_completion(text: str, postcode: str = "60600", max_resp: int = 7) -> List[Dict[str, Any]]:
    """Suggestions d'adresse via Géoplateforme autocomplétion."""
    if not text or len(text.strip()) < 3:
        return []
    params = {
        "text": text.strip(),
        "terr": postcode,                 # limitation géographique par code postal (doc)
        "type": "StreetAddress",
        "maximumResponses": max_resp
    }
    r = requests.get(GEOPF_COMPLETION_URL, params=params, timeout=8)
    r.raise_for_status()
    data = r.json()
    # La structure exacte peut évoluer; on essaie d'être robuste.
    # Beaucoup de réponses exposent un tableau "results" ou "features".
    results = data.get("results") or data.get("features") or []
    out = []
    for it in results:
        props = it.get("properties", it)
        label = props.get("label") or props.get("fulltext") or props.get("name")
        if label:
            out.append({"label": label})
    # fallback si déjà sous forme [{"label":...}]
    if results and isinstance(results[0], dict) and results[0].get("label"):
        out = results
    # dédoublonnage
    seen = set()
    dedup = []
    for x in out:
        if x["label"] not in seen:
            dedup.append(x)
            seen.add(x["label"])
    return dedup

@st.cache_data(ttl=24*60*60)  # 24h
def geopf_geocode_one(query: str) -> Optional[Dict[str, Any]]:
    """Géocode une adresse en (lat, lon)."""
    if not query:
        return None
    # Les paramètres exacts sont détaillés dans le swagger Géoplateforme;
    # on tente le plus standard: q + limit.
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
    coords = geom.get("coordinates")  # souvent [lon, lat]
    if not coords or len(coords) < 2:
        return None
    lon, lat = float(coords[0]), float(coords[1])
    return {"lat": lat, "lon": lon, "label": props.get("label") or query}

def quartier_from_distance(distance_m: float) -> str:
    # TEMPORAIRE (jusqu'à tes polygones GeoJSON)
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
    # TEMPORAIRE : à remplacer par agrégats DVF (médiane m² 12 mois) + calibration
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
    # Bonus proximité gare plafonné
    facteur_gare = 1 + min(0.08, 0.5 / (1 + distance_m / 1000))

    prix_total = prix_m2 * surface * facteur_pieces * facteur_chambres * facteur_etat * facteur_gare
    fourchette = (prix_total * 0.93, prix_total * 1.07)

    return {
        "quartier": quartier,
        "distance_gare_m": int(round(distance_m)),
        "prix_m2": prix_m2 * facteur_pieces * facteur_chambres * facteur_etat * facteur_gare,
        "prix_total": prix_total,
        "min": fourchette[0],
        "max": fourchette[1],
        "explain": {
            "base_m2": prix_m2,
            "facteur_etat": facteur_etat,
            "facteur_gare": facteur_gare,
            "facteur_pieces": facteur_pieces,
            "facteur_chambres": facteur_chambres,
        }
    }

def eur(x: float) -> str:
    return f"{x:,.0f} €".replace(",", " ")

# ---------------------------
# Header + promesse (alignée sur ce que tu fais VRAIMENT)
# ---------------------------
st.markdown("<h1>🏠 Estimation locale à Clermont (60600)</h1>", unsafe_allow_html=True)
st.markdown(
    "<div class='card'><b>Objectif :</b> vous donner une <b>fourchette crédible</b> en 30 secondes, "
    "puis affiner avec des ventes comparables et les spécificités de votre bien.</div>",
    unsafe_allow_html=True
)

st.markdown("<hr/>", unsafe_allow_html=True)

# ---------------------------
# Step 1 - Description + Adresse (avec autocomplétion)
# ---------------------------
colL, colR = st.columns([1.2, 1], gap="large")

with colL:
    st.markdown("## 📋 Décrivez votre bien")

    c1, c2 = st.columns(2)
    with c1:
        bien_type = st.selectbox("Type de bien", ["Maison", "Appartement"])
        surface = st.number_input("Surface (m²)", min_value=10, max_value=500, value=100)
        etat = st.selectbox("État du bien", ["À rénover", "Moyen", "Bon", "Rénové"], index=1)
    with c2:
        nb_pieces = st.number_input("Nombre de pièces", min_value=1, max_value=12, value=3)
        nb_chambres = st.number_input("Nombre de chambres", min_value=0, max_value=10, value=2)
        code_postal = st.text_input("Code postal", value="60600")

    st.markdown("### 📍 Adresse")
    addr_typed = st.text_input("Commencez à taper l’adresse", placeholder="Ex : 3 rue Émile Bousseau")
    suggestions = []
    try:
        suggestions = geopf_completion(addr_typed, postcode=code_postal)
    except Exception:
        suggestions = []

    if suggestions:
        labels = [s["label"] for s in suggestions]
        addr_choice = st.selectbox("Suggestions", labels)
    else:
        addr_choice = addr_typed.strip()

    st.markdown("<p class='small-note'>Astuce : choisissez une suggestion pour améliorer la précision (et calculer la distance à la gare automatiquement).</p>", unsafe_allow_html=True)

    run = st.button("🚀 Obtenir ma fourchette (sans engagement)", use_container_width=True)

with colR:
    st.markdown("## 💎 Ce que vous obtenez")
    st.markdown(
        "<div class='card'>"
        "✅ Distance à la gare calculée automatiquement<br/>"
        "✅ Quartier estimé (version simple, bientôt polygones réels)<br/>"
        "✅ Fourchette immédiate<br/>"
        "✅ Détails & comparables contre vos coordonnées (soft gate)"
        "</div>",
        unsafe_allow_html=True
    )
    st.markdown("<div class='card'><b>Note :</b> l’estimation est indicative. L’affinage final se fait après vérification des éléments (état réel, travaux, terrain, nuisances, etc.).</div>", unsafe_allow_html=True)

# ---------------------------
# Step 2 - Résultat + soft-gate contact
# ---------------------------
if run:
    if not addr_choice or len(addr_choice) < 6:
        st.error("Ajoute une adresse plus complète (ou choisis une suggestion).")
        st.stop()

    try:
        geo = geopf_geocode_one(addr_choice)
    except Exception:
        geo = None

    if not geo:
        st.error("Impossible de géocoder l’adresse pour le moment. Essaie une suggestion différente (ou ajoute le numéro + rue).")
        st.stop()

    distance_m = haversine_m(geo["lat"], geo["lon"], GARE_LAT, GARE_LON)
    res = estimate_price(bien_type, float(surface), int(nb_pieces), int(nb_chambres), etat, distance_m)

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown("## ✨ Votre estimation (fourchette immédiate)")

    m1, m2, m3 = st.columns(3, gap="medium")
    with m1:
        st.markdown(f"<div class='metric'><p class='k'>Fourchette</p><p class='v'>{eur(res['min'])} – {eur(res['max'])}</p></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric'><p class='k'>Quartier (approx.)</p><p class='v'>{res['quartier']}</p></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='metric'><p class='k'>Distance gare</p><p class='v'>{res['distance_gare_m']} m</p></div>", unsafe_allow_html=True)

    st.markdown(
        f"<div class='card'><b>Adresse géocodée :</b> {geo.get('label','')}<br/>"
        f"<b>Prix/m² indicatif (après facteurs) :</b> {eur(res['prix_m2'])} / m²</div>",
        unsafe_allow_html=True
    )

    # Soft gate : détails contre contact
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown("## 📩 Recevoir le détail (comparables + explication)")

    c1, c2 = st.columns(2)
    with c1:
        prenom = st.text_input("Votre prénom")
        email = st.text_input("Votre email")
    with c2:
        telephone = st.text_input("Votre téléphone")
        consent = st.checkbox("J’accepte d’être recontacté au sujet de cette estimation (sans spam).")

    if st.button("✅ Envoyer le détail + être rappelé", use_container_width=True):
        # Validation simple (tu peux durcir ensuite)
        if not (prenom and email and telephone and consent):
            st.error("Il manque une info (ou le consentement).")
            st.stop()

        # Ici tu enregistres en base / Airtable / Notion / Sheets / webhook CRM.
        # Exemple: st.session_state["lead"] = {...}
        st.session_state["lead"] = {
            "prenom": prenom,
            "email": email,
            "telephone": telephone,
            "adresse": geo.get("label", addr_choice),
            "lat": geo["lat"], "lon": geo["lon"],
            "bien_type": bien_type,
            "surface": float(surface),
            "pieces": int(nb_pieces),
            "chambres": int(nb_chambres),
            "etat": etat,
            "distance_gare_m": res["distance_gare_m"],
            "quartier": res["quartier"],
            "estimation_min": float(res["min"]),
            "estimation_max": float(res["max"]),
        }

        # Détails transparents (tu peux choisir de ne pas tout montrer)
        with st.expander("Voir l’explication (transparence)"):
            st.json(res["explain"])

        st.success(f"Merci {prenom} ✅ Je te contacte rapidement pour affiner et te donner des comparables précis.")
