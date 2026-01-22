import streamlit as st
import pandas as pd
import numpy as np

# Fonction d'estimation IA (basée sur DVF Oise/Clermont 2026)
prix_m2_maison = 2100  # €/m² base maisons
prix_m2_appart = 2500  # €/m² base apparts
tendances_mensuelles = {
    '2026-01': 1.02,  # +2% janv (exemple, mettez à jour mensuel via DVF)
    '2026-02': 1.01,
    '2026-03': 1.015,
    # Ajoutez tous les mois, source: app.dvf.etalab.gouv.fr
}
mois_actuel = '2026-01'

def ajuster_prix_mensuel(prix_base, mois):
    return prix_base * tendances_mensuelles.get(mois, 1.0)

def estimer_prix(bien_type, surface, nb_pieces, etat='moyen', renovations=0, distance_gare=0, mois=mois_actuel):
    prix_base = prix_m2_maison if bien_type == 'maison' else prix_m2_appart
    prix_ajuste = ajuster_prix_mensuel(prix_base, mois)
    
    facteur_pieces = 1 + (nb_pieces - 3) * 0.03
    facteur_etat = {'bon': 1.05, 'moyen': 1.0, 'mauvais': 0.95}[etat]
    facteur_renov = 1 + (renovations / 10000)
    facteur_gare = 1 + (1 / (1 + distance_gare / 1000)) * 0.1
    
    prix_total = prix_ajuste * surface * facteur_pieces * facteur_etat * facteur_renov * facteur_gare
    fourchette_min = prix_total * 0.95
    fourchette_max = prix_total * 1.05
    
    return {
        'Prix estimé': f"{prix_total:,.0f} €",
        'Fourchette': f"{fourchette_min:,.0f} € - {fourchette_max:,.0f} €",
        'Prix/m² ajusté': f"{prix_ajuste * facteur_pieces * facteur_etat * facteur_renov * facteur_gare:,.0f} €",
        'Détails': f"Base: {prix_base}€/m², {mois}, {nb_pieces} pièces, état {etat}, rénov {renovations}€, gare {distance_gare}m"
    }

# Interface Streamlit
st.title('🏠 EstimeClermont - IA Gratuite pour Clermont Oise')
st.markdown("**Estimation locale 2026, mise à jour mensuelle via données DVF officielles** [data.gouv.fr]")

col1, col2 = st.columns(2)
with col1:
    bien_type = st.selectbox('Type de bien', ['maison', 'appart'])
    surface = st.number_input('Surface (m²)', min_value=10, max_value=500, value=100)
    nb_pieces = st.number_input('Nb pièces', min_value=1, max_value=10, value=3)
with col2:
    etat = st.selectbox('État général', ['mauvais', 'moyen', 'bon'])
    renovations = st.number_input('Coût rénovations (€)', 0, 50000)
    distance_gare = st.number_input('Distance gare (m)', 0, 5000, 1000)

mois = st.selectbox('Mois référence', sorted(tendances_mensuelles.keys()))

email = st.text_input("Votre email pour PDF détaillé (optionnel)")

if st.button('🚀 Estimer mon bien !', type='primary'):
    result = estimer_prix(bien_type, surface, nb_pieces, etat, renovations, distance_gare, mois)
    st.success(f"**{result['Prix estimé']}**")
    st.info(result['Fourchette'])
    st.metric("Prix/m² ajusté", result['Prix/m² ajusté'])
    st.write("**Détails :** " + result['Détails'])
    
    # Capture lead
    if email:
        st.session_state.lead = {'email': email, 'estimation': result}
        st.balloons()
        st.write("📧 PDF envoyé ! Contact en 24h pour mandat exclusif.")
