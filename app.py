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
SOFT = "#EAF2FF"  # light blue background accents

# Gare Clermont-de-l'Oise (POINT lon lat)
GARE_LON = 2.41767
GARE_LAT = 49.38531

# Scope local
LOCAL_CITY = "Clermont"
LOCAL_POSTCODE = "60600"
LOCAL_LABEL = "Clermont-de-l'Oise (60600)"

# Géoplateforme (IGN)
GEOPF_COMPLETION_URL = "https://data.geopf.fr/geocodage/completion/"
GEOPF_SEARCH_URL = "https://data.geopf.fr/geocodage/search"

# ---------------------------
# Session state
# ---------------------------
st.session_state.setdefault("step", 1)
st.session_state.setdefault("geo", None)
st.session_state.setdefault("res", None)

# Step 1 inputs (keys == widget keys)
st.session_state.setdefault("bien_type", "Maison")
st.session_state.setdefault("surface", 100.0)  # float
st.session_state.setdefault("etat", "Moyen")
st.session_state.setdefault("nb_pieces", 3)     # int
st.session_state.setdefault("nb_chambres", 2)   # int
st.session_state.setdefault("addr_typed", "")
st.session_state.setdefault("addr_choice", "")

# Contact
st.session_state.setdefault("prenom", "")
st.session_state.setdefault("email", "")
st.session_state.setdefault("telephone", "")
st.session_state.setdefault("consent", False)

# Toggle explication
st.session_state.setdefault("show_explain", False)

# ---------------------------
# CSS (premium + secondary back button + form submit style)
# ---------------------------
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
* {{ font-family: 'Poppins', sans-serif !important; }}

.main {{
    background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
}}

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

.card.accent-top {{
  border-top: 4px solid {ACCENT};
}}

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
.metric .v {{ font-size:1.65rem; font-weight:850; margin:0.12rem 0 0 0; letter-spacing:-0.02em; }}

hr {{ border: none; border-top: 1px solid rgba(0,0,0,0.08); margin: 1.3rem 0; }}

/* ✅ Primary buttons (cta + submit) */
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

/* ✅ Secondary button style (Back) via wrapper class */
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

/* Improve widget spacing slightly */
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stForm"]) {{
  margin-top: 0.3rem;
}}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------
# Helpers
# ---------------------------
def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dl / 2) ** 2
    return float(2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))


def normalize_query_to_clermont(q: str) -> str:
    q = (q or "").strip()
    if not q:
        return q
    if LOCAL_POSTCODE not in q and LOCAL_CITY.lower() not in q.lower():
        q = f"{q}, {LOCAL_POSTCODE} {LOCAL_CITY}, Oise, France"
    return q


@st.cache_data(ttl=60 * 60)
def geopf_completion(text: str, postcode: str = LOCAL_POSTCODE, city: str = LOCAL_CITY, max_resp: int = 7) -> List[Dict[str, Any]]:
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
    out: List[Dict[str, Any]] = []

    for it in results:
        props = it.get("properties", it) if isinstance(it, dict) else {}
        label = props.get("label") or props.get("fulltext") or props.get("name")
        if not label:
            continue
        if postcode and postcode not in label:
            continue
        if city and city.lower() not in label.lower():
            continue
        out.append({"label": label})

    seen = set()
    dedup = []
    for x in out:
        if x["label"] not in seen:
            dedup.append(x)
            seen.add(x["label"])
    return dedup


@st.cache_data(ttl=24 * 60 * 60)
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


def estimate_price(bien_type: str, surface: float, nb_pieces: int, nb_chambres: int, etat: str, distance_m: float) -> Dict[str, Any]:
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


def eur(x: float) -> str:
    return f"{x:,.0f} €".replace(",", " ")


# ---------------------------
# Header
# ---------------------------
st.markdown("<h1>🏠 Estimation locale</h1>", unsafe_allow_html=True)
st.markdown(
    f"<div style='text-align:center; margin-bottom:0.6rem;'><span class='badge'>Zone : {LOCAL_LABEL}</span></div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='card accent-top'><b>Objectif :</b> vous donner une <b>fourchette crédible</b> en 30 secondes, "
    "puis affiner avec des ventes comparables et les spécificités de votre bien.</div>",
    unsafe_allow_html=True,
)
st.markdown("<hr/>", unsafe_allow_html=True)

