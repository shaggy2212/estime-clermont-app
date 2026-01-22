import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title='EstimeClermont', page_icon='🏠', layout='wide')

# Logo RE/MAX
st.image('https://i.imgur.com/r7P0dbK.png', width=200, caption='RE/MAX Serenity')

st.title("🏠 Estimation gratuite de mon logement à Clermont de l'Oise")
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
tendances_mensuelles = {
    '2026-01': 1.02,
    '2026-02': 1.01,
    '2026-03': 1.015,
    '2026-04': 1.00,
    '2026-05': 1.01,
    '2026-06': 1.02,
    '2026-07': 1.00,
    '2026-08': 1.00,
    '2026-09': 1.01,
    '2026-10': 1.015,
    '2026-11': 1.01,
    '2026-12': 1.02
}

def estimer_prix(bien_type, surface
