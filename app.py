import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title='EstimeClermont', page_icon='🏠', layout='wide')

st.image('https://i.imgur.com/r7P0dbK.png', width=200, caption='RE/MAX Serenity')

st.title("🏠 Estimation gratuite de mon logement à Clermont de l'Oise")

col_photo1, col_photo2 = st.columns([1, 3])
with col_photo1:
    st.image('https://i.imgur.com/KsQopoC.jpeg', width=150, caption='Hakim SABER')
with col_photo2:
    st.markdown("***Hakim SABER - Agence RE/MAX Serenity***")
    st.markdown("📍 21 rue Eugène Gazeau, 60300 Senlis")
    st.markdown("📞 Contactez-moi pour estimation précise")

st.markdown("### Pourquoi choisir notre estimation ?")
cols = st.columns(3)
with cols[0]:
    st.info("✅ **Locale à Clermont**")
    st.caption("Données précises quartier par quartier (DVF 2026)")
with cols[1]:
    st.info("⚡ **Retour immédiat**")
    st.caption("Résultat en 30 secondes")
with cols[2]:
    st.info("💡 **Conseils personnalisés**")
    st.caption("Astuces pour mettre en avant votre bien")

st.markdown("---")

prix_m2_maison = 2100
prix_m2_appart = 2500
tendances_mensuelles = {'2026-01': 1.02, '2026-02': 1.01, '2026-03': 1.015, '2026-04': 1.00, '2026-05': 1.01, '2026-06': 1.02, '2026-07': 1.00, '2026-08': 1.00, '2026-09': 1.01, '2026-10': 1.015, '2026-11': 1.01, '2026-12': 1.02}

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
    return {'Prix estimé': f"€{prix_total:,.0f}", 'Fourchette': f"€{fourchette_min:,.0f} - €{fourchette_max:,.0f}", 'Prix m²': f"€{prix_ajuste * facteur_pieces * facteur_etat * facteur_chambres * facteur_gare:,.0f}", 'Détails': f"{mois}: {prix_base}€/m² base ×{facteur_mois:.1%}, {nb_pieces}p, {nb_chambres}ch, {etat}, gare{distance_gare}m"}

st.markdown("### Décrivez votre bien")
col1, col2 = st.columns(2)

with col1:
    bien_type = st.selectbox('Type de bien', ['maison', 'appart'])
    surface = st.number_input('Surface (m²)', min_value=10, max_value=500, value=100)
    nb_pieces = st.number_input('Nombre de pièces', min_value=1, max_value=10, value=3)
    nb_chambres = st.number_input('Nombre de chambres', min_value=0, max_value=10, value=2)

with col2:
    adresse = st.text_input('Adresse complète du bien')
    email = st.text_input('Votre email')
    code_postal = st.text_input('Code postal', value='60600')
    ville = st.text_input('Ville', value='Clermont')

telephone = st.text_input('Votre téléphone', help='Pour estimation précise et conseils')
etat = st.selectbox('État général du bien', ['à rénover', 'à rafraichir', 'moyen', 'rénové'], index=2)

distance_gare = st.number_input('Distance à la gare la plus proche (m)', 0, 5000, 1000, step=100)

mois = st.selectbox('Mois référence', sorted(tendances_mensuelles.keys()), index=0)

if st.button('🚀 Obtenir mon estimation gratuite !', type='primary'):
    if adresse and telephone and email:
        result = estimer_prix(bien_type, surface, nb_pieces, nb_chambres, etat, distance_gare, mois)
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Valeur estimée", result['Prix estimé'])
        with col_b:
            st.metric("Fourchette", result['Fourchette'])
        with col_c:
            st.metric("Prix/m²", result['Prix m²'])
        st.info(f"**Détails calcul :** {result['Détails']}")
        st.balloons()
        st.success(f"""
✅ **Estimation reçue !**

Hakim vous appelle dans les **24h** pour :
- Une **estimation plus précise** sur site
- Des **conseils personnalisés** pour mettre en avant votre bien
- Une stratégie adaptée pour {ville} ({code_postal})

📞 {telephone} | 📧 {email} | 📍 {adresse}
        """)
        st.session_state.contact = {'adresse': adresse, 'email': email, 'tel': telephone, 'ville': ville, 'estimation': result}
    else:
        st.error("⚠️ Veuillez remplir adresse, téléphone et email pour résultat personnalisé")

st.markdown("---")
st.markdown("*Données DVF Oise 2026 | Hakim SABER - RE/MAX Serenity Senlis*")
st.markdown("*21 rue Eugène Gazeau, 60300 Senlis*")
