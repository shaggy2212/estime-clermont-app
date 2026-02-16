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

# Couleurs
PRIMARY = "#004D7F"
ACCENT = "#FF7E79"

# CSS personnalisé LÉGER (compatible iframe)
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

* {{
    font-family: 'Poppins', sans-serif !important;
}}

.main {{
    background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
}}

h1 {{
    color: {PRIMARY} !important;
    font-weight: 700 !important;
    font-size: 2.5rem !important;
    text-align: center !important;
}}

h2 {{
    color: {PRIMARY} !important;
    font-weight: 600 !important;
}}

.metric-card {{
    background: linear-gradient(135deg, {ACCENT} 0%, #ff5b66 100%);
    color: white !important;
    border-radius: 12px;
    padding: 1.2rem;
    box-shadow: 0 4px 15px rgba(255, 126, 121, 0.25);
    text-align: center;
}}

.metric-card h3 {{
    color: white !important;
    font-size: 0.75rem !important;
    margin-bottom: 0.5rem !important;
    font-weight: 500 !important;
}}

.metric-card h2 {{
    color: white !important;
    font-size: 1.4rem !important;
    margin: 0 !important;
    font-weight: 700 !important;
}}

.info-box {{
    background: linear-gradient(135deg, #e8f0ff 0%, #f0f4ff 100%);
    border-left: 4px solid {PRIMARY};
    border-radius: 8px;
    padding: 1rem;
}}

.algorithm-card {{
    background: linear-gradient(135deg, #fff5f0 0%, #ffe8e0 100%);
    border-left: 4px solid {ACCENT};
    border-radius: 12px;
    padding: 1.2rem;
    box-shadow: 0 4px 15px rgba(255, 126, 121, 0.15);
}}

.algorithm-card h4 {{
    color: {ACCENT} !important;
    margin-top: 0 !important;
    font-size: 1rem !important;
}}

.algorithm-card ul {{
    margin: 0.8rem 0;
    padding-left: 1.2rem;
}}

.algorithm-card li {{
    margin: 0.4rem 0;
    color: {PRIMARY};
    font-size: 0.9rem;
}}

.stButton > button {{
    background: linear-gradient(135deg, {ACCENT} 0%, #ff5b66 100%) !important;
    color: white !important;
    font-weight: 900 !important;
    border-radius: 10px !important;
    border: none !important;
    padding: 1.5rem 3rem !important;
    font-size: 1.3rem !important;
    box-shadow: 0 4px 15px rgba(255, 126, 121, 0.35);
}}

.stButton > button:hover {{
    box-shadow: 0 6px 20px rgba(255, 126, 121, 0.45);
}}

.success-box {{
    background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
    border-left: 4px solid #28a745;
    border-radius: 8px;
    padding: 1.2rem;
    color: #155724;
}}

.error-box {{
    background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
    border-left: 4px solid #dc3545;
    border-radius: 8px;
    padding: 1.2rem;
    color: #721c24;
}}

.advantage-card {{
    background: white;
    border-radius: 12px;
    padding: 1.2rem;
    box-shadow: 0 4px 15px rgba(0, 77, 127, 0.1);
    border-top: 4px solid {ACCENT};
}}

.form-container {{
    max-width: 600px;
    margin: 0 auto;
}}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SECTION : AVANTAGES + ALGORITHME
# ============================================================

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
    st.markdown(f"""
    <div class="algorithm-card">
        <h4>🧠 Algorithme Affiné (3 Niveaux)</h4>
        <ul>
            <li><strong>Niveau 1:</strong> Base DVF 2026 (données officielles)</li>
            <li><strong>Niveau 2:</strong> Biens similaires (dernières ventes)</li>
            <li><strong>Niveau 3:</strong> Facteurs de localisation</li>
        </ul>
        <p style="color: {ACCENT}; font-weight: 600; margin-top: 0.8rem; font-size: 0.85rem;">
        🎯 Résultat: Un prix représentatif du marché local
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# SECTION : FORMULAIRE (RÉDUIT EN LARGEUR)
# ============================================================

st.markdown('<div class="form-container">', unsafe_allow_html=True)
st.markdown("## 📋 Décrivez votre bien")

st.markdown("### 🏠 Caractéristiques")
col1, col2 = st.columns(2, gap='medium')
with col1:
    bien_type = st.selectbox('Type de bien', ['🏠 Maison', '🏢 Appartement'])
    surface = st.number_input('Surface (m²)', min_value=10, max_value=500, value=100)
with col2:
    nb_pieces = st.number_input('Nombre de pièces', min_value=1, max_value=10, value=3)
    nb_chambres = st.number_input('Nombre de chambres', min_value=0, max_value=10, value=2)

etat = st.selectbox('État du bien', ['À rénover', 'Moyen', 'Bon', 'Rénové'], index=1)

st.markdown("### 📍 Localisation")
col1, col2 = st.columns(2, gap='medium')
with col1:
    adresse = st.text_input('Adresse complète du bien', placeholder='Ex: 3 Rue Émile Bousseau')
with col2:
    code_postal = st.text_input('Code postal', value='60600')

distance_gare = st.number_input('Distance à la gare (m)', 0, 5000, 1000, step=100)

st.markdown("### 👤 Vos coordonnées")
col1, col2 = st.columns(2, gap='medium')
with col1:
    prenom = st.text_input('Votre prénom')
    email = st.text_input('Votre email')
with col2:
    telephone = st.text_input('Votre téléphone')
    ville = st.text_input('Ville', value='Clermont')

st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# SECTION : BOUTON CTA + LOGIQUE D'ESTIMATION
# ============================================================

col_button = st.columns([0.15, 0.7, 0.15])
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
            {'surface': 85, 'pieces': 3, 'chambres': 1, 'etat': 'Bon', 'prix_total': 168000, 'type': 'Maison', 'quartier': 'Nord', 'date_vente': '2025-10'},
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
            facteur_etat = {'À rénover': 0.85, 'Moyen': 1.0, 'Bon': 1.06, 'Rénové': 1.12}[etat]
            facteur_chambres = 1 + (nb_chambres - 2) * 0.05
            facteur_gare = 1 + min(0.08, 0.5 / (1 + distance_gare / 1000))
            
            prix_total = prix_m2 * surface * facteur_pieces * facteur_etat * facteur_chambres * facteur_gare
            fourchette_min = prix_total * 0.94
            fourchette_max = prix_total * 1.06
            prix_m2_final = prix_m2 * facteur_pieces * facteur_etat * facteur_chambres * facteur_gare
            
            return {
                'Prix estimé': f"{prix_total:,.0f}€".replace(',', ' '),
                'Fourchette': f"{fourchette_min:,.0f}€ - {fourchette_max:,.0f}€".replace(',', ' '),
                'Prix m²': f"{prix_m2_final:,.0f}€".replace(',', ' '),
                'Quartier': quartier,
                'Détails': f"Quartier: {quartier} | Base DVF: {prix_m2_base}€/m² | Similaires: {len(similaires_filtres)} bien(s) | État: {etat}"
            }
        
        if adresse and telephone and email and prenom:
            mois = '2026-02'
            result = estimer_prix_affinee(bien_type, surface, nb_pieces, nb_chambres, etat, distance_gare, mois)
            
            st.markdown(f"## ✨ Votre estimation - Référence: {mois}")
            
            col_a, col_b = st.columns(2, gap='medium')
            with col_a:
                st.markdown(f'<div class="metric-card"><h3>Valeur estimée</h3><h2>{result["Prix estimé"]}</h2></div>', unsafe_allow_html=True)
            with col_b:
                st.markdown(f'<div class="metric-card"><h3>Prix/m²</h3><h2>{result["Prix m²"]}</h2></div>', unsafe_allow_html=True)
            
            st.markdown(f'<div class="metric-card"><h3>Fourchette</h3><h2>{result["Fourchette"]}</h2></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box"><strong>🎯 Détails :</strong> {result["Détails"]}</div>', unsafe_allow_html=True)
            st.balloons()
            
            st.markdown(f"""
            <div class="success-box">
                <h3>✅ Estimation reçue, {prenom} !</h3>
                <p><strong>Je vais vous appeler dans les 24h/48h pour :</strong></p>
                <ul>
                    <li>Une <strong>estimation plus précise</strong> de votre bien</li>
                    <li>Des <strong>conseils personnalisés</strong> pour mettre en avant votre bien</li>
                    <li>Une <strong>stratégie adaptée</strong> pour {ville}</li>
                </ul>
                <p><strong>📞 {telephone} | 📧 {email} | 📍 {adresse}</strong></p>
            </div>
            """, unsafe_allow_html=True)
            
            st.session_state.contact = {'prenom': prenom, 'adresse': adresse, 'email': email, 'tel': telephone, 'ville': ville, 'estimation': result}
        else:
            st.markdown('<div class="error-box"><strong>⚠️ Attention !</strong> Veuillez remplir tous les champs (prénom, adresse, téléphone, email)</div>', unsafe_allow_html=True)
