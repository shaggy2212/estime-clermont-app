import streamlit as st
import numpy as np
import requests
import streamlit.components.v1 as components
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

# Gare Clermont-de-l'Oise (POINT lon lat)
GARE_LON = 2.41767
GARE_LAT = 49.38531

# Périmètre (communes autorisées)
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

# Géoplateforme (IGN)
GEOPF_COMPLETION_URL = "https://data.geopf.fr/geocodage/completion/"
GEOPF_SEARCH_URL = "https://data.geopf.fr/geocodage/search"

# ---------------------------
# Session state
# ---------------------------
st.session_state.setdefault("step", 1)
st.session_state.setdefault("geo", None)
st.session_state.setdefault("res", None)

# Step 1 inputs
st.session_state.setdefault("area_name", AUTO_AREA)       # selectbox key
st.session_state.setdefault("area_locked", False)         # internal lock
st.session_state.setdefault("detected_area", DEFAULT_AREA)  # detected area used when AUTO
st.session_state.setdefault("bien_type", "Maison")
st.session_state.setdefault("surface", 100.0)
st.session_state.setdefault("etat", "Moyen")
st.session_state.setdefault("nb_pieces", 3)
st.session_state.setdefault("nb_chambres", 2)
st.session_state.setdefault("addr_typed", "")
st.session_state.setdefault("addr_choice", "")            # label brut
st.session_state.setdefault("addr_choice_display", "")    # label affiché (peut contenir préfixe)

# Contact
st.session_state.setdefault("prenom", "")
st.session_state.setdefault("email", "")
st.session_state.setdefault("telephone", "")
st.session_state.setdefault("consent", False)

# Toggle explication + scroll flag
st.session_state.setdefault("show_explain", False)
st.session_state.setdefault("scroll_top", False)

# ---------------------------
# CSS
# ---------------------------
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
* {{ font-family: 'Poppins', sans-serif !important; }}

.main {{ background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%); }}

h1 {{
    color: {PRIMARY} !important;
    font-weight: 800 !important;
    text-align: center !important;
    margin-bottom: 0.2rem !important;
}}
h2 {{ color: {PRIMARY} !important; font-weight: 750 !important; }}

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
.metric .v {{ font-size:1.65rem; font-weight:850; margin:0.12rem 0 0 0; letter-spacing:-0.02em; }}

hr {{ border: none; border-top: 1px solid rgba(0,0,0,0.08); margin: 1.3rem 0; }}

/* Primary buttons (cta + submit) */
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

/* Secondary button style (Back) via wrapper */
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
# Helpers
# ---------------------------
def scroll_to_top_if_needed():
    # Works in most Streamlit contexts (including embed). If blocked by iframe policies,
    # it simply won't scroll (but won't crash).
    if st.session_state.get("scroll_top"):
        components.html("<script>window.scrollTo(0,0);</script>", height=0)
        st.session_state.scroll_top = False


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


def normalize_query_to_area(q: str, city: str, postcode: str) -> str:
    q = (q or "").strip()
    if not q:
        return q
    low = norm(q)
    if postcode not in low and norm(city) not in low:
        q = f"{q}, {postcode} {city}, Oise, France"
    return q


def get_effective_area() -> Tuple[str, Dict[str, str]]:
    """
    On ne modifie jamais 'area_name' programmatique après rendu du widget.
    Si l'utilisateur est en AUTO, on utilise 'detected_area' (si présent).
    """
    if st.session_state.area_name in AREAS:
        a = st.session_state.area_name
        return a, AREAS[a]

    detected = st.session_state.get("detected_area")
    if detected in AREAS:
        return detected, AREAS[detected]

    return DEFAULT_AREA, AREAS[DEFAULT_AREA]


@st.cache_data(ttl=60 * 60)
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
    # TEMPORAIRE (bientôt polygones)
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
    # TEMPORAIRE : à remplacer par DVF
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


