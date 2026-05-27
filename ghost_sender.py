"""
ghost_sender.py — Ajoute un contact comme membre Ghost via l'Admin API.
À placer à côté de app.py et email_sender.py dans le repo GitHub.
"""

import time
import jwt
import requests
import streamlit as st


def add_to_ghost(email: str, prenom: str = "", note: str = "") -> bool:
    """
    Ajoute (ou met à jour) un membre dans Ghost via l'Admin API.
    - email   : adresse email du contact (obligatoire)
    - prenom  : prénom du contact (optionnel mais recommandé)
    - note    : note interne attachée au membre (optionnel)

    Retourne True si OK, False sinon.
    Stocke le résultat dans st.session_state pour le debug.
    """
    try:
        admin_api_url = st.secrets.get("GHOST_ADMIN_URL", "").rstrip("/")
        admin_api_key = st.secrets.get("GHOST_ADMIN_KEY", "")

        if not admin_api_url or not admin_api_key:
            st.session_state["_ghost_result"] = False
            st.session_state["_ghost_error"]  = (
                f"Secrets manquants — GHOST_ADMIN_URL={'OK' if admin_api_url else 'VIDE'}, "
                f"GHOST_ADMIN_KEY={'OK' if admin_api_key else 'VIDE'}"
            )
            return False

        # La clé Admin Ghost a le format "id:secret"
        if ":" not in admin_api_key:
            st.session_state["_ghost_result"] = False
            st.session_state["_ghost_error"]  = "GHOST_ADMIN_KEY mal formatée (doit contenir 'id:secret')"
            return False

        key_id, secret = admin_api_key.split(":", 1)

        # Génération du token JWT (valable 5 minutes, audience = /admin/)
        iat = int(time.time())
        token = jwt.encode(
            payload = {
                "iat": iat,
                "exp": iat + 5 * 60,
                "aud": "/admin/",
            },
            key       = bytes.fromhex(secret),
            algorithm = "HS256",
            headers   = {"kid": key_id, "alg": "HS256", "typ": "JWT"},
        )

        # Construction du payload du membre
        name = (prenom or "").strip() or email.split("@")[0]
        member_payload = {
            "members": [{
                "email": email,
                "name":  name,
                "note":  note or "Inscrit via ICOstim",
                "subscribed": True,
                "labels": [{"name": "ICOstim", "slug": "icostim"}],
            }]
        }

        # Appel API Ghost
        endpoint = f"{admin_api_url}/ghost/api/admin/members/"
        headers  = {
            "Authorization": f"Ghost {token}",
            "Content-Type":  "application/json",
        }

        r = requests.post(endpoint, json=member_payload, headers=headers, timeout=15)

        # Si le membre existe déjà, Ghost renvoie 422 — on considère ça comme un succès
        # (le contact est bien dans Ghost, juste pas créé à nouveau)
        if r.status_code in (200, 201):
            st.session_state["_ghost_result"]   = True
            st.session_state["_ghost_error"]    = ""
            st.session_state["_ghost_response"] = f"Status {r.status_code} — Membre créé"
            return True
        elif r.status_code == 422 and "already exists" in r.text.lower():
            st.session_state["_ghost_result"]   = True
            st.session_state["_ghost_error"]    = ""
            st.session_state["_ghost_response"] = f"Status {r.status_code} — Membre déjà existant (OK)"
            return True
        else:
            st.session_state["_ghost_result"]   = False
            st.session_state["_ghost_response"] = f"Status {r.status_code} — {r.text[:400]}"
            st.session_state["_ghost_error"]    = r.text[:200]
            return False

    except Exception as e:
        st.session_state["_ghost_result"] = False
        st.session_state["_ghost_error"]  = str(e)
        return False
