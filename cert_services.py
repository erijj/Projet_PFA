"""
SmartCert — cert_services.py
Deux services indépendants :
  1. generate_certificate_pdf(cert: dict) -> BytesIO
  2. send_certificate_email(cert: dict, pdf_bytes: BytesIO) -> bool
"""

import io
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email              import encoders
from datetime           import datetime

# ── ReportLab ────────────────────────────────────────────
from reportlab.lib.pagesizes   import A4
from reportlab.lib             import colors
from reportlab.lib.units       import mm
from reportlab.pdfgen          import canvas
from reportlab.lib.utils       import ImageReader

# ─── EMAIL CONFIG ─────────────────────────────────────────
# Remplir dans .env ou variables d'environnement
SMTP_HOST     = os.getenv('SMTP_HOST',     'smtp.gmail.com')
SMTP_PORT     = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER     = os.getenv('SMTP_USER',     'smartcert.noreply@gmail.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')          # App Password Gmail
FROM_NAME     = os.getenv('FROM_NAME',     'SmartCert')

# ─── PALETTE (reprend les couleurs du projet) ─────────────
C_NAVY   = colors.HexColor('#001D39')
C_BLUE1  = colors.HexColor('#0A4174')
C_TEAL   = colors.HexColor('#4E8EA2')
C_ACCENT = colors.HexColor('#7BBDE8')
C_PALE   = colors.HexColor('#BDD8E9')
C_WHITE  = colors.white
C_GREEN  = colors.HexColor('#10b981')
C_GOLD   = colors.HexColor('#C8A84B')

# ═══════════════════════════════════════════════════════════
#  1. GÉNÉRATION PDF
# ═══════════════════════════════════════════════════════════

def generate_certificate_pdf(cert: dict) -> io.BytesIO:
    """
    Génère un certificat PDF professionnel à partir des données.

    Paramètres attendus dans cert :
        id, recipient_name, email, program,
        institution, issue_date, status,
        blockchain_hash, tx_hash

    Retourne un BytesIO contenant le PDF.
    """
    buffer = io.BytesIO()
    W, H   = A4                        # 595 x 842 pts
    c      = canvas.Canvas(buffer, pagesize=A4)

    _draw_background(c, W, H)
    _draw_border(c, W, H)
    _draw_header(c, W, H)
    _draw_body(c, W, H, cert)
    _draw_blockchain_footer(c, W, H, cert)
    _draw_decorations(c, W, H)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# ── Couches graphiques ────────────────────────────────────

def _draw_background(c, W, H):
    """Fond dégradé bleu marine."""
    # Rectangle de fond principal
    c.setFillColor(C_NAVY)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Bande décorative haute
    c.setFillColor(C_BLUE1)
    c.rect(0, H - 110*mm, W, 110*mm, fill=1, stroke=0)

    # Bande décorative basse
    c.setFillColor(C_BLUE1)
    c.rect(0, 0, W, 28*mm, fill=1, stroke=0)

    # Cercle décoratif (haut gauche)
    c.setFillColor(colors.HexColor('#0D3A63'))
    c.circle(0, H, 80*mm, fill=1, stroke=0)

    # Cercle décoratif (bas droit)
    c.circle(W, 0, 60*mm, fill=1, stroke=0)


def _draw_border(c, W, H):
    """Double bordure élégante."""
    margin = 12*mm
    c.setStrokeColor(C_TEAL)
    c.setLineWidth(2)
    c.rect(margin, margin, W - 2*margin, H - 2*margin, fill=0, stroke=1)

    inner = margin + 3*mm
    c.setStrokeColor(C_ACCENT)
    c.setLineWidth(0.5)
    c.rect(inner, inner, W - 2*inner, H - 2*inner, fill=0, stroke=1)