def parse_display_choice(display_value: str) -> Tuple[Optional[str], str]:
    """
    display_value peut être:
      - "Commune — label"
      - "Commune—label"
      - "Commune - label"
      - "label"
    Retourne (area_name ou None, label)
    """
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
    """
    On ne touche pas au selectbox 'area_name'. On stocke la détection dans 'detected_area'.
    """
    display_val = st.session_state.get("addr_choice_display", "")
    area, label = parse_display_choice(display_val)

    st.session_state.addr_choice = label
    if area:
        st.session_state.detected_area = area
        st.session_state.area_locked = True


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
        st.markdown("## 📍 Votre secteur")
        area_options = [AUTO_AREA] + list(AREAS.keys())
        st.selectbox("Choisissez la commune (ou laissez en auto)", area_options, key="area_name")

        # If manual choose, override detection
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
            # ✅ Message corrigé: sur la partie descriptive
            st.markdown(
                "<div class='small-note'>Plus le descriptif est précis, plus l’estimation sera cohérente.</div>",
                unsafe_allow_html=True,
            )

        st.markdown("### 🧭 Localisation")
        st.text_input("Commencez à taper l’adresse", placeholder="Ex : 5 Rue du Chemin Blanc", key="addr_typed")
        # ✅ Message déplacé au bon endroit
        st.markdown(
            "<div class='small-note'>Plus l’adresse est précise (numéro + rue), plus le résultat est fiable.</div>",
            unsafe_allow_html=True,
        )

        typed = st.session_state.addr_typed

        suggestions_display: List[str] = []
        if st.session_state.area_name == AUTO_AREA:
            # Mode auto: agrège suggestions de toutes les communes (avec préfixe)
            for area_name, info in AREAS.items():
                try:
                    labs = geopf_completion(typed, postcode=info["postcode"], city=info["city"], max_resp=5)
                except Exception:
                    labs = []
                for lab in labs:
                    suggestions_display.append(f"{area_name} — {lab}")
        else:
            # Mode manuel: commune verrouillée
            try:
                labs = geopf_completion(typed, postcode=ai["postcode"], city=ai["city"])
            except Exception:
                labs = []
            suggestions_display = labs[:]

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
            st.session_state.addr_choice = (typed or "").strip()
            st.session_state.addr_choice_display = st.session_state.addr_choice

        # Feedback
        if st.session_state.area_name == AUTO_AREA:
            detected = st.session_state.get("detected_area")
            if detected in AREAS and st.session_state.area_locked:
                inf = AREAS[detected]
                st.markdown(
                    f"<div class='card soft'><b>Commune détectée :</b> {detected} — <b>CP :</b> {inf['postcode']}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<p class='small-note'>Astuce : choisissez une suggestion (préfixée par la commune) pour détecter automatiquement.</p>",
                    unsafe_allow_html=True,
                )

        if st.button("🚀 Obtenir ma fourchette (sans engagement)", use_container_width=True):
            # Si AUTO, déduit depuis la sélection au moment du clic
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

            # ✅ Important: remonter en haut au Step 2
            st.session_state.scroll_top = True
            st.rerun()

    with colR:
        st.markdown("## 💎 Ce que vous obtenez")
        st.markdown(
            "<div class='card accent-top'>"
            "✅ Adresse filtrée sur la commune (auto ou manuel)<br/>"
            "✅ Distance à la gare calculée automatiquement<br/>"
            "✅ Fourchette immédiate<br/>"
            "✅ Détails & comparables contre vos coordonnées"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='card soft'><b>Note :</b> l’estimation est indicative. L’affinage final se fait après vérification "
            "(état réel, travaux, terrain, nuisances, exposition, prestations) — et les comparables DVF.</div>",
            unsafe_allow_html=True,
        )

# ---------------------------
# Step 2
# ---------------------------
if st.session_state.step == 2 and st.session_state.geo and st.session_state.res:
    # ✅ force scroll top so user sees results first
    scroll_to_top_if_needed()

    geo = st.session_state.geo
    res = st.session_state.res

    effective_area, ai = get_effective_area()

    # ✅ Secteur affiché: pour Clermont-de-l'Oise, on ajoute le quartier (Nord/Centre/etc.)
    if effective_area == "Clermont-de-l'Oise":
        sector_display = f"{effective_area} — {res.get('quartier', '')}"
    else:
        sector_display = f"{effective_area}"

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
            st.session_state.scroll_top = True  # remonte aussi en revenant
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

    # ✅ On garde le formulaire en dessous (pas de scroll automatique vers lui)
    st.markdown("<hr/>", unsafe_allow_html=True)
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
                "secteur_effectif": effective_area,
                "secteur_affiche": sector_display,
                "code_postal": ai.get("postcode", ""),
                "ville_api": ai.get("city", ""),
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
                "quartier": res.get("quartier", ""),
                "estimation_min": float(res["min"]),
                "estimation_max": float(res["max"]),
            }
            st.success(f"Merci {st.session_state.prenom} ✅ Je te contacte rapidement pour affiner et te donner des comparables précis.")
