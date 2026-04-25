"""
SmartCert — app.py (version complète avec PDF + Email)
"""

from flask      import Flask, jsonify, request, send_file, g
from flask_cors import CORS
from web3       import Web3
import sqlite3, hashlib, uuid, json, os, io
from datetime   import datetime
from typing     import Optional

# Nouveaux services (fichier cert_services.py dans le même dossier)
try:
    from .cert_services import generate_certificate_pdf, send_certificate_email
except ImportError:
    from cert_services import generate_certificate_pdf, send_certificate_email

# Fix P1: import and register the authentication blueprint
from auth import auth_bp, require_auth

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Fix P1: register authentication routes (/auth/login, /auth/logout, /auth/me …)
app.register_blueprint(auth_bp)

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'certificates.db')
WEB3_PROVIDER = os.getenv('WEB3_PROVIDER', 'http://127.0.0.1:7545')
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))
# ─── DATABASE ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn   = get_db()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS certificates (
            id              TEXT PRIMARY KEY,
            recipient_name  TEXT NOT NULL,
            email           TEXT NOT NULL,
            program         TEXT NOT NULL,
            institution     TEXT DEFAULT 'SmartCert University',
            issue_date      TEXT NOT NULL,
            director_name   TEXT,
            status          TEXT DEFAULT 'Vérifié',
            blockchain_hash TEXT,
            tx_hash         TEXT,
            created_by      TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            action       TEXT NOT NULL,
            cert_id      TEXT,
            performed_by TEXT DEFAULT 'admin',
            timestamp    TEXT DEFAULT (datetime('now')),
            details      TEXT
        );
        CREATE TABLE IF NOT EXISTS users (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            email            TEXT UNIQUE NOT NULL,
            password_hash    TEXT NOT NULL,
            role             TEXT NOT NULL,
            name             TEXT NOT NULL,
            created_at       TEXT DEFAULT (datetime('now'))
        );
    """)
    # Migration: Add columns if they don't exist
    try:
        conn.execute("ALTER TABLE certificates ADD COLUMN director_name TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE certificates ADD COLUMN created_by TEXT")
    except:
        pass
    conn.commit()
        
    conn.close()
    print("[OK] Base de donnees initialisee")

# ─── HELPERS ──────────────────────────────────────────────
def generate_cert_id():
    year  = datetime.now().year
    short = str(uuid.uuid4()).upper()[:6]
    return f"CERT-{year}-{short}"

def compute_hash(data: dict) -> str:
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return "0x" + hashlib.sha256(payload.encode()).hexdigest()

def record_on_blockchain(cert_hash: str) -> Optional[str]:
    if w3.is_connected():
        try:
            accounts = w3.eth.accounts
            if accounts:
                tx = w3.eth.send_transaction({
                    'from':  accounts[0],
                    'to':    accounts[0],
                    'value': 0,
                    'data':  cert_hash.encode() if isinstance(cert_hash, str) else cert_hash,
                })
                return tx.hex()
        except Exception as e:
            print(f"⚠ Blockchain tx error: {e}")
    # Fix P7: use SHA-256 instead of broken MD5 for the fallback tx hash
    return "0xtx_" + hashlib.sha256(cert_hash.encode()).hexdigest()[:32]

def log_action(action: str, cert_id: str = None, details: str = None):
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_log (action, cert_id, details) VALUES (?, ?, ?)",
        (action, cert_id, details)
    )
    conn.commit()
    conn.close()

def row_to_dict(row):
    return dict(row)

# ═══════════════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════════════

@app.route('/')
def home():
    return jsonify({
        'status':       'success',
        'message':      'API SmartCert — Blockchain Certificate System',
        'web3_version': w3.api,
        'version':      '1.1.0',
    })

@app.route('/chain/status')
@require_auth()
def chain_status():
    connected = w3.is_connected()
    return jsonify({
        'connected':        connected,
        'web3_version':     w3.api,
        'network':          'Ethereum Testnet (Ganache)' if connected else 'Non connecté',
        'contract_address': None,
        'message':          'Connexion active' if connected else 'Blockchain non disponible',
    })



@app.route('/certificates/<cert_id>', methods=['GET'])
@require_auth()
def get_certificate(cert_id):
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM certificates WHERE id = ?", (cert_id,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Certificat introuvable'}), 404
    return jsonify(row_to_dict(row))

@app.route('/certificates', methods=['POST'])
@require_auth(roles=['admin'])
def issue_certificate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Corps JSON invalide'}), 400

    for field in ['recipient_name', 'email', 'program']:
        if not data.get(field):
            return jsonify({'error': f'Champ obligatoire manquant : {field}'}), 400

    cert_id       = generate_cert_id()
    issue_date    = data.get('issue_date') or datetime.now().strftime('%Y-%m-%d')
    institution   = data.get('institution', 'SmartCert University')
    director_name = data.get('director_name', 'Directeur des Études')

    hash_payload = {
        'id':             cert_id,
        'recipient_name': data['recipient_name'],
        'email':          data['email'],
        'program':        data['program'],
        'institution':    institution,
        'issue_date':     issue_date,
        'director_name':  director_name
    }
    blockchain_hash = compute_hash(hash_payload)
    tx_hash         = record_on_blockchain(blockchain_hash)

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO certificates 
            (id, recipient_name, email, program, institution, issue_date, director_name, status, blockchain_hash, tx_hash, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cert_id, data['recipient_name'], data['email'], data['program'], institution, issue_date, director_name, 'Vérifié', blockchain_hash, tx_hash, g.user['email']))
        conn.commit()
    except Exception as e:
        print(f"[ERREUR SQL] {e}")
        return jsonify({'error': 'Erreur lors de la sauvegarde'}), 500
    finally:
        conn.close()

    print(f"[OK] Certificat cree : {cert_id}")

    cert = {
        'id':              cert_id,
        'recipient_name':  data['recipient_name'],
        'email':           data['email'],
        'program':         data['program'],
        'institution':     institution,
        'issue_date':      issue_date,
        'status':          'Vérifié',
        'blockchain_hash': blockchain_hash,
        'tx_hash':         tx_hash,
    }

    # ── Envoi email automatique ──────────────────────────
    try:
        pdf_buf  = generate_certificate_pdf(cert)
        email_ok = send_certificate_email(cert, pdf_buf)
        log_action('EMAIL_SENT' if email_ok else 'EMAIL_FAILED', cert_id, data['email'])
    except Exception as e:
        print(f"[AVERTISSEMENT] Email/PDF error: {e}")
        email_ok = False

    log_action('ISSUE', cert_id, f"Émis pour {data['recipient_name']}")

    return jsonify({
        'message':         'Certificat émis avec succès',
        'cert_id':         cert_id,
        'blockchain_hash': blockchain_hash,
        'tx_hash':         tx_hash,
        'email_sent':      email_ok,
    }), 201

@app.route('/certificates', methods=['GET'])
@require_auth()
def get_certificates():
    try:
        conn = get_db()
        email = g.user.get('email')
        role = g.user.get('role')
        
        if role == 'admin':
            # Admin sees only certificates they created
            cursor = conn.execute("SELECT * FROM certificates WHERE created_by = ? ORDER BY issue_date DESC", (email,))
        else:
            # Student sees only certificates where they are the recipient
            cursor = conn.execute("SELECT * FROM certificates WHERE email = ? ORDER BY issue_date DESC", (email,))
            
        rows = cursor.fetchall()
        result = [row_to_dict(row) for row in rows]
        print(f"[OK] {len(result)} certificats envoyes pour {email} ({role})")
        return jsonify(result)
    except Exception as e:
        print(f"[ERREUR lecture] {e}")
        return jsonify([]), 500
    finally:
        conn.close()

@app.route('/certificates/verify/<cert_id>', methods=['GET'])
def verify_certificate(cert_id):
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM certificates WHERE id = ? OR blockchain_hash = ?",
        (cert_id, cert_id)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({
            'valid':    False,
            'verified': False,
            'message':  'Aucun certificat trouvé pour cet identifiant.',
        }), 404

    cert     = row_to_dict(row)
    is_valid = cert['status'] == 'Vérifié'
    # log_action('VERIFY', cert['id'])  # Removed to prevent Live Server auto-reload loop during verification

    return jsonify({
        'valid':    is_valid,
        'verified': is_valid,
        'message':  'Certificat valide' if is_valid else f"Certificat {cert['status']}",
        **cert,
    })

@app.route('/certificates/<cert_id>', methods=['DELETE'])
@require_auth(roles=['admin'])
def delete_certificate(cert_id):
    conn = get_db()
    row  = conn.execute(
        "SELECT id FROM certificates WHERE id = ?", (cert_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Certificat introuvable'}), 404
    conn.execute("DELETE FROM certificates WHERE id = ?", (cert_id,))
    conn.commit()
    conn.close()
    log_action('DELETE', cert_id)
    return jsonify({'message': 'Certificat supprimé', 'cert_id': cert_id})

@app.route('/certificates/<cert_id>/status', methods=['PATCH'])
@require_auth(roles=['admin'])
def update_status(cert_id):
    data       = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Corps JSON invalide'}), 400
    new_status = data.get('status')
    allowed    = ['Vérifié', 'En attente', 'Révoqué']
    if new_status not in allowed:
        return jsonify({'error': f'Statut invalide. Valeurs acceptées : {allowed}'}), 400
    conn = get_db()
    row  = conn.execute(
        "SELECT id FROM certificates WHERE id = ?", (cert_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Certificat introuvable'}), 404
    conn.execute(
        "UPDATE certificates SET status = ? WHERE id = ?",
        (new_status, cert_id)
    )
    conn.commit()
    conn.close()
    log_action('STATUS_UPDATE', cert_id, f"Statut → {new_status}")
    return jsonify({'message': 'Statut mis à jour', 'cert_id': cert_id, 'status': new_status})

@app.route('/stats', methods=['GET'])
@require_auth()
def get_stats():
    conn = get_db()
    email = g.user.get('email')
    role = g.user.get('role')
    
    if role == 'admin':
        condition = "WHERE created_by = ?"
        params = (email,)
    else:
        condition = "WHERE email = ?"
        params = (email,)
        
    total    = conn.execute(f"SELECT COUNT(*) FROM certificates {condition}", params).fetchone()[0]
    verified = conn.execute(f"SELECT COUNT(*) FROM certificates {condition} AND status='Vérifié'", params).fetchone()[0]
    pending  = conn.execute(f"SELECT COUNT(*) FROM certificates {condition} AND status='En attente'", params).fetchone()[0]
    revoked  = conn.execute(f"SELECT COUNT(*) FROM certificates {condition} AND status='Révoqué'", params).fetchone()[0]
    conn.close()
    return jsonify({
        'total':    total,
        'verified': verified,
        'pending':  pending,
        'revoked':  revoked,
    })

@app.route('/audit', methods=['GET'])
@require_auth(roles=['admin'])
def get_audit():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return jsonify({'logs': [row_to_dict(r) for r in rows]})

# ═══════════════════════════════════════════════════════════
#  NOUVELLES ROUTES — PDF & EMAIL
# ═══════════════════════════════════════════════════════════

@app.route('/certificates/<cert_id>/pdf', methods=['GET'])
@require_auth()
def download_certificate_pdf(cert_id):
    """Génère et retourne le certificat en PDF."""
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM certificates WHERE id = ?", (cert_id,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Certificat introuvable'}), 404

    cert = row_to_dict(row)

    try:
        pdf_buffer = generate_certificate_pdf(cert)
    except Exception as e:
        print(f"[ERREUR PDF] {cert_id}: {e}")
        return jsonify({'error': 'Erreur interne lors de la generation du PDF'}), 500

    log_action('DOWNLOAD_PDF', cert_id, f"PDF → {cert['recipient_name']}")

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"certificat_{cert_id}.pdf"
    )


@app.route('/certificates/<cert_id>/send-email', methods=['POST'])
@require_auth(roles=['admin'])
def send_email_route(cert_id):
    """Envoie le certificat PDF par email au bénéficiaire."""
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM certificates WHERE id = ?", (cert_id,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Certificat introuvable'}), 404

    cert = row_to_dict(row)

    try:
        pdf_buffer = generate_certificate_pdf(cert)
        success    = send_certificate_email(cert, pdf_buffer)
    except Exception as e:
        print(f"[ERREUR EMAIL] {cert_id}: {e}")
        return jsonify({'error': "Erreur interne lors de l'envoi de l'email"}), 500

    if success:
        log_action('EMAIL_SENT', cert_id, f"Email → {cert['email']}")
        return jsonify({
            'message': f"Email envoyé à {cert['email']}",
            'cert_id': cert_id
        })
    else:
        return jsonify({'error': 'Échec envoi email — vérifiez la config SMTP'}), 500


# ═══════════════════════════════════════════════════════════
if __name__ == '__main__':
    init_db()
    print("SmartCert API demarree -> http://127.0.0.1:5000")
    app.run(debug=False, host='127.0.0.1', port=5000)