def _draw_header(c, W, H):
    """En-tête : logo texte + titre principal."""
    # ── Logo SmartCert ──────────────────────────────
    logo_x, logo_y = W/2, H - 38*mm
    # Cercle fond logo
    c.setFillColor(C_TEAL)
    c.circle(logo_x, logo_y, 14*mm, fill=1, stroke=0)
    # Texte "SC" centré
    c.setFillColor(C_WHITE)
    c.setFont('Helvetica-Bold', 18)
    c.drawCentredString(logo_x, logo_y - 3*mm, 'SC')

    # ── Nom de l'institution ─────────────────────────
    c.setFillColor(C_PALE)
    c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(W/2, H - 58*mm, 'SMARTCERT UNIVERSITY')

    c.setFillColor(C_ACCENT)
    c.setFont('Helvetica', 7)
    c.drawCentredString(W/2, H - 64*mm, 'BLOCKCHAIN CERTIFICATE AUTHORITY  ·  ETHEREUM TESTNET')

    # ── Ligne séparatrice ────────────────────────────
    sep_y = H - 72*mm
    c.setStrokeColor(C_TEAL)
    c.setLineWidth(1)
    c.line(30*mm, sep_y, W - 30*mm, sep_y)

    # ── Titre "CERTIFICAT DE RÉUSSITE" ───────────────
    c.setFillColor(C_WHITE)
    c.setFont('Helvetica-Bold', 22)
    c.drawCentredString(W/2, H - 85*mm, 'CERTIFICAT DE RÉUSSITE')

    c.setFillColor(C_ACCENT)
    c.setFont('Helvetica', 8)
    c.drawCentredString(W/2, H - 92*mm, 'CERTIFICATE OF ACHIEVEMENT')


def _draw_body(c, W, H, cert):
    """Corps du certificat : bénéficiaire, programme, détails."""
    name    = cert.get('recipient_name', '—')
    program = cert.get('program', '—')
    inst    = cert.get('institution', 'SmartCert University')
    date    = (cert.get('issue_date') or '—').split('T')[0]
    status  = cert.get('status', 'Vérifié')
    cert_id = cert.get('id', '—')

    # ── "Certifie que" ───────────────────────────────
    c.setFillColor(C_PALE)
    c.setFont('Helvetica', 10)
    c.drawCentredString(W/2, H - 106*mm, 'Certifie que')

    # ── Nom du bénéficiaire ──────────────────────────
    # Choisir taille de police adaptée à la longueur du nom
    name_font_size = 28 if len(name) <= 25 else (22 if len(name) <= 35 else 18)
    c.setFillColor(C_WHITE)
    c.setFont('Helvetica-Bold', name_font_size)
    c.drawCentredString(W/2, H - 120*mm, name)

    # Ligne sous le nom
    c.setStrokeColor(C_GOLD)
    c.setLineWidth(1.5)
    name_w = c.stringWidth(name, 'Helvetica-Bold', name_font_size)
    c.line(W/2 - name_w/2, H - 123*mm, W/2 + name_w/2, H - 123*mm)

    # ── "a complété avec succès le programme" ────────
    c.setFillColor(C_PALE)
    c.setFont('Helvetica', 9)
    c.drawCentredString(W/2, H - 133*mm, 'a complété avec succès le programme')

    # ── Nom du programme ─────────────────────────────
    prog_font = 16 if len(program) <= 40 else 13
    c.setFillColor(C_ACCENT)
    c.setFont('Helvetica-Bold', prog_font)
    c.drawCentredString(W/2, H - 145*mm, program)

    # ── Institution ──────────────────────────────────
    c.setFillColor(C_PALE)
    c.setFont('Helvetica', 9)
    c.drawCentredString(W/2, H - 155*mm, f'délivré par  {inst}')

    # ── Séparateur ───────────────────────────────────
    sep_y2 = H - 167*mm
    c.setStrokeColor(colors.HexColor('#1A4A6A'))
    c.setLineWidth(1)
    c.line(25*mm, sep_y2, W - 25*mm, sep_y2)

    # ── Grille d'infos (3 colonnes) ──────────────────
    grid_y  = H - 180*mm
    cols    = [W*0.22, W*0.5, W*0.78]   # centres des 3 colonnes
    labels  = ["Date d'émission", "Identifiant", "Statut"]
    values  = [date, cert_id, status]
    v_colors = [C_WHITE, C_ACCENT, C_GREEN if status == 'Vérifié' else C_PALE]

    for cx, lbl, val, vcol in zip(cols, labels, values, v_colors):
        # Label
        c.setFillColor(C_PALE)
        c.setFont('Helvetica', 7)
        c.drawCentredString(cx, grid_y, lbl.upper())
        # Valeur
        c.setFillColor(vcol)
        val_font = 8 if len(val) > 14 else 10
        c.setFont('Helvetica-Bold', val_font)
        c.drawCentredString(cx, grid_y - 7*mm, val)

    # ── Tampon "VÉRIFIÉ" ─────────────────────────────
    stamp_x, stamp_y = W - 50*mm, H - 170*mm
    c.saveState()
    c.translate(stamp_x, stamp_y)
    c.rotate(15)
    c.setStrokeColor(C_GREEN)
    c.setLineWidth(2.5)
    c.setFillColor(colors.HexColor('#0B2E1A'))
    c.roundRect(-22*mm, -8*mm, 44*mm, 16*mm, 4*mm, fill=1, stroke=1)
    c.setFillColor(C_GREEN)
    c.setFont('Helvetica-Bold', 12)
    c.drawCentredString(0, -3*mm, '✓  VÉRIFIÉ')
    c.restoreState()

    # ── Zone signature ────────────────────────────────
    sig_y = H - 210*mm
    sig_x = W * 0.27
    c.setStrokeColor(C_TEAL)
    c.setLineWidth(0.8)
    c.line(sig_x - 28*mm, sig_y, sig_x + 28*mm, sig_y)
    c.setFillColor(C_PALE)
    c.setFont('Helvetica', 7)
    c.drawCentredString(sig_x, sig_y - 5*mm, 'Directeur des Études')
    c.drawCentredString(sig_x, sig_y - 10*mm, inst)

    # Sceau (cercle)
    seal_x = W * 0.73
    c.setStrokeColor(C_TEAL)
    c.setLineWidth(1)
    c.circle(seal_x, sig_y - 5*mm, 15*mm, fill=0, stroke=1)
    c.setFillColor(C_TEAL)
    c.setFont('Helvetica-Bold', 6)
    c.drawCentredString(seal_x, sig_y - 3*mm, 'SCEAU OFFICIEL')
    c.drawCentredString(seal_x, sig_y - 9*mm, 'SMARTCERT')


