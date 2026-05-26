"""
email_sender.py — Envoi de l'email d'estimation via Brevo SMTP
À placer à côté de app.py dans le repo GitHub.
"""

import smtplib
import streamlit as st
from email.message import EmailMessage
from string import Template


# ===========================
# Helpers
# ===========================
def _fmt_int(x) -> str:
    """Formate un nombre avec espace fine comme séparateur de milliers (ex: 132 206)."""
    try:
        return f"{int(float(x)):,}".replace(",", "\u202f")
    except Exception:
        return "—"


# ===========================
# Template HTML (placeholders $var)
# ===========================
EMAIL_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Votre estimation immobilière</title>
</head>
<body style="margin:0; padding:0; background-color:#f0f4f8; font-family:'Georgia', serif;">

  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f0f4f8; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px; width:100%;">

          <!-- HEADER -->
          <tr>
            <td style="background-color:#063970; border-radius:20px 20px 0 0; padding: 40px 48px 36px; text-align:center;">
              <p style="margin:0 0 8px 0; font-family:Arial, sans-serif; font-size:13px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:rgba(255,255,255,0.55);">ICOstim</p>
              <h1 style="margin:0; font-family:Georgia, serif; font-size:32px; font-weight:700; color:#ffffff; line-height:1.2;">✨ Votre estimation<br>est prête</h1>
              <p style="margin:16px 0 0; font-family:Arial, sans-serif; font-size:15px; color:rgba(255,255,255,0.75); line-height:1.6;">Bonjour <strong style="color:white;">$prenom</strong>, voici les résultats de votre estimation basée sur les ventes réelles de votre secteur.</p>
            </td>
          </tr>

          <!-- ADRESSE -->
          <tr>
            <td style="background-color:#FF7E79; padding: 14px 48px; text-align:center;">
              <p style="margin:0; font-family:Arial, sans-serif; font-size:13px; font-weight:700; color:white; letter-spacing:0.05em;">📍 $adresse</p>
            </td>
          </tr>

          <!-- MAIN CARD -->
          <tr>
            <td style="background-color:#ffffff; padding: 40px 48px 32px;">

              <!-- Fourchette -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background: linear-gradient(135deg, #063970, #0a5cb8); border-radius:16px; margin-bottom:24px;">
                <tr>
                  <td style="padding: 28px 32px; text-align:center;">
                    <p style="margin:0 0 6px; font-family:Arial, sans-serif; font-size:11px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:rgba(255,255,255,0.6);">Fourchette estimée</p>
                    <p style="margin:0; font-family:Georgia, serif; font-size:34px; font-weight:700; color:#ffffff; letter-spacing:-0.02em;">$est_min € – $est_max €</p>
                    <p style="margin:10px 0 0; font-family:Arial, sans-serif; font-size:13px; color:rgba(255,255,255,0.65);">Basée sur les ventes réelles DVF · $bien_type · $surface m²</p>
                  </td>
                </tr>
              </table>

              <!-- 2 métriques -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:28px;">
                <tr>
                  <td width="48%" style="background-color:#f8fafc; border-radius:12px; padding:20px 20px; text-align:center; border:2px solid #e2e8f0;">
                    <p style="margin:0 0 4px; font-family:Arial, sans-serif; font-size:10px; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; color:#94a3b8;">Prix médian au m²</p>
                    <p style="margin:0; font-family:Georgia, serif; font-size:22px; font-weight:700; color:#063970;">$pm2 €<span style="font-size:14px; font-weight:400;">/m²</span></p>
                  </td>
                  <td width="4%"></td>
                  <td width="48%" style="background-color:#fff7f7; border-radius:12px; padding:20px 20px; text-align:center; border:2px solid #ffd4d2;">
                    <p style="margin:0 0 4px; font-family:Arial, sans-serif; font-size:10px; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; color:#94a3b8;">Attractivité du secteur</p>
                    <p style="margin:0; font-family:Georgia, serif; font-size:16px; font-weight:700; color:#FF7E79; line-height:1.3;">$attractivite</p>
                  </td>
                </tr>
              </table>

              <!-- Fiabilité -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:32px;">
                <tr>
                  <td style="background-color:#f0f9ff; border-radius:12px; padding:16px 20px; border-left:4px solid #063970;">
                    <p style="margin:0; font-family:Arial, sans-serif; font-size:13px; color:#334155; line-height:1.5;"><strong style="color:#063970;">Fiabilité des données :</strong> $fiabilite</p>
                  </td>
                </tr>
              </table>

              <hr style="border:none; border-top:2px dashed #e2e8f0; margin:0 0 28px;">

              <p style="margin:0 0 12px; font-family:Georgia, serif; font-size:17px; font-style:italic; color:#64748b; line-height:1.6;">Estimer votre bien à distance, c'est bien. Le voir en vrai, c'est mieux. 😃</p>
              <p style="margin:0 0 24px; font-family:Arial, sans-serif; font-size:14px; color:#475569; line-height:1.7;">Cette fourchette est basée sur de vraies ventes, c'est solide. Mais pour un chiffre vraiment précis et des conseils adaptés à votre projet, rien ne vaut un vrai échange.</p>

              <!-- CTA -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center">
                    <a href="https://hakimremax.youcanbook.me/" style="display:inline-block; background-color:#FF7E79; color:#ffffff; font-family:Arial, sans-serif; font-size:16px; font-weight:700; text-decoration:none; padding:18px 40px; border-radius:14px; letter-spacing:0.02em;">📞 Réserver un appel avec Hakim →</a>
                  </td>
                </tr>
              </table>

              <p style="margin:16px 0 0; font-family:Arial, sans-serif; font-size:12px; color:#94a3b8; text-align:center;">Un échange téléphonique de 20 minutes · Gratuit · Sans engagement</p>

            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color:#f8fafc; border-radius:0 0 20px 20px; padding:32px 48px; border-top:2px solid #e2e8f0;">

              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:24px;">
                <tr>
                  <td width="64" style="vertical-align:middle; padding-right:16px;">
                    <img src="https://i.imgur.com/bPfH4jv.jpeg" width="56" height="56" alt="Hakim" style="border-radius:50%; display:block; border:3px solid #FF7E79; object-fit:cover;">
                  </td>
                  <td style="vertical-align:middle;">
                    <p style="margin:0 0 2px; font-family:Arial, sans-serif; font-size:15px; font-weight:700; color:#063970;">Hakim Saber</p>
                    <p style="margin:0 0 2px; font-family:Arial, sans-serif; font-size:12px; color:#64748b; font-weight:600;">Conseiller Immobilier RE/MAX</p>
                    <p style="margin:0; font-family:Arial, sans-serif; font-size:12px; color:#94a3b8;">Fondateur de <a href="https://immoclermontoise.fr" style="color:#FF7E79; text-decoration:none;">immoclermontoise.fr</a></p>
                  </td>
                </tr>
              </table>

              <hr style="border:none; border-top:1px solid #e2e8f0; margin:0 0 24px;">

              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px;">
                <tr>
                  <td align="left" style="vertical-align:middle;">
                    <img src="https://i.imgur.com/s1HfxcK.png" height="36" alt="ICOstim" style="display:inline-block;">
                  </td>
                  <td align="right" style="vertical-align:middle;">
                    <img src="https://i.imgur.com/x7KZrNm.png" height="36" alt="RE/MAX" style="display:inline-block;">
                  </td>
                </tr>
              </table>

              <p style="margin:0; font-family:Arial, sans-serif; font-size:11px; color:#cbd5e1; text-align:center; line-height:1.6;">Vous recevez cet email car vous avez utilisé l'outil ICOstim sur immoclermontoise.fr.<br>Pour ne plus en recevoir, répondez simplement "stop" à cet email.</p>

            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>""")


# ===========================
# Fonction principale d'envoi
# ===========================
def send_estimation_email(
    to_email: str,
    prenom: str,
    adresse: str,
    bien_type: str,
    surface: float,
    est_min: float,
    est_max: float,
    pm2: float,
    fiabilite: str,
    attractivite: str,
) -> bool:
    """
    Envoie l'email d'estimation au client via Brevo SMTP.
    Retourne True si envoi OK, False sinon.
    En cas d'erreur, le message est stocké dans st.session_state["_brevo_error"].
    """
    try:
        # Lecture des secrets
        host       = st.secrets["BREVO_SMTP_HOST"]
        port       = int(st.secrets["BREVO_SMTP_PORT"])
        user       = st.secrets["BREVO_SMTP_USER"]
        pwd        = st.secrets["BREVO_SMTP_PASS"]
        from_email = st.secrets["BREVO_FROM_EMAIL"]
        from_name  = st.secrets["BREVO_FROM_NAME"]
        bcc_email  = st.secrets.get("BREVO_BCC_EMAIL", "")  # optionnel : copie pour Hakim

        # Construction du HTML avec les vraies données
        html = EMAIL_TEMPLATE.substitute(
            prenom       = prenom or "",
            adresse      = adresse or "",
            bien_type    = bien_type or "",
            surface      = int(float(surface or 0)),
            est_min      = _fmt_int(est_min),
            est_max      = _fmt_int(est_max),
            pm2          = _fmt_int(pm2),
            fiabilite    = fiabilite or "—",
            attractivite = attractivite or "—",
        )

        # Construction du message
        msg = EmailMessage()
        msg["Subject"] = f"✨ Votre estimation pour {adresse}"
        msg["From"]     = f"{from_name} <{from_email}>"
        msg["To"]       = to_email
        msg["Reply-To"] = from_email
        if bcc_email:
            msg["Bcc"] = bcc_email

        # Fallback texte pour les clients qui n'affichent pas le HTML
        msg.set_content(
            f"Bonjour {prenom},\n\n"
            f"Votre estimation pour {adresse} est prête :\n"
            f"Fourchette : {_fmt_int(est_min)} € à {_fmt_int(est_max)} €\n"
            f"Prix médian au m² : {_fmt_int(pm2)} €/m²\n"
            f"Fiabilité : {fiabilite}\n"
            f"Attractivité du secteur : {attractivite}\n\n"
            f"Pour affiner cette estimation, réservez un appel : https://hakimremax.youcanbook.me/\n\n"
            f"Hakim — ImmoClermontOise"
        )
        msg.add_alternative(html, subtype="html")

        # Envoi SMTP
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(user, pwd)
            server.send_message(msg)

        st.session_state["_brevo_result"] = True
        st.session_state["_brevo_error"]  = ""
        return True

    except Exception as e:
        st.session_state["_brevo_result"] = False
        st.session_state["_brevo_error"]  = str(e)
        return False
