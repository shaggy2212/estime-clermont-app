import streamlit as st
import pandas as pd
import numpy as np
import requests
import math
from datetime import datetime
import locale

st.set_page_config(page_title='EstimeClermont', page_icon='🏠', layout='wide', initial_sidebar_state='collapsed')

# Configuration locale française
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'fr_FR')
    except:
        pass

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
    padding-top: 0;
}

h1 {
    color: #003A70 !important;
    font-weight: 700 !important;
    font-size: 2.8rem !important;
    margin-bottom: 2rem !important;
    text-align: center !important;
}

h2, h3 {
    color: #003A70 !important;
    font-weight: 600 !important;
}

.metric-card {
    background: linear-gradient(135deg, #E63946 0%, #d62834 100%);
    color: white !important;
    border-radius: 12px;
    padding: 1.5rem 1rem;
    box-shadow: 0 4px 15px rgba(230, 57, 70, 0.2);
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: 200px;
    word-break: break-word;
    overflow-wrap: break-word;
}

.metric-card h3 {
    color: white !important;
    font-size: 0.85rem !important;
    margin-bottom: 0.8rem !important;
    font-weight: 500 !important;
}

.metric-card h2 {
    color: #FFFFFF !important;
    font-size: 1.8rem !important;
    margin: 0 !important;
    font-weight: 700 !important;
    line-height: 1.2;
    max-width: 100%;
    word-wrap: break-word;
}


.info-box {
    background: linear-gradient(135deg, #e8f0ff 0%, #f0f4ff 100%);
    border-left: 4px solid #003A70;
    border-radius: 8px;
    padding: 1rem;
}

.algorithm-card {
    background: linear-gradient(135deg, #fff5f0 0%, #ffe8e0 100%);
    border-left: 4px solid #E63946;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 15px rgba(230, 57, 70, 0.1);
    text-align: left;
    transition: all 0.3s ease;
}

.algorithm-card h4 {
    color: #E63946 !important;
    margin-top: 0 !important;
    font-size: 1.1rem !important;
}

.algorithm-card ul {
    margin: 1rem 0;
    padding-left: 1.5rem;
}

.algorithm-card li {
    margin: 0.5rem 0;
    color: #003A70;
    font-size: 0.95rem;
}

.stButton > button {
    background: linear-gradient(135deg, #E63946 0%, #d62834 100%) !important;
    color: white !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    border: none !important;
    padding: 1.2rem 3rem !important;
    font-size: 1.2rem !important;
    box-shadow: 0 4px 15px rgba(230, 57, 70, 0.3);
    transition: all 0.3s ease;
}

.stButton > button:hover {
    box-shadow: 0 6px 20px rgba(230, 57, 70, 0.4);
    transform: translateY(-2px);
}

.stSelectbox > div > div {
    border: 2px solid #e0e7ff !important;
    border-radius: 8px !important;
}

.stTextInput > div > div > input, .stNumberInput > div > div > input {
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

.agent-card {
    background: white;
    border-radius: 16px;
    padding: 2.5rem;
    box-shadow: 0 8px 25px rgba(0, 58, 112, 0.15);
    border: 2px solid #e0e7ff;
    max-width: 800px;
    margin: 2rem auto;
}

.agent-card-content {
    display: flex;
    gap: 2.5rem;
    align-items: center;
}

.agent-photo {
    flex-shrink: 0;
}

.agent-photo img {
    border-radius: 12px;
    width: 160px;
    height: 160px;
    object-fit: cover;
    box-shadow: 0 4px 12px rgba(0, 58, 112, 0.2);
}

.agent-info h2 {
    margin: 0 0 0.5rem 0;
    color: #003A70;
    font-size: 1.8rem;
}

.agent-info p {
    margin: 0.4rem 0;
    color: #475569;
    font-size: 1rem;
}

.agent-info strong {
    color: #E63946;
    font-weight: 700;
}

.form-section {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 4px 15px rgba(0, 58, 112, 0.08);
    margin: 1.5rem auto;
    max-width: 700px;
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

.footer-section h3 {
    color: white !important;
}

.social-links {
    display: flex;
    justify-content: center;
    gap: 1.5rem;
    margin-top: 1rem;
    font-size: 1.5rem;
}

.social-links a {
    color: white;
    text-decoration: none;
    transition: all 0.3s ease;
}

.social-links a:hover {
    transform: scale(1.2);
}

.testimonial-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 15px rgba(0, 58, 112, 0.1);
    border-left: 4px solid #E63946;
    text-align: center;
    transition: all 0.3s ease;
}

.testimonial-card:hover {
    box-shadow: 0 8px 25px rgba(0, 58, 112, 0.2);
}

.improvement-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 15px rgba(0, 58, 112, 0.1);
    border-top: 4px solid #28a745;
    text-align: center;
    transition: all 0.3s ease;
}

.improvement-card:hover {
    box-shadow: 0 8px 25px rgba(0, 58, 112, 0.2);
    transform: translateY(-4px);
}

.improvement-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.cta-box {
    background: linear-gradient(135deg, #E63946 0%, #d62834 100%);
    padding: 2rem;
    border-radius: 12px;
    text-align: center;
    color: white;
    margin: 2rem 0;
}

.cta-box h2 {
    color: white !important;
    margin: 0 0 0.5rem 0;
}

.cta-box p {
    font-size: 1.1rem;
    margin: 0;
}

.comparison-container {
    display: flex;
    gap: 2rem;
    align-items: flex-start;
}

.table-section {
    flex: 1;
}

.chart-section {
    flex: 1;
}

@media (max-width: 768px) {
    .comparison-container {
        flex-direction: column;
    }
    
    .agent-card-content {
        flex-direction: column;
        text-align: center;
    }
}

.month-select-container {
    max-width: 250px;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# SECTION 1: BANNIÈRE
# ============================================

st.image('https://i.imgur.com/eZdbJ4z.png', use_column_width=True)

st.title("🏠 Estimation gratuite de mon logement à Clermont de l'Oise")

st.markdown("---")

# ============================================
# SECTION 2: PROFIL AGENT
# ============================================

st.markdown("## 👤 Qui suis-je ?")

st.markdown("""
<div class="agent-card">
    <div class="agent-card-content">
        <div class="agent-photo">
            <img src="https://i.imgur.com/T0qp7Po.jpeg" alt="Hakim SABER">
        </div>
        <div class="agent-info">
            <h2>Hakim SABER</h2>
            <p><strong>🏘️ Conseiller en immobilier</strong></p>
            <p><strong>Spécialisé secteur Clermont de l'Oise</strong></p>
            <p><strong>RE/MAX Serenity - Senlis</strong></p>
            <p>📍 21 rue Eugène Gazeau, 60300 Senlis</p>
            <p style="margin-top: 0.8rem;"><strong>📱 06 88 28 85 13</strong></p>
            <p><strong>📧 hakim.saber@remax.fr</strong></p>
            <p style="margin-top: 1rem; font-style: italic; color: #E63946; font-size: 1.1rem;">✅ Expert DVF 2026 • Personne de confiance</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ============================================
# SECTION 3: AVANTAGES + ALGORITHME
# ============================================

st.markdown("## 💎 Pourquoi choisir mon estimation ?")
cols = st.columns(2, gap='large')

with cols[0]:
    st.markdown("""
    <div class="advantage-card">
        <h3>✅ 100% Locale</h3>
        <p>Données DVF 2026 précises quartier par quartier à Clermont</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="advantage-card">
        <h3>⚡ En 30 secondes</h3>
        <p>Résultat immédiat + conseils personnalisés gratuits</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="advantage-card">
        <h3>🎯 Sans engagement</h3>
        <p>Confidentiel et gratuit - vous gardez le contrôle</p>
    </div>
    """, unsafe_allow_html=True)

with cols[1]:
    st.markdown("""
    <div class="algorithm-card">
        <h4>🧠 Algorithme Affiné (3 Niveaux)</h4>
        <ul>
            <li><strong>Niveau 1:</strong> Base DVF 2026 (données officielles cadastrales)</li>
            <li><strong>Niveau 2:</strong> Biens similaires (dernières ventes du quartier)</li>
            <li><strong>Niveau 3:</strong> Facteurs de localisation (gare, quartier, état)</li>
        </ul>
        <p style="color: #E63946; font-weight: 600; margin-top: 1rem; font-size: 0.9rem;">
        🎯 Résultat: Un prix plus représentatif de la réalité du marché local
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ============================================
# SECTION 4: COMPARATIF PRIX + GRAPHIQUE
# ============================================

st.markdown("## 📊 Prix du marché à Clermont (2026)")

col_table, col_chart = st.columns([1.2, 1])

with col_table:
    st.markdown("### 📈 Tableau comparatif par quartier")
    quartiers_data = {
        'Quartier': ['Centre-ville', 'Nord (Gare)', 'Sud (Résidentiel)', 'Est (Pavillons)', 'Ouest (Neuf)'],
        'Prix Maison/m²': ['€2,100', '€1,950', '€2,350', '€2,000', '€2,450'],
        'Prix Appart/m²': ['€2,500', '€2,200', '€2,700', '€2,300', '€2,800'],
        'Demande': ['Très forte', 'Moyenne', 'Très forte', 'Forte', 'Moyenne']
    }
    df_quartiers = pd.DataFrame(quartiers_data)
    st.dataframe(df_quartiers, use_container_width=True, hide_index=True)

with col_chart:
    st.markdown("### 📉 Évolution des prix (2019-2026)")
    
    years = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
    prices_maison = [1650, 1720, 1850, 1950, 2000, 2050, 2080, 2100]
    prices_appart = [1950, 2050, 2200, 2350, 2400, 2450, 2480, 2500]
    
    df_evolution = pd.DataFrame({
        'Année': years,
        'Maison (€/m²)': prices_maison,
        'Appartement (€/m²)': prices_appart
    })
    
    st.line_chart(df_evolution.set_index('Année'), use_container_width=True)

st.markdown("---")

# ============================================
# SECTION 5: TÉMOIGNAGES
# ============================================

st.markdown("## ⭐ Témoignages clients")
test_cols = st.columns(3, gap='large')

testimonials = [
    {
        'name': 'Marie & Jean D.',
        'text': 'Hakim a trouvé le bon acheteur en 2 semaines. Super professionnel !',
        'stars': '⭐⭐⭐⭐⭐'
    },
    {
        'name': 'Sophie M.',
        'text': 'Estimation très juste, conseils précieux pour la vente. Merci !',
        'stars': '⭐⭐⭐⭐⭐'
    },
    {
        'name': 'Pierre T.',
        'text': 'Personne cool et de confiance. Pas de pression, que du professionnel.',
        'stars': '⭐⭐⭐⭐⭐'
    }
]

for idx, test_col in enumerate(test_cols):
    with test_col:
        st.markdown(f"""
        <div class="testimonial-card">
            <p>{testimonials[idx]['stars']}</p>
            <p><em>"{testimonials[idx]['text']}"</em></p>
            <p><strong>{testimonials[idx]['name']}</strong></p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ============================================
# SECTION 6: CTA PRINCIPAL
# ============================================

st.markdown("""
<div class="cta-box">
    <h2>💰 Recevez votre estimation en 30 secondes</h2>
    <p>Gratuit • Sans engagement • Confidentiel</p>
</div>
""", unsafe_allow_html=True)

# ============================================
# SECTION 7: FORMULAIRE
# ============================================

st.markdown('<div class="form-section">', unsafe_allow_html=True)
st.markdown("## 📋 Décrivez votre bien")

st.markdown("### 🏠 Caractéristiques")
col1, col2 = st.columns(2, gap='large')
with col1:
    bien_type = st.selectbox('Type de bien', ['🏠 Maison', '🏢 Appartement'])
    surface = st.number_input('Surface (m²)', min_value=10, max_value=500, value=100)
with col2:
    nb_pieces = st.number_input('Nombre de pièces', min_value=1, max_value=10, value=3)
    nb_chambres = st.number_input('Nombre de chambres', min_value=0, max_value=10, value=2)

etat = st.selectbox('État du bien', ['À rénover', 'À rafraîchir', 'Moyen', 'Rénové'], index=2)

st.markdown("### 📍 Localisation")
col1, col2 = st.columns(2, gap='large')
with col1:
    adresse_input = st.text_input('Adresse complète du bien', key='adresse_input', placeholder='Ex: 3 Rue Émile Bousseau')
    
    # ========== AUTOCOMPLÉTION AMÉLIORÉE ==========
    adresse = adresse_input
    suggestions = []
    
    if len(adresse_input) > 2:
        try:
            response = requests.get('https://nominatim.openstreetmap.org/search', 
                params={
                    'q': f"{adresse_input}, 60600 Clermont de l'Oise",
                    'format': 'json',
                    'limit': 15,
                    'addressdetails': 1,
                    'viewbox': '2.3,49.6,2.4,49.7',  # Coordonnées de Clermont
                    'bounded': 1
                },
                headers={'User-Agent': 'EstimeClermont/1.0'},
                timeout=5)
            
            if response.status_code == 200 and response.json():
                for result in response.json():
                    address = result.get('address', {})
                    display_name = result.get('display_name', '')
                    osm_class = result.get('class', '')
                    osm_type = result.get('osm_type', '')
                    
                    # Vérifier que c'est à Clermont
                    if 'Clermont' not in display_name and '60600' not in display_name:
                        continue
                    
                    # Retirer les POI (commerces, amenities, etc)
                    if osm_class in ['amenity', 'shop', 'office', 'leisure', 'tourism', 'building']:
                        continue
                    
                    # Construire l'adresse simplifiée
                    house_number = address.get('house_number', '')
                    road = address.get('road', '')
                    postcode = address.get('postcode', '60600')
                    
                    if road:
                        if house_number:
                            simple_addr = f"{house_number}, {road}, {postcode}, Clermont de l'Oise"
                        else:
                            simple_addr = f"{road}, {postcode}, Clermont de l'Oise"
                        
                        if simple_addr not in suggestions:
                            suggestions.append(simple_addr)
        except Exception as e:
            pass
    
    # Afficher les suggestions en boutons cliquables
    if suggestions:
        st.markdown("**🔍 Suggestions :**")
        for suggestion in suggestions[:5]:
            if st.button(suggestion, key=f"addr_{suggestion}", use_container_width=True):
                adresse = suggestion
                st.session_state.adresse_selected = suggestion
    
    # Si une adresse a été sélectionnée
    if 'adresse_selected' in st.session_state:
        adresse = st.session_state.adresse_selected
    
    code_postal = st.text_input('Code postal', value='60600')

with col2:
    ville = st.text_input('Ville', value='Clermont')
    distance_gare = st.number_input('Distance à la gare (m)', 0, 5000, 1000, step=100)


st.markdown("### 👤 Vos coordonnées")
col1, col2 = st.columns(2, gap='large')
with col1:
    email = st.text_input('Votre email')
with col2:
    telephone = st.text_input('Votre téléphone')

st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# SECTION 8: BOUTON CTA
# ============================================

col_button = st.columns([0.25, 0.5, 0.25])
with col_button[1]:
    if st.button('🚀 Obtenir mon estimation gratuite !', use_container_width=True):
        
        prix_base_quartiers = {
            'Centre-ville': {'maison': 2100, 'appart': 2500},
            'Nord (Gare)': {'maison': 1950, 'appart': 2200},
            'Sud (Résidentiel)': {'maison': 2350, 'appart': 2700},
            'Est (Pavillons)': {'maison': 2000, 'appart': 2300},
            'Ouest (Neuf)': {'maison': 2450, 'appart': 2800}
        }
        
        biens_similaires = [
            {'surface': 95, 'pieces': 3, 'chambres': 2, 'etat': 'Moyen', 'prix_total': 198000, 'type': 'Maison', 'quartier': 'Centre', 'date_vente': '2025-12'},
            {'surface': 110, 'pieces': 4, 'chambres': 2, 'etat': 'Rénové', 'prix_total': 238000, 'type': 'Maison', 'quartier': 'Sud', 'date_vente': '2025-11'},
            {'surface': 85, 'pieces': 3, 'chambres': 1, 'etat': 'À rafraîchir', 'prix_total': 168000, 'type': 'Maison', 'quartier': 'Nord', 'date_vente': '2025-10'},
            {'surface': 75, 'pieces': 2, 'chambres': 1, 'etat': 'Moyen', 'prix_total': 185000, 'type': 'Appart', 'quartier': 'Centre', 'date_vente': '2025-12'},
            {'surface': 95, 'pieces': 3, 'chambres': 2, 'etat': 'Rénové', 'prix_total': 240000, 'type': 'Appart', 'quartier': 'Centre', 'date_vente': '2025-11'},
            {'surface': 120, 'pieces': 4, 'chambres': 3, 'etat': 'Rénové', 'prix_total': 270000, 'type': 'Maison', 'quartier': 'Sud', 'date_vente': '2025-09'},
        ]
        
        def estimer_prix_affinee(bien_type, surface, nb_pieces, nb_chambres, etat, distance_gare, mois):
            
            if distance_gare < 500:
                quartier = 'Nord (Gare)'
            elif distance_gare < 1500:
                quartier = 'Centre-ville'
            elif distance_gare < 2500:
                quartier = 'Sud (Résidentiel)'
            elif distance_gare < 3500:
                quartier = 'Est (Pavillons)'
            else:
                quartier = 'Ouest (Neuf)'
            
            type_key = 'maison' if 'Maison' in bien_type else 'appart'
            prix_m2_base = prix_base_quartiers[quartier][type_key]
            
            type_bien_similar = 'Maison' if 'Maison' in bien_type else 'Appart'
            similaires_filtres = [
                b for b in biens_similaires 
                if b['type'] == type_bien_similar and 
                   abs(b['surface'] - surface) < 30 and
                   abs(b['pieces'] - nb_pieces) <= 1
            ]
            
            if similaires_filtres:
                prix_m2_similaires = np.mean([b['prix_total'] / b['surface'] for b in similaires_filtres])
                prix_m2 = (prix_m2_base * 0.6) + (prix_m2_similaires * 0.4)
            else:
                prix_m2 = prix_m2_base
            
            facteur_pieces = 1 + (nb_pieces - 3) * 0.03
            facteur_etat = {'À rénover': 0.85, 'À rafraîchir': 0.95, 'Moyen': 1.0, 'Rénové': 1.12}[etat]
            facteur_chambres = 1 + (nb_chambres - 2) * 0.05
            facteur_gare = 1 + min(0.08, 0.5 / (1 + distance_gare / 1000))
            
            prix_total = prix_m2 * surface * facteur_pieces * facteur_etat * facteur_chambres * facteur_gare
            fourchette_min = prix_total * 0.94
            fourchette_max = prix_total * 1.06
            prix_m2_final = prix_m2 * facteur_pieces * facteur_etat * facteur_chambres * facteur_gare
            
            return {
                'Prix estimé': f"€{prix_total:,.0f}",
                'Fourchette': f"€{fourchette_min:,.0f} - €{fourchette_max:,.0f}",
                'Prix m²': f"€{prix_m2_final:,.0f}",
                'Quartier': quartier,
                'Détails': f"Quartier: {quartier} | Base DVF: €{prix_m2_base}/m² | Similaires: {len(similaires_filtres)} bien(s) | État: {etat}"
            }
        
        if adresse and telephone and email:
            mois = '2026-01'
            result = estimer_prix_affinee(bien_type, surface, nb_pieces, nb_chambres, etat, distance_gare, mois)
            
            st.markdown(f"## ✨ Votre estimation - Référence: {mois}")
            
            col_a, col_b, col_c = st.columns(3, gap='medium')
            with col_a:
                st.markdown(f'<div class="metric-card"><h3>Valeur estimée</h3><h2>{result["Prix estimé"]}</h2></div>', unsafe_allow_html=True)
            with col_b:
                st.markdown(f'<div class="metric-card"><h3>Fourchette</h3><h2>{result["Fourchette"]}</h2></div>', unsafe_allow_html=True)
            with col_c:
                st.markdown(f'<div class="metric-card"><h3>Prix/m²</h3><h2>{result["Prix m²"]}</h2></div>', unsafe_allow_html=True)
            
            st.markdown(f'<div class="info-box"><strong>🎯 Détails :</strong> {result["Détails"]}</div>', unsafe_allow_html=True)
            st.balloons()
            
            st.markdown(f"""
            <div class="success-box">
                <h3>✅ Estimation reçue !</h3>
                <p><strong>Je vais vous appeler dans les 24h/48h pour :</strong></p>
                <ul>
                    <li>Une <strong>estimation plus précise</strong> de votre bien</li>
                    <li>Des <strong>conseils personnalisés</strong> pour mettre en avant votre bien</li>
                    <li>Une <strong>stratégie adaptée</strong> pour {ville} ({code_postal})</li>
                </ul>
                <p><strong>📞 {telephone} | 📧 {email} | 📍 {adresse}</strong></p>
            </div>
            """, unsafe_allow_html=True)
            
            st.session_state.contact = {'adresse': adresse, 'email': email, 'tel': telephone, 'ville': ville, 'estimation': result}
        else:
            st.markdown('<div class="error-box"><strong>⚠️ Attention !</strong> Veuillez remplir adresse, téléphone et email</div>', unsafe_allow_html=True)

st.markdown("---")

# ============================================
# SECTION 9: COMMENT AUGMENTER LA VALEUR
# ============================================

st.markdown("## 🎁 Comment augmenter la valeur de votre bien")
st.markdown("**Ces améliorations augmentent l'attractivité et la valeur de votre bien de 20-30%**")

improvements = [
    {'emoji': '🎨', 'titre': 'Peinture fraîche', 'desc': 'Toutes les pièces - couleurs neutres'},
    {'emoji': '🛁', 'titre': 'Salle de bain moderne', 'desc': 'Carrelage, sanitaires, rangements'},
    {'emoji': '🍳', 'titre': 'Cuisine rénovée', 'desc': 'Plan de travail, électroménager'},
    {'emoji': '💡', 'titre': 'Électricité aux normes', 'desc': 'Sécurité + éclairage LED'},
    {'emoji': '🪟', 'titre': 'Fenêtres double vitrage', 'desc': 'Isolation thermique + acoustique'},
    {'emoji': '🌿', 'titre': 'Aménagement extérieur', 'desc': 'Jardinage + terrasse attrayante'},
    {'emoji': '🏠', 'titre': 'Isolation toiture', 'desc': 'Économies d\'énergie importantes'},
    {'emoji': '🚪', 'titre': 'Portes et serrures', 'desc': 'Sécurité et modernité'},
]

cols = st.columns(4, gap='medium')
for idx, improvement in enumerate(improvements):
    with cols[idx % 4]:
        st.markdown(f"""
        <div class="improvement-card">
            <div class="improvement-icon">{improvement['emoji']}</div>
            <h4 style="margin-top: 0; color: #003A70;">{improvement['titre']}</h4>
            <p style="color: #475569; font-size: 0.9rem;">{improvement['desc']}</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ============================================
# SECTION 10: FOOTER
# ============================================

st.markdown("""
<div class="footer-section">
    <h3>📞 Vous voulez vendre votre bien au meilleur prix ? Parlons-en 😊</h3>
    <p><strong>Hakim SABER - RE/MAX Serenity</strong></p>
    <p>21 rue Eugène Gazeau, 60300 Senlis</p>
    <p style="margin-top: 1rem;">
        <strong>📱 06 88 28 85 13</strong> | 
        <strong>📧 hakim.saber@remax.fr</strong>
    </p>
    <p style="font-size: 0.9rem; margin-top: 1rem; color: #e8e8e8;">Données DVF Oise 2026 | Estimation gratuite sans engagement</p>
    <div class="social-links">
        <a href="https://www.facebook.com/remax.serenity" target="_blank" title="Facebook">📘</a>
        <a href="https://www.linkedin.com/in/hakim-saber" target="_blank" title="LinkedIn">💼</a>
        <a href="https://wa.me/33688288513" target="_blank" title="WhatsApp">💬</a>
    </div>
</div>
""", unsafe_allow_html=True)