def _draw_blockchain_footer(c, W, H, cert):
    """Pied de page blockchain : hash + instructions de vérification."""
    bh   = cert.get('blockchain_hash', '')
    txh  = cert.get('tx_hash', '')
    fh   = 18*mm    # hauteur de la zone footer

    # Fond de la zone blockchain
    c.setFillColor(colors.HexColor('#061422'))
    c.rect(15*mm, 15*mm, W - 30*mm, fh, fill=1, stroke=0)
    c.setStrokeColor(C_TEAL)
    c.setLineWidth(0.5)
    c.rect(15*mm, 15*mm, W - 30*mm, fh, fill=0, stroke=1)

    # Icône chaîne
    c.setFillColor(C_ACCENT)
    c.setFont('Helvetica-Bold', 8)
    c.drawString(18*mm, 28*mm, '⛓  BLOCKCHAIN HASH (SHA-256)')

    # Hash tronqué
    c.setFillColor(C_TEAL)
    c.setFont('Helvetica', 6.5)
    hash_display = (bh[:72] + '…') if len(bh) > 72 else bh
    c.drawString(18*mm, 23*mm, hash_display or 'Non disponible')

    # Tx hash
    if txh:
        c.setFillColor(colors.HexColor('#3A6A8A'))
        c.setFont('Helvetica', 6)
        c.drawString(18*mm, 18.5*mm, f'TX: {txh[:60]}')

    # URL vérification (droite)
    c.setFillColor(C_PALE)
    c.setFont('Helvetica', 6.5)
    c.drawRightString(W - 18*mm, 23*mm, 'Vérifiez sur : smartcert.app/verify')
    c.drawRightString(W - 18*mm, 18.5*mm, f'ID : {cert.get("id","—")}')


