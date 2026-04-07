"""
SmartCert — cert_services.py (VERSION FINALE)
Design certificat professionnel style papier officiel
identique dans le PDF et dans les pages web
"""

import io, smtplib, os
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders

from reportlab.lib.pagesizes import A4
from reportlab.lib           import colors
from reportlab.lib.units     import mm
from reportlab.pdfgen        import canvas
from reportlab.lib.utils     import ImageReader

SMTP_HOST     = os.getenv('SMTP_HOST',     'smtp.gmail.com')
SMTP_PORT     = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER     = os.getenv('SMTP_USER',     'smartcert.noreply@gmail.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
FROM_NAME     = os.getenv('FROM_NAME',     'SmartCert')

# Palette identique au projet
C_NAVY  = colors.HexColor('#001D39')
C_BLUE  = colors.HexColor('#0A4174')
C_TEAL  = colors.HexColor('#4E8EA2')
C_ACC   = colors.HexColor('#7BBDE8')
C_PALE  = colors.HexColor('#BDD8E9')
C_WHITE = colors.white
C_GREEN = colors.HexColor('#10b981')
C_GOLD  = colors.HexColor('#C9A03D')
C_BODY  = colors.HexColor('#1A2A4F')
C_DARK  = colors.HexColor('#2C3E5A')
C_BORDER = colors.HexColor('#D4AF37')

"""def _logo():
    base = os.path.dirname(os.path.abspath(__file__))
    for p in [os.path.join(base,'..','shared','logo.png'),
              os.path.join(base,'shared','logo.png'),
              os.path.join(base,'logo.png')]:
        if os.path.exists(p): return p
    return None"""

def _logo() -> str | None:
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, '..', 'shared', 'logo.png'),
        os.path.join(base, 'shared', 'logo.png'),
        os.path.join(base, 'logo.png'),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # تحذير مرة واحدة فقط عند التشغيل
    print("⚠ logo.png introuvable — le PDF utilisera le texte 'SmartCert' à la place.")
    print(f"  Chemins recherchés : {candidates}")
    return None

