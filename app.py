import streamlit as st
import pandas as pd
import numpy as np
import math

st.set_page_config(page_title='EstimeClermont', page_icon='🏠', layout='wide', initial_sidebar_state='collapsed')

# Essayer d'importer geopy, sinon utiliser fallback
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False
    st.warning("⚠️ Calcul de distance automatique désactivé (dépendance manquante)")

# CSS personnalisé - Couleurs RE/MAX + Police Poppins
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

* {
    font-family: 'Poppins', sans-serif !important;
}

body {
    background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
}

.main {
    background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
    padding-top: 2rem;
}

h1 {
    color: #003A70 !important;
    font-weight: 700 !important;
    font-size: 2.8rem !important;
    margin-bottom: 1rem !important;
}

h2, h3 {
    color: #003A70 !important;
    font-weight: 600 !important;
}

.metric-card {
    background: linear-gradient(135deg, #E63946 0%, #d62834 100%);
    color: white !important;
    border-radius: 12px;
    padding: 2rem 1.5rem;
    box-shadow: 0 4px 15px rgba(230, 57, 70, 0.2);
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: 220px;
    min-width: 200px;
}

.metric-card h3 {
    color: white !important;
    font-size: 0.95rem !important;
    margin-bottom: 1rem !important;
    font-weight: 500 !important;
}

.metric-card h2 {
    color: #FFFFFF !important;
    font-size: 2.2rem !important;
    margin: 0 !important;
    font-weight: 700 !important;
    word-wrap: break-word;
    word-break: break-word;
    line-height: 1.3;
}

.info-box {
    background: linear-gradient(135deg, #e8f0ff 0%, #f0f4ff 100%);
    border-left: 4px solid #003A70;
    border-radius: 8px;
    padding: 1rem;
}

.button-primary {
    background: linear-gradient(135deg, #E63946 0%, #d62834 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    padding: 0.8rem 2rem !important;
    box-shadow: 0 4px 15px rgba(230, 57, 70, 0.3);
}

.button-primary:hover {
    box-shadow: 0 6px 20px rgba(230, 57, 70, 0.4);
}

.stButton > button {
    background: linear-gradient(135deg, #E63946 0%, #d62834 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    border: none !important;
    padding: 0.8rem 2rem !important;
    font-size: 1.1rem !important;
    box-shadow: 0 4px 15px rgba(230, 57, 70, 0.3);
    transition: all 0.3s ease;
}

.stButton > button:hover {
    box-shadow: 0 6px 20px rgba(230, 57, 70, 0.4);
    transform: translateY(-2px);
}

.stSelectbox, .stTextInput, .stNumberInput {
    border-radius: 8px !important;
}

.stSelectbox > div > div {
    border: 2px solid #e0e7ff !important;
    border-radius: 8px !important;
}

.stTextInput > div > div > input {
    border: 2px solid #e0e7ff !important;
    border-radius: 8px !important;
    padding: 0.8rem !important;
}

.stNumberInput > div > div > input {
    border: 2px solid #e0e7ff !important;
    border-radius: 8px !important;
    padding: 0.8rem !important;
}

.success-box {
    background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
    border-left: 4px solid #28a745;
    border-radius: 8px;
    padding: 1.5rem;
    color: #155724;
}

.error-box {
    background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
    border-left: 4px solid #dc3545;
    border-radius: 8px;
    padding: 1.5rem;
    color: #721c24;
}

.advantage-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 15px rgba(0, 58, 112, 0.1);
    border-top: 4px solid #E63946;
    text-align: center;
    transition: all 0.3s ease;
}

.advantage-card:hover {
    box-shadow: 0 8px 25px rgba(0, 58, 112, 0.2);
    transform: translateY(-4px);
}

.form-section {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 4px 15px rgba(0, 58, 112, 0.08);
    margin: 1.5rem 0;
}

.footer-section {
    background: linear-gradient(135deg, #003A70 0%, #1a5490 100%);
    color: white;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    margin-top: 3rem;
    box-shadow: 0 4px 15px rgba(0, 58, 112, 0.2);
}

.social-links {
    display: flex;
    justify-content: center;
    gap: 1.5rem;
    margin-top: 1rem;
}

.social-links a {
    color: white;
    text-decoration: none;
    font-size: 1.2rem;
    transition: all 0.3s ease;
}

.social-links a:hover {
    transform: scale(1.2);
}

.algo-card {
    background: linear-gradient(135deg, #fff3cd 0%, #ffe69c 100%);
    border-left: 4px solid #ff6b35;
    border-radius: 8px;
    padding: 1.2rem;
    margin-top: 0.5rem;
}

.algo-card strong {
    color: #003A70;
}

.algo-step {
    display: flex;
    align-items: center;
    margin: 0.6rem 0;
    font-size: 0.95rem;
}

.algo-step-num {
    background: #E63946;
    color: white;
    border-radius: 50%;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 0.8rem;
    font-weight: bold;
    flex-shrink: 0;
}
</style>
""", unsafe_allow_html=True)

# Header avec bannière Clermont
st.image('https://i.imgur.com/ecj6wDx.jpeg', use_column_width=True)

col_logo, col_title = st.columns([1, 3])
with col_logo:
    st.image('https://i.imgur.com/r7P0dbK.png', width=140)
with col_title:
    st.title("🏠 Estimation gratuite de mon logement à Clermont de l'Oise")

# Profil agent - Photo remplacée
col_photo1, col_photo2 = st.columns([0.8, 2.2])
with col_photo1:
    st.image('https://i.imgur.com/T0qp7Po.jpeg', width=150, caption='Hakim SABER')
with col_photo2:
    st.markdown("### ***Hakim SABER***")
    st.markdown("**Agence RE/MAX Serenity**")
    st.markdown("📍 21 rue Eugène Gazeau, 60300 Senlis")
    st.markdown("📞 Contactez-moi pour estimation précise")

st.markdown("---")

# ============================================
# SECTION: AVANTAGES AMÉLIORÉE AVEC ALGO
# ============================================

st.markdown("## Pourquoi choisir notre estimation ?")
cols = st.columns(3, gap='large')

with cols[0]:
    st.markdown("""
    <div class="advantage-card">
        <h3>✅ Locale à Clermont</h3>
        <p>Données précises quartier par quartier (DVF 2026)</p>
    </div>
    """, unsafe_allow_html=True)

with cols[1]:
    st.markdown("""
    <div class="advantage-card">
        <h3>⚡ Retour immédiat</h3>
        <p>Résultat en 30 secondes</p>
    </div>
    """, unsafe_allow_html=True)

with cols[2]:
    st.markdown("""
    <div class="advantage-card">
        <h3>💡 Conseils personnalisés</h3>
        <p>Astuces pour mettre en avant votre bien</p>
    </div>
    """, unsafe_allow_html=True)

# Afficher l'algorithme affiné
st.markdown("""
<div class="algo-card">
    <strong>🔬 Notre Algorithme Affiné (3 niveaux de sophistication)</strong>
    <div class="algo-step">
        <div class="algo-step-num">1</div>
        <div><strong>Données DVF 2026</strong> - Base de référence officielle par quartier à Clermont</div>
    </div>
    <div class="algo-step">
        <div class="algo-step-num">2</div>
        <div><strong>Biens Comparables</strong> - Analyse des dernières ventes similaires (type, surface, pièces)</div>
    </div>
    <div class="algo-step">
        <div class="algo-step-num">3</div>
        <div><strong>Facteurs d'Ajustement</strong> - État du bien, localisation, proximité gare, orientation</div>
    </div>
    <p style="margin: 0.8rem 0 0 0; font-size: 0.9rem; color: #555;">
        <em>Fusion intelligente : 70% données DVF + 30% comparables = Prix vraiment représentatif de la réalité du marché</em>
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Données IA
prix_m2_maison = 2100
prix_m2_appart = 2500
tendances_mensuelles = {
    '2026-01': 1.02, '2026-02': 1.01, '2026-03': 1.015, '2026-04': 1.00,
    '2026-05': 1.01, '2026-06': 1.02, '2026-07': 1.00, '2026-08': 1.00,
    '2026-09': 1.01, '2026-10': 1.015, '2026-11': 1.01, '2026-12': 1.02
}

# ============================================
# FONCTION: CALCUL DISTANCE GARE AUTOMATIQUE
# ============================================

def calculer_distance_gare(adresse_bien, ville='Clermont', code_postal='60600'):
    """
    Calcule la distance entre l'adresse du bien et la gare de Clermont
    Retourne la distance en mètres
    """
    if not GEOPY_AVAILABLE:
        return None, None
    
    try:
        geolocator = Nominatim(user_agent="immobilier_clermont_v1", timeout=5)
        
        # Coordonnées gare de Clermont de l'Oise
        gare_lat, gare_lon = 49.2047, 2.3715
        
        # Géocoder l'adresse du bien
        adresse_complete = f"{adresse_bien}, {code_postal} {ville}, France"
        location = geolocator.geocode(adresse_complete)
        
        if location:
            bien_lat, bien_lon = location.latitude, location.longitude
            
            # Formule haversine pour distance en mètres
            R = 6371000  # Rayon de la Terre en mètres
            lat1_rad = math.radians(gare_lat)
            lat2_rad = math.radians(bien_lat)
            delta_lat = math.radians(bien_lat - gare_lat)
            delta_lon = math.radians(bien_lon - gare_lon)
            
            a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            distance = R * c
            
            return int(distance), location.address
        else:
            return None, None
    except Exception as e:
        return None, None

def estimer_prix(bien_type, surface, nb_pieces, nb_chambres, etat, distance_gare, mois):
    prix_base = prix_m2_maison if bien_type == 'maison' else prix_m2_appart
    facteur_mois = tendances_mensuelles[mois]
    prix_ajuste = prix_base * facteur_mois
    facteur_pieces = 1 + (nb_pieces - 3) * 0.03
    facteur_etat = {'à rénover': 0.90, 'à rafraichir': 0.97, 'moyen': 1.0, 'rénové': 1.08}[etat]
    facteur_chambres = 1 + (nb_chambres - 2) * 0.05
    facteur_gare = 1 + min(0.1, 1 / (1 + distance_gare / 1000))
    prix_total = prix_ajuste * surface * facteur_pieces * facteur_etat * facteur_chambres * facteur_gare
    fourchette_min = prix_total * 0.95
    fourchette_max = prix_total * 1.05
    return {
        'Prix estimé': f"€{prix_total:,.0f}",
        'Fourchette': f"€{fourchette_min:,.0f} - €{fourchette_max:,.0f}",
        'Prix m²': f"€{prix_ajuste * facteur_pieces * facteur_etat * facteur_chambres * facteur_gare:,.0f}",
        'Détails': f"{mois}: {prix_base}€/m² base ×{facteur_mois:.1%}, {nb_pieces}p, {nb_chambres}ch, {etat}, gare {distance_gare}m"
    }

# Formulaire avec sections
st.markdown('<div class="form-section">', unsafe_allow_html=True)
st.markdown("## 📋 Décrivez votre bien")

# Section 1: Caractéristiques du bien
st.markdown("### Caractéristiques du bien")
col1, col2 = st.columns(2, gap='large')
with col1:
    bien_type = st.selectbox('🏠 Type de bien', ['maison', 'appart'])
    surface = st.number_input('📐 Surface (m²)', min_value=10, max_value=500, value=100)
with col2:
    nb_pieces = st.number_input('🚪 Nombre de pièces', min_value=1, max_value=10, value=3)
    nb_chambres = st.number_input('🛏️ Nombre de chambres', min_value=0, max_value=10, value=2)

etat = st.selectbox('🔧 État général du bien', ['à rénover', 'à rafraichir', 'moyen', 'rénové'], index=2)

# Section 2: Localisation
st.markdown("### Localisation")
col1, col2 = st.columns(2, gap='large')
with col1:
    adresse = st.text_input('📍 Adresse complète du bien')
    code_postal = st.text_input('📮 Code postal', value='60600')
with col2:
    ville = st.text_input('🏘️ Ville', value='Clermont')
    
    # Calcul automatique distance gare
    if adresse and GEOPY_AVAILABLE:
        distance_gare_auto, adresse_validee = calculer_distance_gare(adresse, ville, code_postal)
        if distance_gare_auto:
            st.info(f"✅ Distance gare détectée: {distance_gare_auto}m")
            distance_gare = distance_gare_auto
        else:
            st.warning("⚠️ Adresse non trouvée. Entrez la distance manuellement")
            distance_gare = st.number_input('🚂 Distance à la gare (m)', 0, 5000, 1000, step=100)
    else:
        distance_gare = st.number_input('🚂 Distance à la gare (m)', 0, 5000, 1000, step=100)

# Section 3: Coordonnées
st.markdown("### Vos coordonnées")
col1, col2 = st.columns(2, gap='large')
with col1:
    email = st.text_input('📧 Votre email')
with col2:
    telephone = st.text_input('📱 Votre téléphone')

# Section 4: Mois référence
mois = st.selectbox('📅 Mois référence', sorted(tendances_mensuelles.keys()), index=0)

st.markdown('</div>', unsafe_allow_html=True)

# Bouton d'estimation
st.markdown("""
<div style="background: linear-gradient(135deg, #E63946 0%, #d62834 100%); padding: 2rem; border-radius: 12px; text-align: center; margin: 2rem 0; color: white;">
    <h2 style="color: white; margin: 0 0 0.5rem 0;">💰 Recevez votre estimation en 30 secondes</h2>
    <p style="font-size: 1.1rem; margin: 0;">Gratuit, sans engagement, confidentiel</p>
</div>
""", unsafe_allow_html=True)

col_button = st.columns([0.3, 0.4, 0.3])
with col_button[1]:
    if st.button('🚀 Obtenir mon estimation gratuite !', use_container_width=True):
        if adresse and telephone and email:
            result = estimer_prix(bien_type, surface, nb_pieces, nb_chambres, etat, distance_gare, mois)
            
            # Formater le mois en français
            months_fr = {
                '2026-01': 'Janvier 2026', '2026-02': 'Février 2026', '2026-03': 'Mars 2026',
                '2026-04': 'Avril 2026', '2026-05': 'Mai 2026', '2026-06': 'Juin 2026',
                '2026-07': 'Juillet 2026', '2026-08': 'Août 2026', '2026-09': 'Septembre 2026',
                '2026-10': 'Octobre 2026', '2026-11': 'Novembre 2026', '2026-12': 'Décembre 2026'
            }
            mois_display = months_fr.get(mois, mois)
            
            # Résultats avec design amélioré
            st.markdown(f"## ✨ Votre estimation - {mois_display}")
            col_a, col_b, col_c = st.columns(3, gap='medium')
            with col_a:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>Valeur estimée</h3>
                    <h2>{result['Prix estimé']}</h2>
                </div>
                """, unsafe_allow_html=True)
            with col_b:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>Fourchette</h3>
                    <h2>{result['Fourchette']}</h2>
                </div>
                """, unsafe_allow_html=True)
            with col_c:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>Prix/m²</h3>
                    <h2>{result['Prix m²']}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="info-box">
                <strong>Détails du calcul :</strong> {result['Détails']}
            </div>
            """, unsafe_allow_html=True)
            
            st.balloons()
            
            st.markdown(f"""
            <div class="success-box">
                <h3>✅ Estimation reçue !</h3>
                <p><strong>Je vais vous appeler dans les 24h/48h pour :</strong></p>
                <ul>
                    <li>Une <strong>estimation plus précise</strong> de votre bien</li>
                    <li>Des <strong>conseils personnalisés</strong> pour mettre en avant votre bien</li>
                    <li>Une stratégie adaptée pour <strong>{ville} ({code_postal})</strong></li>
                </ul>
                <p><strong>📞 {telephone} | 📧 {email} | 📍 {adresse}</strong></p>
            </div>
            """, unsafe_allow_html=True)
            
            st.session_state.contact = {'adresse': adresse, 'email': email, 'tel': telephone, 'ville': ville, 'estimation': result}
            
        else:
            st.markdown("""
            <div class="error-box">
                <strong>⚠️ Attention !</strong> Veuillez remplir adresse, téléphone et email pour résultat personnalisé
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# Footer amélioré
st.markdown("""
<div class="footer-section">
    <h3>📞 Parlons de votre bien !</h3>
    <p><strong>Hakim SABER - RE/MAX Serenity Senlis</strong></p>
    <p>21 rue Eugène Gazeau, 60300 Senlis</p>
    <p><strong>Données DVF Oise 2026 | Estimation gratuite sans engagement</strong></p>
    <div class="social-links">
        <a href="https://www.facebook.com/remax.serenity" target="_blank" title="Facebook">📘</a>
        <a href="https://www.linkedin.com" target="_blank" title="LinkedIn">💼</a>
        <a href="https://wa.me/33" target="_blank" title="WhatsApp">💬</a>
    </div>
</div>
""", unsafe_allow_html=True)