def _draw_decorations(c, W, H):
    """Éléments décoratifs : coins, lignes."""
    corner = 8*mm
    margin = 12*mm
    c.setStrokeColor(C_GOLD)
    c.setLineWidth(1.5)
    # Coin haut gauche
    c.line(margin, H - margin, margin + corner, H - margin)
    c.line(margin, H - margin, margin, H - margin - corner)
    # Coin haut droit
    c.line(W - margin, H - margin, W - margin - corner, H - margin)
    c.line(W - margin, H - margin, W - margin, H - margin - corner)
    # Coin bas gauche
    c.line(margin, margin, margin + corner, margin)
    c.line(margin, margin, margin, margin + corner)
    # Coin bas droit
    c.line(W - margin, margin, W - margin - corner, margin)
    c.line(W - margin, margin, W - margin, margin + corner)


# ═══════════════════════════════════════════════════════════
#  2. ENVOI EMAIL
# ═══════════════════════════════════════════════════════════

def send_certificate_email(cert: dict, pdf_bytes: io.BytesIO) -> bool:
    """
    Envoie un email HTML au bénéficiaire avec le certificat PDF en pièce jointe.

    Retourne True si l'envoi a réussi, False sinon.
    """
    recipient_email = cert.get('email')
    if not recipient_email:
        print("⚠ Pas d'email — envoi annulé")
        return False

    if not SMTP_PASSWORD:
        print("⚠ SMTP_PASSWORD non configuré — envoi simulé (mode démo)")
        return True   # Simule succès en mode démo

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎓 Votre certificat SmartCert — {cert.get('program', '')}"
        msg['From']    = f"{FROM_NAME} <{SMTP_USER}>"
        msg['To']      = recipient_email

        # ── Corps HTML ────────────────────────────────
        html_body = _build_email_html(cert)
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # ── Pièce jointe PDF ──────────────────────────
        pdf_bytes.seek(0)
        part = MIMEBase('application', 'pdf')
        part.set_payload(pdf_bytes.read())
        encoders.encode_base64(part)
        filename = f"certificat_{cert.get('id', 'smartcert')}.pdf"
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        msg.attach(part)

        # ── Envoi SMTP ────────────────────────────────
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, recipient_email, msg.as_string())

        print(f"✅ Email envoyé → {recipient_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ Erreur SMTP : authentification échouée — vérifiez SMTP_USER et SMTP_PASSWORD")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ Erreur SMTP : {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue lors de l'envoi : {e}")
        return False


def _build_email_html(cert: dict) -> str:
    """Construit le corps HTML de l'email de notification."""
    name    = cert.get('recipient_name', 'Étudiant')
    program = cert.get('program', '—')
    inst    = cert.get('institution', 'SmartCert University')
    date    = (cert.get('issue_date') or '—').split('T')[0]
    cert_id = cert.get('id', '—')
    bh      = cert.get('blockchain_hash', '—')

    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Votre Certificat SmartCert</title>
</head>
<body style="margin:0;padding:0;background:#001D39;font-family:'Segoe UI',Arial,sans-serif">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#001D39;padding:32px 16px">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(135deg,#0A4174,#4E8EA2);border-radius:16px 16px 0 0;padding:36px 32px;text-align:center">
            <div style="width:60px;height:60px;background:rgba(255,255,255,.15);border-radius:50%;margin:0 auto 16px;display:flex;align-items:center;justify-content:center;font-size:28px;line-height:60px">🎓</div>
            <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:800;letter-spacing:-0.5px">SmartCert</h1>
            <p style="margin:6px 0 0;color:#BDD8E9;font-size:12px;letter-spacing:2px;text-transform:uppercase">Blockchain Certificate Authority</p>
          </td>
        </tr>

        <!-- BODY -->
        <tr>
          <td style="background:#0A2E50;padding:36px 32px">

            <p style="margin:0 0 8px;color:#BDD8E9;font-size:14px">Bonjour <strong style="color:#7BBDE8">{name}</strong>,</p>
            <p style="margin:0 0 24px;color:#6EA2B3;font-size:14px;line-height:1.7">
              Félicitations ! Votre certificat numérique a été émis avec succès et enregistré de manière permanente sur la blockchain Ethereum.
            </p>

            <!-- Carte certificat -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#001D39;border:1px solid rgba(78,142,162,0.3);border-radius:12px;overflow:hidden;margin-bottom:24px">
              <tr>
                <td style="background:rgba(16,185,129,0.08);border-bottom:1px solid rgba(16,185,129,0.2);padding:14px 20px">
                  <span style="color:#10b981;font-weight:700;font-size:13px">✅ Certificat Authentique et Vérifié</span>
                </td>
              </tr>
              <tr>
                <td style="padding:20px">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="padding:8px 0;border-bottom:1px solid rgba(78,142,162,0.1)">
                        <span style="color:#6EA2B3;font-size:11px;text-transform:uppercase;letter-spacing:.5px">Bénéficiaire</span><br>
                        <strong style="color:#E8F4FF;font-size:14px">{name}</strong>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:8px 0;border-bottom:1px solid rgba(78,142,162,0.1)">
                        <span style="color:#6EA2B3;font-size:11px;text-transform:uppercase;letter-spacing:.5px">Programme</span><br>
                        <strong style="color:#E8F4FF;font-size:14px">{program}</strong>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:8px 0;border-bottom:1px solid rgba(78,142,162,0.1)">
                        <span style="color:#6EA2B3;font-size:11px;text-transform:uppercase;letter-spacing:.5px">Institution</span><br>
                        <strong style="color:#E8F4FF;font-size:14px">{inst}</strong>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:8px 0;border-bottom:1px solid rgba(78,142,162,0.1)">
                        <span style="color:#6EA2B3;font-size:11px;text-transform:uppercase;letter-spacing:.5px">Date d'émission</span><br>
                        <strong style="color:#E8F4FF;font-size:14px">{date}</strong>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:8px 0">
                        <span style="color:#6EA2B3;font-size:11px;text-transform:uppercase;letter-spacing:.5px">Identifiant Unique</span><br>
                        <strong style="color:#7BBDE8;font-family:monospace;font-size:13px">{cert_id}</strong>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>

            <!-- Hash blockchain -->
            <div style="background:#000d1a;border:1px solid rgba(78,142,162,0.2);border-radius:8px;padding:14px;margin-bottom:24px">
              <p style="margin:0 0 6px;color:#6EA2B3;font-size:10px;text-transform:uppercase;letter-spacing:1px">⛓ Hash Blockchain (SHA-256)</p>
              <p style="margin:0;color:#4E8EA2;font-family:monospace;font-size:10px;word-break:break-all;line-height:1.8">{bh}</p>
            </div>

            <!-- CTA -->
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="center">
                  <a href="http://127.0.0.1:5000/certificates/verify/{cert_id}"
                     style="display:inline-block;background:linear-gradient(135deg,#0A4174,#4E8EA2);color:#ffffff;text-decoration:none;padding:13px 32px;border-radius:10px;font-weight:700;font-size:14px">
                    🔍 Vérifier mon certificat en ligne
                  </a>
                </td>
              </tr>
            </table>

            <p style="margin:24px 0 0;color:#4E8EA2;font-size:12px;text-align:center;line-height:1.7">
              Le certificat PDF est joint à cet email.<br>
              Conservez cet identifiant : <strong style="color:#7BBDE8">{cert_id}</strong>
            </p>

          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#061422;border-radius:0 0 16px 16px;padding:20px 32px;text-align:center">
            <p style="margin:0;color:#1A4A6A;font-size:11px">SmartCert · Blockchain Certificate Authority · Ethereum Testnet</p>
            <p style="margin:6px 0 0;color:#1A3A5A;font-size:10px">Cet email a été généré automatiquement. Ne pas répondre.</p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""