# ---------------------------
# Step 1
# ---------------------------
if st.session_state.step == 1:
    colL, colR = st.columns([1.2, 1], gap="large")

    with colL:
        st.markdown("## 📋 Décrivez votre bien")

        c1, c2 = st.columns(2)
        with c1:
            st.selectbox("Type de bien", ["Maison", "Appartement"], key="bien_type")
            st.number_input("Surface (m²)", min_value=10.0, max_value=500.0, step=1.0, key="surface")
            st.selectbox("État du bien", ["À rénover", "Moyen", "Bon", "Rénové"], key="etat")

        with c2:
            st.number_input("Nombre de pièces", min_value=1, max_value=12, step=1, key="nb_pieces")
            st.number_input("Nombre de chambres", min_value=0, max_value=10, step=1, key="nb_chambres")
            st.markdown(f"<div class='card soft'><b>Ville :</b> {LOCAL_LABEL}</div>", unsafe_allow_html=True)

        st.markdown("### 📍 Adresse (uniquement Clermont 60600)")
        st.text_input("Commencez à taper l’adresse", placeholder="Ex : 5 Rue du Chemin Blanc", key="addr_typed")

        try:
            suggestions = geopf_completion(st.session_state.addr_typed, postcode=LOCAL_POSTCODE, city=LOCAL_CITY)
        except Exception:
            suggestions = []

        if suggestions:
            labels = [s["label"] for s in suggestions]
            default_index = labels.index(st.session_state.addr_choice) if st.session_state.addr_choice in labels else 0
            st.selectbox("Suggestions (Clermont uniquement)", labels, index=default_index, key="addr_choice")
        else:
            st.session_state.addr_choice = (st.session_state.addr_typed or "").strip()

        st.markdown(
            "<p class='small-note'>Pour une estimation plus fiable, l’outil est volontairement limité à "
            "<b>Clermont-de-l’Oise (60600)</b>.</p>",
            unsafe_allow_html=True,
        )

        if st.button("🚀 Obtenir ma fourchette (sans engagement)", use_container_width=True):
            addr_choice = (st.session_state.addr_choice or "").strip()
            if not addr_choice or len(addr_choice) < 6:
                st.error("Ajoute une adresse plus complète (ou choisis une suggestion à Clermont).")
                st.stop()

            q = normalize_query_to_clermont(addr_choice)

            try:
                geo = geopf_geocode_one(q)
            except Exception:
                geo = None

            if not geo:
                st.error("Impossible de géocoder l’adresse. Choisis une suggestion ou précise numéro + rue.")
                st.stop()

            # garde-fou Clermont
            label_low = (geo.get("label") or "").lower()
            if LOCAL_POSTCODE not in label_low and LOCAL_CITY.lower() not in label_low:
                st.error("Cette adresse ne semble pas être à Clermont (60600). Choisis une suggestion dans Clermont.")
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
            "<div class='card accent-top'>"
            "✅ Distance à la gare calculée automatiquement<br/>"
            "✅ Quartier estimé (version simple, bientôt polygones réels)<br/>"
            "✅ Fourchette immédiate<br/>"
            "✅ Détails & comparables contre vos coordonnées"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='card soft'><b>Note :</b> l’estimation est indicative. L’affinage final se fait après vérification "
            "(état réel, travaux, terrain, nuisances, etc.).</div>",
            unsafe_allow_html=True,
        )

# ---------------------------
# Step 2
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
        f"<div class='card soft'><b>Adresse géocodée :</b> {geo.get('label','')}<br/>"
        f"<b>Prix/m² indicatif (après facteurs) :</b> {eur(res['prix_m2'])} / m²</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<hr/>", unsafe_allow_html=True)

    # Controls row: back (secondary) + toggle
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
        # Pretty explanation card instead of raw JSON
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

    st.markdown("## 📩 Recevoir le détail (comparables + explication)")

    with st.form("contact_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Votre prénom", key="prenom")
            st.text_input("Votre email", key="email")
        with c2:
            st.text_input("Votre téléphone", key="telephone")
            st.checkbox("J’accepte d’être recontacté au sujet de cette estimation (sans spam).", key="consent")

        submitted = st.form_submit_button("✅ Envoyer le détail + être rappelé", use_container_width=True)

    if submitted:
        if not (st.session_state.prenom and st.session_state.email and st.session_state.telephone and st.session_state.consent):
            st.error("Il manque une info (ou le consentement).")
        else:
            st.session_state["lead"] = {
                "prenom": st.session_state.prenom,
                "email": st.session_state.email,
                "telephone": st.session_state.telephone,
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

            st.success(f"Merci {st.session_state.prenom} ✅ Je te contacte rapidement pour affiner et te donner des comparables précis.")
