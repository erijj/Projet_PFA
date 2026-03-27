"""
SmartCert — app.py
Backend Flask : API REST pour la gestion des certificats
Base de données : SQLite (database.db)
Blockchain : Ethereum Testnet via Web3.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from web3 import Web3
import sqlite3
import hashlib
import uuid
import json
import os
from datetime import datetime
from typing import Optional


# ─── INIT APP ─────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Autorise les requêtes depuis le frontend

# ─── CONFIG ───────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DATABASE     = os.path.join(BASE_DIR, 'database.db')

# Ethereum Testnet (Ganache local par défaut)
# Remplacer par l'URL de votre nœud (Ganache, Infura Sepolia, etc.)
WEB3_PROVIDER = os.getenv('WEB3_PROVIDER', 'http://127.0.0.1:7545')

w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# ─── DATABASE ─────────────────────────────────────────────
def get_db():
    """Ouvre une connexion à la base de données SQLite."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # retourne des dicts
    return conn

def init_db():
    """Crée les tables si elles n'existent pas."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS certificates (
            id              TEXT PRIMARY KEY,
            recipient_name  TEXT NOT NULL,
            email           TEXT NOT NULL,
            program         TEXT NOT NULL,
            institution     TEXT DEFAULT 'SmartCert University',
            issue_date      TEXT NOT NULL,
            status          TEXT DEFAULT 'Vérifié',
            blockchain_hash TEXT,
            tx_hash         TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            action      TEXT NOT NULL,
            cert_id     TEXT,
            performed_by TEXT DEFAULT 'admin',
            timestamp   TEXT DEFAULT (datetime('now')),
            details     TEXT
        );
    """)
    conn.commit()
    conn.close()
    print("✅ Base de données initialisée")

# ─── HELPERS ──────────────────────────────────────────────
def generate_cert_id():
    """Génère un identifiant unique CERT-YYYY-XXXX."""
    year = datetime.now().year
    short = str(uuid.uuid4()).upper()[:6]
    return f"CERT-{year}-{short}"

def compute_hash(data: dict) -> str:
    """Calcule le hash SHA-256 des données du certificat."""
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return "0x" + hashlib.sha256(payload.encode()).hexdigest()

def record_on_blockchain(cert_hash: str) -> Optional[str]:
    """
    Simule l'enregistrement du hash sur la blockchain.
    En production : appeler un Smart Contract déployé.
    Retourne un tx_hash simulé (ou réel si connecté).
    """
    if w3.is_connected():
        try:
            # Simulation : transaction vers l'adresse nulle avec le hash en data
            accounts = w3.eth.accounts
            if accounts:
                tx = w3.eth.send_transaction({
                    'from': accounts[0],
                    'to':   accounts[0],
                    'value': 0,
                    'data': cert_hash.encode() if isinstance(cert_hash, str) else cert_hash,
                })
                return tx.hex()
        except Exception as e:
            print(f"⚠ Blockchain tx error: {e}")
    # Fallback : hash simulé si blockchain non connectée
    return "0xtx_" + hashlib.md5(cert_hash.encode()).hexdigest()

def log_action(action: str, cert_id: str = None, details: str = None):
    """Enregistre une action dans le journal d'audit."""
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_log (action, cert_id, details) VALUES (?, ?, ?)",
        (action, cert_id, details)
    )
    conn.commit()
    conn.close()

def row_to_dict(row):
    """Convertit une Row SQLite en dict Python."""
    return dict(row)

# ═══════════════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════════════

# ─── TEST ──────────────────────────────────────────────────
@app.route('/')
def home():
    return jsonify({
        'status':       'success',
        'message':      'API SmartCert — Blockchain Certificate System',
        'web3_version': w3.api,
        'version':      '1.0.0',
    })

# ─── BLOCKCHAIN STATUS ─────────────────────────────────────
@app.route('/chain/status')
def chain_status():
    connected = w3.is_connected()
    return jsonify({
        'connected':        connected,
        'web3_version':     w3.api,
        'network':          'Ethereum Testnet (Ganache)' if connected else 'Non connecté',
        'contract_address': None,  # À renseigner quand le contrat est déployé
        'message':          'Connexion active' if connected else 'Blockchain non disponible',
    })

# ─── GET ALL CERTIFICATES ──────────────────────────────────
@app.route('/certificates', methods=['GET'])
def get_certificates():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM certificates ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify({
        'certificates': [row_to_dict(r) for r in rows],
        'total':        len(rows),
    })

