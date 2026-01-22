import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="EstimeClermont", page_icon="🏠", layout="wide")

# Logo RE/MAX (uploadez icons8-remax-1000.jpeg dans repo GitHub)
if 'logo' in st.session_state:
    st.image(st.session_state.logo, width=200)
else:
    st.markdown("![RE/MAX Serenity](https://icons8-remax ou hébergez votre logo)")

st.title("🏠 Estimation gratuite de mon logement à Clermont de l'Oise")
st.markdown("**Hakim SABER - Agence RE/MAX Serenity**")
st.markdown("📍 21 rue Eugène Gazeau, 60300 Senlis | 📞 [Votre numéro téléphone]")

## Avantages
st.markdown("### Pourquoi estimer avec nous ?")
cols = st.columns(3)
with cols[0]:
    st.success("✅ **Locale Clermont**")
    st.caption("Données précises quartier par quartier")
with cols[1]:
    st.success("⚡ **Immédiate**")
    st.caption("Résultat en 30 secondes")
with cols[2]:
    st.success("💡 **Conseils perso**")
    st.caption("Astuces pour booster votre prix")

st.markdown("**Estimation locale 2026, mise à jour mensuelle via DVF officielles**")

# Formulaire étendu
col1, col2 = st.columns(2)
with col1:
    bien_type = st.selectbox('Type de bien', ['maison', 'appart'])
    surface = st.number_input('Surface (m²)', min_value=10, max_value=500, value=100)
    nb_pieces = st.number_input('Nb pièces', min_value=1, max_value=10, value=