def generate_certificate_pdf(cert: dict) -> io.BytesIO:
    buf = io.BytesIO()
    W, H = A4
    c = canvas.Canvas(buf, pagesize=A4)

    # ── FOND BLANC PAPIER ────────────────────────────────
    c.setFillColor(colors.HexColor('#FDFAF4'))
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Texture subtile : lignes très légères
    c.setStrokeColor(colors.HexColor('#E8DFC8'))
    c.setLineWidth(0.3)
    for y in range(0, int(H), 8):
        c.line(0, y, W, y)

    # Fond blanc pur sur la zone centrale
    c.setFillColor(colors.white)
    c.rect(14*mm, 14*mm, W-28*mm, H-28*mm, fill=1, stroke=0)

    # ── BORDURES DORÉES DOUBLES ──────────────────────────
    c.setStrokeColor(C_GOLD)
    c.setLineWidth(3.5)
    c.rect(10*mm, 10*mm, W-20*mm, H-20*mm, fill=0, stroke=1)
    c.setLineWidth(0.8)
    c.rect(13.5*mm, 13.5*mm, W-27*mm, H-27*mm, fill=0, stroke=1)

    # ── COINS ORNEMENTAUX ───────────────────────────────
    def corner(x, y, dx, dy):
        s = 10*mm
        c.setStrokeColor(C_GOLD)
        c.setLineWidth(2)
        c.line(x, y, x+dx*s, y)
        c.line(x, y, x, y+dy*s)
        c.setFillColor(C_GOLD)
        c.circle(x, y, 1.5*mm, fill=1, stroke=0)
    m = 10*mm
    corner(m, m, 1, 1)
    corner(W-m, m, -1, 1)
    corner(m, H-m, 1, -1)
    corner(W-m, H-m, -1, -1)

    # ── BANDE DÉCORATIVE BLEUE HAUTE ───────────────────
    c.setFillColor(C_BLUE)
    c.rect(14*mm, H-50*mm, W-28*mm, 36*mm, fill=1, stroke=0)

    # ── LOGO STYLE PAGE WEB (90x60) ─────────────────────
    logo_path = _logo()
    lw, lh = 90, 60  # en points (1 point = 1/72 inch)
    # Convertir en mm pour le placement (90px ~ 31.75mm)
    lw_mm = 31.75 * mm
    lh_mm = 21.17 * mm
    lx = W/2 - lw_mm/2
    ly = H - 46*mm

    # Cadre blanc avec ombre légère
    c.setFillColor(colors.white)
    c.setStrokeColor(C_ACC)
    c.setLineWidth(1.5)
    c.roundRect(lx-3*mm, ly-3*mm, lw_mm+6*mm, lh_mm+6*mm, 4*mm, fill=1, stroke=1)
    
    # Effet d'ombre (simulation)
    c.setFillColor(colors.HexColor('#E0E0E0'))
    c.roundRect(lx-2*mm, ly-4*mm, lw_mm+6*mm, lh_mm+6*mm, 4*mm, fill=0, stroke=0)
    
    if logo_path:
        try:
            # Charger l'image et la redimensionner
            from PIL import Image
            img = Image.open(logo_path)
            # Conserver les proportions
            img_width, img_height = img.size
            ratio = min(lw_mm / img_width, lh_mm / img_height)
            new_w = img_width * ratio
            new_h = img_height * ratio
            img_x = lx + (lw_mm - new_w)/2
            img_y = ly + (lh_mm - new_h)/2
            c.drawImage(ImageReader(logo_path), img_x, img_y,
                        width=new_w, height=new_h, mask='auto', preserveAspectRatio=True)
        except:
            # Fallback si PIL n'est pas disponible
            try:
                c.drawImage(ImageReader(logo_path), lx, ly,
                            width=lw_mm, height=lh_mm, mask='auto', preserveAspectRatio=True)
            except:
                c.setFillColor(C_BLUE)
                c.setFont('Helvetica-Bold', 14)
                c.drawCentredString(W/2, ly+8*mm, 'SmartCert')
    else:
        c.setFillColor(C_BLUE)
        c.setFont('Helvetica-Bold', 14)
        c.drawCentredString(W/2, ly+8*mm, 'SmartCert')

    # ── NOM INSTITUTION ─────────────────────────────────
    c.setFillColor(C_PALE)
    c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(W/2, H-52*mm, cert.get('institution','SmartCert University').upper())

    # ── LIGNE DORÉE SÉPARATRICE ─────────────────────────
    c.setStrokeColor(C_GOLD)
    c.setLineWidth(1.2)
    c.line(22*mm, H-55*mm, W-22*mm, H-55*mm)
    c.setStrokeColor(C_TEAL)
    c.setLineWidth(0.4)
    c.line(22*mm, H-56.5*mm, W-22*mm, H-56.5*mm)

    # ── TITRE ───────────────────────────────────────────
    c.setFillColor(C_BODY)
    c.setFont('Helvetica-Bold', 24)
    c.drawCentredString(W/2, H-68*mm, 'CERTIFICAT DE RÉUSSITE')
    c.setFillColor(C_TEAL)
    c.setFont('Helvetica', 8)
    c.drawCentredString(W/2, H-74*mm, '—  CERTIFICATE OF ACHIEVEMENT  —')

    # ── CORPS ───────────────────────────────────────────
    name    = cert.get('recipient_name', '—')
    program = cert.get('program', '—')
    date    = (cert.get('issue_date') or '—').split('T')[0]
    status  = cert.get('status', 'Vérifié')
    cid     = cert.get('id', '—')

    c.setFillColor(C_TEAL)
    c.setFont('Helvetica', 10)
    c.drawCentredString(W/2, H-86*mm, 'La présente certifie que')

    # Nom
    fs = 28 if len(name) <= 22 else (22 if len(name) <= 30 else 17)
    c.setFillColor(C_BODY)
    c.setFont('Helvetica-Bold', fs)
    c.drawCentredString(W/2, H-98*mm, name)

    nw = c.stringWidth(name, 'Helvetica-Bold', fs)
    c.setStrokeColor(C_GOLD)
    c.setLineWidth(1.2)
    half = min(nw/2+8*mm, W/2-18*mm)
    c.line(W/2-half, H-101*mm, W/2+half, H-101*mm)

    c.setFillColor(C_DARK)
    c.setFont('Helvetica', 9.5)
    c.drawCentredString(W/2, H-110*mm, 'a complété avec succès le programme')

    pf = 15 if len(program) <= 40 else 12
    c.setFillColor(C_BODY)
    c.setFont('Helvetica-Bold', pf)
    c.drawCentredString(W/2, H-120*mm, program)

    # ── SÉPARATEUR ──────────────────────────────────────
    c.setStrokeColor(colors.HexColor('#D5E8F5'))
    c.setLineWidth(0.8)
    c.line(20*mm, H-128*mm, W-20*mm, H-128*mm)

    # ── 3 CARTES INFO ───────────────────────────────────
    gy = H-140*mm
    for cx, lb, vl in zip(
        [W*0.22, W*0.5, W*0.78],
        ["Date d'émission","Identifiant","Statut"],
        [date, cid, status]
    ):
        c.setFillColor(colors.HexColor('#F0F7FF'))
        c.setStrokeColor(colors.HexColor('#C0D8F0'))
        c.setLineWidth(0.5)
        c.roundRect(cx-22*mm, gy-10*mm, 44*mm, 19*mm, 2*mm, fill=1, stroke=1)
        c.setFillColor(C_TEAL)
        c.setFont('Helvetica', 6.5)
        c.drawCentredString(cx, gy+5*mm, lb.upper())
        vc = C_GREEN if (lb == 'Statut' and status == 'Vérifié') else C_BODY
        c.setFillColor(vc)
        vf = 7.5 if len(vl) > 14 else 9.5
        c.setFont('Helvetica-Bold', vf)
        c.drawCentredString(cx, gy-4*mm, vl)

    # ── TAMPON VÉRIFIÉ ──────────────────────────────────
    if status == 'Vérifié':
        c.saveState()
        c.translate(W-46*mm, H-128*mm)
        c.rotate(16)
        c.setStrokeColor(C_GREEN)
        c.setLineWidth(2.2)
        c.setFillColor(colors.HexColor('#F0FDF8'))
        c.roundRect(-19*mm, -7*mm, 38*mm, 14*mm, 3*mm, fill=1, stroke=1)
        c.setFillColor(C_GREEN)
        c.setFont('Helvetica-Bold', 10)
        c.drawCentredString(0, -2.5*mm, 'VERIFIE')
        c.restoreState()

    # ── SÉPARATION SIGNATURE ────────────────────────────
    sep_y = H-168*mm
    c.setStrokeColor(colors.HexColor('#D5E8F5'))
    c.setLineWidth(0.8)
    c.line(20*mm, sep_y+14*mm, W-20*mm, sep_y+14*mm)

    # ── SIGNATURE GAUCHE ────────────────────────────────
    sx = W*0.28
    # Tracé cursif
    c.setStrokeColor(C_BODY)
    c.setLineWidth(1.6)
    c.setLineCap(1)
    p = c.beginPath()
    p.moveTo(sx-17*mm, sep_y+9*mm)
    p.curveTo(sx-9*mm, sep_y+14*mm, sx+1*mm, sep_y+7*mm, sx+8*mm, sep_y+12*mm)
    p.curveTo(sx+13*mm, sep_y+15*mm, sx+15*mm, sep_y+8*mm, sx+17*mm, sep_y+10*mm)
    c.drawPath(p, stroke=1, fill=0)
    p2 = c.beginPath()
    p2.moveTo(sx-11*mm, sep_y+6*mm)
    p2.curveTo(sx-3*mm, sep_y+10*mm, sx+5*mm, sep_y+4*mm, sx+11*mm, sep_y+8*mm)
    c.drawPath(p2, stroke=1, fill=0)

    c.setStrokeColor(C_TEAL)
    c.setLineWidth(0.7)
    c.line(sx-20*mm, sep_y, sx+20*mm, sep_y)
    c.setFillColor(C_BODY)
    c.setFont('Helvetica-Bold', 7.5)
    c.drawCentredString(sx, sep_y-5*mm, 'Dr. Sarah Martin')
    c.setFillColor(C_TEAL)
    c.setFont('Helvetica', 6.5)
    c.drawCentredString(sx, sep_y-10*mm, 'Directrice des Études')

    # ── CACHET OFFICIEL ─────────────────────────────────
    seax = W*0.72
    seay = sep_y + 3*mm
    ro, ri = 17*mm, 12*mm

    c.setFillColor(colors.HexColor('#EEF5FB'))
    c.setStrokeColor(C_BODY)
    c.setLineWidth(1.8)
    c.circle(seax, seay, ro, fill=1, stroke=1)

    c.setStrokeColor(C_TEAL)
    c.setLineWidth(0.8)
    c.circle(seax, seay, ri, fill=0, stroke=1)

    c.setStrokeColor(C_ACC)
    c.setLineWidth(0.4)
    c.setDash([1.5, 2.5])
    c.circle(seax, seay, ro-3*mm, fill=0, stroke=1)
    c.setDash([])

    lp = _logo()
    if lp:
        try:
            lsz = 14*mm
            c.drawImage(ImageReader(lp), seax-lsz/2, seay-lsz/2+2*mm,
                        width=lsz, height=lsz, mask='auto', preserveAspectRatio=True)
        except:
            c.setFillColor(C_BODY)
            c.setFont('Helvetica-Bold', 9)
            c.drawCentredString(seax, seay+1*mm, 'SC')
    else:
        c.setFillColor(C_BODY)
        c.setFont('Helvetica-Bold', 9)
        c.drawCentredString(seax, seay+1*mm, 'SC')

    c.setFillColor(C_BODY)
    c.setFont('Helvetica-Bold', 5.5)
    c.drawCentredString(seax, seay+11*mm, 'SMARTCERT UNIVERSITY')
    c.setFillColor(C_TEAL)
    c.setFont('Helvetica', 5)
    c.drawCentredString(seax, seay-10*mm, 'OFFICIEL · BLOCKCHAIN')

    c.setFillColor(C_GOLD)
    c.setFont('Helvetica-Bold', 7)
    c.drawCentredString(seax-11*mm, seay-1*mm, '*')
    c.drawCentredString(seax+11*mm, seay-1*mm, '*')

    # ── NOTE AUTH ───────────────────────────────────────
    c.setFillColor(colors.HexColor('#6A8FAA'))
    c.setFont('Helvetica', 7.5)
    c.drawCentredString(W/2, sep_y-20*mm,
        'Ce certificat est authentifié par la blockchain Ethereum et ne peut être falsifié.')

    # ── FOOTER BLOCKCHAIN ───────────────────────────────
    bh = cert.get('blockchain_hash','')
    c.setFillColor(C_BLUE)
    c.rect(14*mm, 14*mm, W-28*mm, 13*mm, fill=1, stroke=0)

    c.setFillColor(C_ACC)
    c.setFont('Helvetica-Bold', 6.5)
    c.drawString(18*mm, 23*mm, 'SHA-256:')
    c.setFillColor(C_PALE)
    c.setFont('Helvetica', 6)
    h_disp = (bh[:68]+'...') if len(bh) > 68 else (bh or 'Non disponible')
    c.drawString(34*mm, 23*mm, h_disp)
    c.setFillColor(colors.HexColor('#7BBDE8'))
    c.setFont('Helvetica', 5.5)
    c.drawString(18*mm, 18*mm, f'ID: {cid}')
    c.drawRightString(W-18*mm, 18*mm, 'smartcert.app/verify')

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def send_certificate_email(cert: dict, pdf_bytes: io.BytesIO) -> bool:
    email = cert.get('email')
    if not email: return False
    if not SMTP_PASSWORD:
        print("Mode demo — email simulé")
        return True
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Votre certificat SmartCert — {cert.get('program','')}"
        msg['From']    = f"{FROM_NAME} <{SMTP_USER}>"
        msg['To']      = email
        msg.attach(MIMEText(_email_html(cert), 'html', 'utf-8'))
        pdf_bytes.seek(0)
        part = MIMEBase('application','pdf')
        part.set_payload(pdf_bytes.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="certificat_{cert.get("id","smartcert")}.pdf"')
        msg.attach(part)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.ehlo(); s.starttls(); s.login(SMTP_USER, SMTP_PASSWORD)
            s.sendmail(SMTP_USER, email, msg.as_string())
        print(f"Email envoye -> {email}")
        return True
    except Exception as e:
        print(f"Erreur email: {e}")
        return False


def _email_html(cert):
    n  = cert.get('recipient_name','Etudiant')
    pr = cert.get('program','—')
    ins= cert.get('institution','SmartCert University')
    d  = (cert.get('issue_date') or '—').split('T')[0]
    cid= cert.get('id','—')
    bh = cert.get('blockchain_hash','—')
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#001D39;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:32px 16px">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px">
<tr><td style="background:linear-gradient(135deg,#0A4174,#4E8EA2);border-radius:16px 16px 0 0;padding:32px;text-align:center">
  <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:10px">
    <img src="https://smartcert.app/logo.png" alt="SmartCert" style="width:45px;height:30px;object-fit:contain">
    <h1 style="margin:0;color:white;font-size:24px">SmartCert</h1>
  </div>
  <p style="margin:6px 0 0;color:#BDD8E9;font-size:11px;letter-spacing:2px">BLOCKCHAIN CERTIFICATE AUTHORITY</p>
</td></tr>
<tr><td style="background:#0A2E50;padding:32px">
  <p style="color:#BDD8E9;font-size:14px">Bonjour <strong style="color:#7BBDE8">{n}</strong>,</p>
  <p style="color:#6EA2B3;font-size:13px;line-height:1.7">Votre certificat a ete emis et enregistre sur la blockchain Ethereum.</p>
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#001D39;border:1px solid rgba(78,142,162,.3);border-radius:10px;margin:16px 0">
    <tr><td style="background:rgba(16,185,129,.08);border-bottom:1px solid rgba(16,185,129,.2);padding:12px 18px">
      <span style="color:#10b981;font-weight:700;font-size:13px">✅ Certificat Authentique et Verifie</span>
    </td></tr>
    <tr><td style="padding:18px">
      <p style="margin:0 0 8px;color:#6EA2B3;font-size:10px;text-transform:uppercase">Beneficiaire</p>
      <p style="margin:0 0 14px;color:#E8F4FF;font-size:15px;font-weight:700">{n}</p>
      <p style="margin:0 0 8px;color:#6EA2B3;font-size:10px;text-transform:uppercase">Programme</p>
      <p style="margin:0 0 14px;color:#E8F4FF;font-size:14px">{pr}</p>
      <p style="margin:0 0 8px;color:#6EA2B3;font-size:10px;text-transform:uppercase">Institution</p>
      <p style="margin:0 0 14px;color:#E8F4FF;font-size:13px">{ins}</p>
      <p style="margin:0 0 8px;color:#6EA2B3;font-size:10px;text-transform:uppercase">Date · Identifiant</p>
      <p style="margin:0;color:#7BBDE8;font-family:monospace;font-size:12px">{d} · {cid}</p>
    </td></tr>
  </table>
  <div style="background:#000d1a;border:1px solid rgba(78,142,162,.2);border-radius:8px;padding:12px;margin-bottom:20px">
    <p style="margin:0 0 5px;color:#6EA2B3;font-size:10px;text-transform:uppercase">Hash Blockchain SHA-256</p>
    <p style="margin:0;color:#4E8EA2;font-family:monospace;font-size:9px;word-break:break-all">{bh}</p>
  </div>
  <div style="text-align:center;margin-bottom:16px">
    <div style="display:inline-block;border:1px solid #C9A03D;border-radius:8px;padding:8px 16px">
      <span style="color:#C9A03D;font-size:11px">🎓 Vérifié sur Blockchain Ethereum</span>
    </div>
  </div>
  <p style="color:#4E8EA2;font-size:12px;text-align:center">PDF joint a cet email · ID : <strong style="color:#7BBDE8">{cid}</strong></p>
</td></tr>
<tr><td style="background:#061422;border-radius:0 0 16px 16px;padding:14px;text-align:center">
  <p style="margin:0;color:#1A4A6A;font-size:10px">SmartCert · Blockchain Certificate Authority · Ethereum Testnet</p>
</td></tr>
</table>
</td></tr>
</table>
</body></html>"""