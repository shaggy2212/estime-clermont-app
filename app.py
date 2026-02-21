import streamlit as st
import numpy as np
import requests
from typing import Optional, Dict, Any, List

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

# Coordonnées gare Clermont-de-l'Oise (SNCF Gares & Connexions : POINT (lon lat))
GARE_LON = 2.41767
GARE_LAT = 49.38531

# Géoplateforme (IGN) - endpoints
GEOPF_COMPLETION_URL = "https://data.geopf.fr/geocodage/completion/"
GEOPF_SEARCH_URL = "https://data.geopf.fr/geocodage/search"

# ---------------------------
# Session state (fix navigation step)
# ---------------------------
if "step" not in st.session_state:
    st.session_state.step = 1
if "geo" not in st.session_state:
    st.session_state.geo = None
if "res" not in st.session_state:
    st.session_state.res = None

# Optional: persist step-1 inputs so returning doesn't reset everything
defaults = {
    "bien_type": "Maison",
    "surface": 100.0,
    "etat": "Moyen",
    "nb_pieces": 3,
    "nb_chambres": 2,
    "code_postal": "60600",
    "addr_typed": "",
    "addr_choice": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------
# UI style (léger)
# ---------------------------
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
* {{ font-family: 'Poppins', sans-serif !important; }}
.main {{ background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%); }}

h1 {{ color: {PRIMARY} !important; font-weight: 800 !important; text-align:center; margin-bottom: 0.2rem; }}
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
""",
    unsafe_allow_html=True,
)

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
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dl / 2) ** 2
    return float(2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))


@st.cache_data(ttl=60 * 60)  # 1h
def geopf_completion(text: str, postcode: str = "60600", max_resp: int = 7) -> List[Dict[str, Any]]:
    """Suggestions d'adresse via Géoplateforme autocomplétion."""
    if not text or len(text.strip()) < 3:
        return []
    params = {
        "text": text.strip(),
        "terr": postcode,
        "type": "StreetAddress",
        "maximumResponses": max_resp,
    }
    r = requests.get(GEOPF_COMPLETION_URL, params=params, timeout=8)
    r.raise_for_status()
    data = r.json()

    results = data.get("results") or data.get("features") or []
    out: List[Dict[str, Any]] = []

    for it in results:
        props = it.get("properties", it) if isinstance(it, dict) else {}
        label = props.get("label") or props.get("fulltext") or props.get("name")
        if label:
            out.append({"label": label})

    # If API already returns label-based list
    if results and isinstance(results, list) and isinstance(results[0], dict) and results[0].get("label"):
        out = results  # type: ignore[assignment]

    # Deduplicate
    seen = set()
    dedup = []
    for x in out:
        lab = x.get("label")
        if lab and lab not in seen:
            dedup.append({"label": lab})
            seen.add(lab)
    return dedup


@st.cache_data(ttl=24 * 60 * 60)  # 24h
def geopf_geocode_one(query: str) -> Optional[Dict[str, Any]]:
    """Géocode une adresse en (lat, lon)."""
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
    # TEMPORAIRE : à remplacer par DVF (médiane m² 12 mois) + calibration
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
    distance_m: float,
) -> Dict[str, Any]:
    quartier = quartier_from_distance(distance_m)
    prix_m2 = base_prix_m2(quartier, bien_type)

    facteur_pieces = 1 + (nb_pieces - 3) * 0.03
    facteur_chambres = 1 + (nb_chambres - 2) * 0.05
    facteur_etat = {"À rénover": 0.85, "Moyen": 1.0, "Bon": 1.06, "Rénové": 1.12}[etat]
    facteur_gare = 1 + min(0.08, 0.5 / (1 + distance_m / 1000))  # bonus plafonné

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
        },
    }


def eur(x: float) -> str:
    return f"{x:,.0f} €".replace(",", " ")


# ---------------------------
# Header
# ---------------------------
st.markdown("<h1>🏠 Estimation locale à Clermont (60600)</h1>", unsafe_allow_html=True)
st.markdown(
    "<div class='card'><b>Objectif :</b> vous donner une <b>fourchette crédible</b> en 30 secondes, "
    "puis affiner avec des ventes comparables et les spécificités de votre bien.</div>",
    unsafe_allow_html=True,
)
st.markdown("<hr/>", unsafe_allow_html=True)