# ─── GET ONE CERTIFICATE ───────────────────────────────────
@app.route('/certificates/<cert_id>', methods=['GET'])
def get_certificate(cert_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM certificates WHERE id = ?", (cert_id,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Certificat introuvable'}), 404

    return jsonify(row_to_dict(row))

# ─── ISSUE CERTIFICATE ─────────────────────────────────────
@app.route('/certificates', methods=['POST'])
def issue_certificate():
    data = request.get_json()

    # Validation
    required = ['recipient_name', 'email', 'program']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Champ obligatoire manquant : {field}'}), 400

    cert_id     = generate_cert_id()
    issue_date  = data.get('issue_date') or datetime.now().strftime('%Y-%m-%d')
    institution = data.get('institution', 'SmartCert University')

    # Hash du certificat
    hash_payload = {
        'id':             cert_id,
        'recipient_name': data['recipient_name'],
        'email':          data['email'],
        'program':        data['program'],
        'institution':    institution,
        'issue_date':     issue_date,
    }
    blockchain_hash = compute_hash(hash_payload)

    # Enregistrement blockchain
    tx_hash = record_on_blockchain(blockchain_hash)

    # Sauvegarde en base
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO certificates
            (id, recipient_name, email, program, institution, issue_date,
             status, blockchain_hash, tx_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cert_id,
            data['recipient_name'],
            data['email'],
            data['program'],
            institution,
            issue_date,
            'Vérifié',
            blockchain_hash,
            tx_hash,
        ))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    conn.close()

    log_action('ISSUE', cert_id, f"Émis pour {data['recipient_name']}")

    return jsonify({
        'message':         'Certificat émis avec succès',
        'cert_id':         cert_id,
        'blockchain_hash': blockchain_hash,
        'tx_hash':         tx_hash,
    }), 201

# ─── VERIFY CERTIFICATE ────────────────────────────────────
@app.route('/certificates/verify/<cert_id>', methods=['GET'])
def verify_certificate(cert_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM certificates WHERE id = ? OR blockchain_hash = ?",
        (cert_id, cert_id)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({
            'valid':   False,
            'verified': False,
            'message': 'Aucun certificat trouvé pour cet identifiant.',
        }), 404

    cert = row_to_dict(row)
    is_valid = cert['status'] == 'Vérifié'
    log_action('VERIFY', cert['id'])

    return jsonify({
        'valid':            is_valid,
        'verified':         is_valid,
        'message':          'Certificat valide' if is_valid else f"Certificat {cert['status']}",
        **cert,
    })

# ─── DELETE CERTIFICATE ────────────────────────────────────
@app.route('/certificates/<cert_id>', methods=['DELETE'])
def delete_certificate(cert_id):
    conn = get_db()
    row = conn.execute(
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

# ─── UPDATE STATUS ─────────────────────────────────────────
@app.route('/certificates/<cert_id>/status', methods=['PATCH'])
def update_status(cert_id):
    data = request.get_json()
    new_status = data.get('status')
    allowed = ['Vérifié', 'En attente', 'Révoqué']

    if new_status not in allowed:
        return jsonify({'error': f'Statut invalide. Valeurs acceptées : {allowed}'}), 400

    conn = get_db()
    row = conn.execute(
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

# ─── STATS ─────────────────────────────────────────────────
@app.route('/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    total    = conn.execute("SELECT COUNT(*) FROM certificates").fetchone()[0]
    verified = conn.execute("SELECT COUNT(*) FROM certificates WHERE status='Vérifié'").fetchone()[0]
    pending  = conn.execute("SELECT COUNT(*) FROM certificates WHERE status='En attente'").fetchone()[0]
    revoked  = conn.execute("SELECT COUNT(*) FROM certificates WHERE status='Révoqué'").fetchone()[0]
    conn.close()

    return jsonify({
        'total':    total,
        'verified': verified,
        'pending':  pending,
        'revoked':  revoked,
    })

# ─── AUDIT LOG ─────────────────────────────────────────────
@app.route('/audit', methods=['GET'])
def get_audit():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return jsonify({'logs': [row_to_dict(r) for r in rows]})

# ═══════════════════════════════════════════════════════════
#  LAUNCH
# ═══════════════════════════════════════════════════════════
if __name__ == '__main__':
    init_db()
    print("🚀 SmartCert API démarrée → http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)