# ---------------------------
# Step 1 - Description + Adresse
# ---------------------------
if st.session_state.step == 1:
    colL, colR = st.columns([1.2, 1], gap="large")

    with colL:
        st.markdown("## 📋 Décrivez votre bien")

        c1, c2 = st.columns(2)
        with c1:
            st.session_state.bien_type = st.selectbox(
                "Type de bien",
                ["Maison", "Appartement"],
                index=0 if st.session_state.bien_type == "Maison" else 1,
                key="bien_type_select",
            )
            st.session_state.surface = st.number_input(
                "Surface (m²)",
                min_value=10,
                max_value=500,
                value=float(st.session_state.surface),
                key="surface_input",
            )
            st.session_state.etat = st.selectbox(
                "État du bien",
                ["À rénover", "Moyen", "Bon", "Rénové"],
                index=["À rénover", "Moyen", "Bon", "Rénové"].index(st.session_state.etat),
                key="etat_select",
            )
        with c2:
            st.session_state.nb_pieces = st.number_input(
                "Nombre de pièces",
                min_value=1,
                max_value=12,
                value=int(st.session_state.nb_pieces),
                key="pieces_input",
            )
            st.session_state.nb_chambres = st.number_input(
                "Nombre de chambres",
                min_value=0,
                max_value=10,
                value=int(st.session_state.nb_chambres),
                key="chambres_input",
            )
            st.session_state.code_postal = st.text_input("Code postal", value=st.session_state.code_postal, key="cp_input")

        st.markdown("### 📍 Adresse")
        st.session_state.addr_typed = st.text_input(
            "Commencez à taper l’adresse",
            placeholder="Ex : 3 rue Émile Bousseau",
            value=st.session_state.addr_typed,
            key="addr_typed_input",
        )

        suggestions: List[Dict[str, Any]] = []
        try:
            suggestions = geopf_completion(st.session_state.addr_typed, postcode=st.session_state.code_postal)
        except Exception:
            suggestions = []

        if suggestions:
            labels = [s["label"] for s in suggestions]
            # default to previous choice if still available
            default_index = 0
            if st.session_state.addr_choice in labels:
                default_index = labels.index(st.session_state.addr_choice)

            st.session_state.addr_choice = st.selectbox("Suggestions", labels, index=default_index, key="addr_suggest_select")
        else:
            st.session_state.addr_choice = st.session_state.addr_typed.strip()

        st.markdown(
            "<p class='small-note'>Astuce : choisissez une suggestion pour améliorer la précision "
            "(et calculer la distance à la gare automatiquement).</p>",
            unsafe_allow_html=True,
        )

        go_step2 = st.button("🚀 Obtenir ma fourchette (sans engagement)", use_container_width=True)

        if go_step2:
            addr_choice = (st.session_state.addr_choice or "").strip()
            if not addr_choice or len(addr_choice) < 6:
                st.error("Ajoute une adresse plus complète (ou choisis une suggestion).")
                st.stop()

            try:
                geo = geopf_geocode_one(addr_choice)
            except Exception:
                geo = None

            if not geo:
                st.error(
                    "Impossible de géocoder l’adresse. Essaie une suggestion différente (ou ajoute le numéro + rue)."
                )
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
            st.rerun()

    with colR:
        st.markdown("## 💎 Ce que vous obtenez")
        st.markdown(
            "<div class='card'>"
            "✅ Distance à la gare calculée automatiquement<br/>"
            "✅ Quartier estimé (version simple, bientôt polygones réels)<br/>"
            "✅ Fourchette immédiate<br/>"
            "✅ Détails & comparables contre vos coordonnées"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='card'><b>Note :</b> l’estimation est indicative. L’affinage final se fait après vérification "
            "(état réel, travaux, terrain, nuisances, etc.).</div>",
            unsafe_allow_html=True,
        )

# ---------------------------
# Step 2 - Résultat + soft-gate contact (stable)
# ---------------------------
if st.session_state.step == 2 and st.session_state.geo and st.session_state.res:
    geo = st.session_state.geo
    res = st.session_state.res

    st.markdown("## ✨ Votre estimation (fourchette immédiate)")

    m1, m2, m3 = st.columns(3, gap="medium")
    with m1:
        st.markdown(
            f"<div class='metric'><p class='k'>Fourchette</p><p class='v'>{eur(res['min'])} – {eur(res['max'])}</p></div>",
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f"<div class='metric'><p class='k'>Quartier (approx.)</p><p class='v'>{res['quartier']}</p></div>",
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f"<div class='metric'><p class='k'>Distance gare</p><p class='v'>{res['distance_gare_m']} m</p></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div class='card'><b>Adresse géocodée :</b> {geo.get('label','')}<br/>"
        f"<b>Prix/m² indicatif (après facteurs) :</b> {eur(res['prix_m2'])} / m²</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<hr/>", unsafe_allow_html=True)

    top_left, top_right = st.columns([1, 1], gap="medium")
    with top_left:
        if st.button("⬅️ Modifier les infos du bien", use_container_width=True):
            st.session_state.step = 1
            st.rerun()

    with top_right:
        with st.expander("Voir l’explication (transparence)"):
            st.json(res["explain"])

    st.markdown("## 📩 Recevoir le détail (comparables + explication)")

    # Contact form to prevent step bouncing on checkbox rerun
    with st.form("contact_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            prenom = st.text_input("Votre prénom", key="prenom")
            email = st.text_input("Votre email", key="email")
        with c2:
            telephone = st.text_input("Votre téléphone", key="telephone")
            consent = st.checkbox(
                "J’accepte d’être recontacté au sujet de cette estimation (sans spam).",
                key="consent",
            )

        submitted = st.form_submit_button("✅ Envoyer le détail + être rappelé", use_container_width=True)

    if submitted:
        if not (st.session_state.get("prenom") and st.session_state.get("email") and st.session_state.get("telephone") and st.session_state.get("consent")):
            st.error("Il manque une info (ou le consentement).")
        else:
            # Ici tu enregistres en base / Airtable / Notion / Sheets / webhook CRM
            st.session_state["lead"] = {
                "prenom": st.session_state["prenom"],
                "email": st.session_state["email"],
                "telephone": st.session_state["telephone"],
                "adresse": geo.get("label", st.session_state.addr_choice),
                "lat": geo["lat"],
                "lon": geo["lon"],
                "bien_type": st.session_state.bien_type,
                "surface": float(st.session_state.surface),
                "pieces": int(st.session_state.nb_pieces),
                "chambres": int(st.session_state.nb_chambres),
                "etat": st.session_state.etat,
                "distance_gare_m": res["distance_gare_m"],
                "quartier": res["quartier"],
                "estimation_min": float(res["min"]),
                "estimation_max": float(res["max"]),
            }

            st.success(f"Merci {st.session_state['prenom']} ✅ Je te contacte rapidement pour affiner et te donner des comparables précis.")
