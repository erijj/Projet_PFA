"""
SmartCert — app.py (VERSION FINALE UNIFIÉE)
Auth complète + PDF + Email + routes publiques pour verify
Inclut: validation, rate limiting, session cleanup, error handling
Compatible avec : dashboard.html, script.js, dashboard_candidat.html,
                  issue-cert.html, verify-cert.html
"""

from flask import Flask, jsonify, request, make_response, send_file
from flask_cors import CORS
from web3 import Web3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
import secrets
import warnings
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from utils import (
    DATABASE, generate_cert_id, compute_hash, fake_tx_hash,
    validate_email, validate_recipient_name, validate_date, validate_program,
    validate_status, can_transition, get_utc_now, VALID_STATUSES, ALLOWED_TRANSITIONS
)

# ─── DEV MODE ─────────────────────────────────────────────
DEV_MODE = os.getenv('DEV_MODE', 'True').lower() == 'true'

# ─── INIT APP ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "CHANGE_ME_TO_A_RANDOM_SECRET_IN_PROD")
if app.secret_key == "CHANGE_ME_TO_A_RANDOM_SECRET_IN_PROD" and not app.debug:
    warnings.warn(
        "FLASK_SECRET_KEY non défini — utilisez une clé secrète forte en production !",
        stacklevel=2
    )

# ─── CORS ─────────────────────────────────────────────────
# Autoriser dashboard (5500) + pages publiques (ouvertes via fichier)
CORS(app, 
     supports_credentials=True,
     origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "http://127.0.0.1:5000",
        "http://localhost:5000",
        "http://192.168.1.13:5500",
        "http://192.168.1.13:5501",
        "http://192.168.1.13:5000",
        "file://",
        "null",   # ouverture directe fichier HTML depuis le bureau
     ],
     allow_headers=['Content-Type', 'Authorization', 'Cookie'],
     expose_headers=['Set-Cookie', 'Content-Type', 'Access-Control-Allow-Credentials'],
     methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
     allow_credentials=True
)

# ─── RATE LIMITING CONSTANTS ────────────────────────────
MAX_LOGIN_ATTEMPTS = 5         # Tentatives de connexion
ATTEMPT_WINDOW_MINUTES = 15    # Fenêtre de temps en minutes
ATTEMPT_DECAY_SECONDS = 900    # Réinitialiser après 15 min

# ─── BLOCKCHAIN ───────────────────────────────────────────
WEB3_PROVIDER = os.getenv('WEB3_PROVIDER', 'http://127.0.0.1:7545')
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# ─── SESSION ──────────────────────────────────────────────
SESSION_COOKIE          = "smartcert_session"
SESSION_DURATION_HOURS  = 8


# ═══════════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════════

def get_db():
    """Ouvre une connexion SQLite avec retour en dict."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crée les tables si elles n'existent pas."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS certificates (
            id               TEXT PRIMARY KEY,
            recipient_name   TEXT NOT NULL,
            email            TEXT NOT NULL,
            program          TEXT NOT NULL,
            institution      TEXT DEFAULT 'SmartCert University',
            issue_date       TEXT NOT NULL,
            status           TEXT DEFAULT 'En attente',
            blockchain_hash  TEXT,
            tx_hash          TEXT,
            created_at       TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            action       TEXT NOT NULL,
            cert_id      TEXT,
            performed_by TEXT DEFAULT 'admin',
            timestamp    TEXT DEFAULT (datetime('now')),
            severity     TEXT DEFAULT 'INFO',
            details      TEXT
        );
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'etudiant'
        );
        CREATE TABLE IF NOT EXISTS sessions (
            session_id  TEXT PRIMARY KEY,
            user_id     INTEGER NOT NULL,
            email       TEXT NOT NULL,
            role        TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now')),
            expires_at  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS failed_attempts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT NOT NULL,
            attempt_at  TEXT DEFAULT (datetime('now')),
            ip_address  TEXT
        );
    """)
    conn.commit()
    conn.close()
    print("✅ Base de données initialisée")


def ensure_default_users():
    """Crée les comptes démo admin et étudiant s'ils n'existent pas."""
    conn = get_db()
    defaults = [
        ("admin@smartcert.tn",    "admin123",    "admin"),
        ("etudiant@smartcert.tn", "etudiant123", "etudiant"),
    ]
    for email, pw, role in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO users (email, password_hash, role) VALUES (?, ?, ?)",
            (email.lower(), generate_password_hash(pw), role),
        )
    conn.commit()
    conn.close()
    print("✅ Comptes démo vérifiés")


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════

def record_on_blockchain(cert_hash: str) -> Optional[str]:
    """
    Enregistre le hash sur la blockchain.
    Fallback vers tx simulé si Ganache non connecté.
    """
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
                print(f"✅ Blockchain tx: {tx.hex()}")
                return tx.hex()
        except Exception as e:
            print(f"⚠ Blockchain tx error: {e}")
            log_action('BLOCKCHAIN_ERROR', details=f"Transaction failed: {str(e)}", severity='WARNING')
    return fake_tx_hash(cert_hash)


def log_action(action: str, cert_id: str = None, details: str = None,
               performed_by: str = 'admin', severity: str = 'INFO'):
    """Enregistre une action dans le journal d'audit."""
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO audit_log (action, cert_id, details, performed_by, severity) VALUES (?, ?, ?, ?, ?)",
            (action, cert_id, details, performed_by, severity)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Log error: {e}")


def record_failed_attempt(email: str, ip_address: str = None):
    """Enregistre une tentative de connexion échouée."""
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO failed_attempts (email, ip_address) VALUES (?, ?)",
            (email.lower(), ip_address)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Failed attempt recording error: {e}")


def get_failed_attempts(email: str) -> int:
    """Retourne le nombre de tentatives échouées récentes."""
    try:
        conn = get_db()
        cutoff_time = (datetime.now(timezone.utc) - timedelta(minutes=ATTEMPT_WINDOW_MINUTES)).isoformat()
        count = conn.execute(
            "SELECT COUNT(*) FROM failed_attempts WHERE email = ? AND attempt_at > ?",
            (email.lower(), cutoff_time)
        ).fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"❌ Failed attempts lookup error: {e}")
        return 0


def cleanup_old_attempts():
    """Nettoie les tentatives de connexion échouées expirées."""
    try:
        conn = get_db()
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=ATTEMPT_WINDOW_MINUTES)).isoformat()
        conn.execute("DELETE FROM failed_attempts WHERE attempt_at < ?", (cutoff,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠ Cleanup error: {e}")


def cleanup_expired_sessions():
    """Thread daemon: nettoie les sessions expirées toutes les heures."""
    while True:
        try:
            time.sleep(3600)  # Toutes les heures
            conn = get_db()
            conn.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")
            conn.commit()
            conn.close()
            print("✅ Session cleanup completed")
        except Exception as e:
            print(f"⚠ Session cleanup error: {e}")


def row_to_dict(row) -> dict:
    return dict(row)


# ═══════════════════════════════════════════════════════════
#  SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════

def create_session(user_id: int, email: str, role: str) -> str:
    session_id = secrets.token_hex(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=SESSION_DURATION_HOURS)).isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (session_id, user_id, email, role, expires_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, user_id, email, role, expires_at),
    )
    conn.commit()
    conn.close()
    return session_id


def get_session_user() -> Optional[dict]:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return None
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    session = dict(row)
    try:
        expires_at = datetime.fromisoformat(session["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            delete_session(session_id)
            return None
    except (ValueError, KeyError):
        return None
    return session


def delete_session(session_id: str):
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════
#  DECORATORS AUTH
# ═══════════════════════════════════════════════════════════

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # في DEV_MODE، السماح بالوصول بدون تحقق
        if DEV_MODE:
            return fn(*args, **kwargs)
        
        if not get_session_user():
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # في DEV_MODE، السماح بالوصول بدون تحقق الدور
            if DEV_MODE:
                return fn(*args, **kwargs)
            
            user = get_session_user()
            if not user:
                return jsonify({"error": "Unauthorized"}), 401
            if user.get("role") not in roles:
                return jsonify({"error": "Forbidden — رôle insuffisant"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return deco


# ═══════════════════════════════════════════════════════════
#  ROUTES — TEST
# ═══════════════════════════════════════════════════════════

@app.route('/')
def home():
    return jsonify({
        'status':       'success',
        'message':      'API SmartCert — Blockchain Certificate System',
        'web3_version': w3.api,
        'version':      '2.0.0',
    })


# ═══════════════════════════════════════════════════════════
#  ROUTES — AUTH
# ═══════════════════════════════════════════════════════════

@app.route('/auth/login', methods=['POST'])
def auth_login():
    data     = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    ip_addr  = request.remote_addr

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    # Vérifier la validité du format email
    valid_email, email_error = validate_email(email)
    if not valid_email:
        return jsonify({"error": email_error}), 400

    # Rate limiting: vérifier les tentatives échouées
    failed_count = get_failed_attempts(email)
    if failed_count >= MAX_LOGIN_ATTEMPTS:
        log_action('LOGIN_BLOCKED', details=f"Too many attempts from {ip_addr}", performed_by=email, severity='WARNING')
        return jsonify({
            "error": f"Trop de tentatives échouées. Réessayez après 15 minutes."
        }), 429

    conn = get_db()
    row  = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if not row or not check_password_hash(row["password_hash"], password):
        record_failed_attempt(email, ip_addr)
        log_action('LOGIN_FAILED', details=f"Invalid credentials from {ip_addr}", performed_by=email, severity='WARNING')
        return jsonify({"error": "Identifiants incorrects"}), 401

    # Connexion réussie: effacer les tentatives échouées
    try:
        conn = get_db()
        conn.execute("DELETE FROM failed_attempts WHERE email = ?", (email,))
        conn.commit()
        conn.close()
    except:
        pass

    user       = dict(row)
    session_id = create_session(user["id"], user["email"], user["role"])

    resp = make_response(jsonify({
        "message": "Connexion réussie",
        "user": {"id": user["id"], "email": user["email"], "role": user["role"]},
    }))
    resp.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        samesite="None",
        max_age=SESSION_DURATION_HOURS * 3600,
        secure=False,  # True en production HTTPS
    )
    log_action('LOGIN', details=f"Connexion de {email} depuis {ip_addr}", performed_by=email)
    return resp


@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        delete_session(session_id)
    resp = make_response(jsonify({"message": "Déconnecté"}))
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@app.route('/auth/me', methods=['GET'])
def auth_me():
    user = get_session_user()
    if not user:
        return jsonify({"authenticated": False}), 200
    return jsonify({
        "authenticated": True,
        "user": {
            "id":    user["user_id"],
            "email": user["email"],
            "role":  user["role"],
        },
    })


# ═══════════════════════════════════════════════════════════
#  ROUTES — BLOCKCHAIN STATUS
# ═══════════════════════════════════════════════════════════

@app.route('/chain/status')
def chain_status():
    """
    Route PUBLIQUE — utilisée par verify-cert.html sans login.
    Aussi accessible avec login depuis le dashboard.
    """
    connected = w3.is_connected()
    return jsonify({
        'connected':        connected,
        'web3_version':     w3.api,
        'network':          'Ethereum Testnet (Ganache)' if connected else 'Non connecté',
        'contract_address': None,
        'message':          'Connexion active' if connected else 'Blockchain non disponible',
    })


# ═══════════════════════════════════════════════════════════
#  ROUTES — CERTIFICATS
# ═══════════════════════════════════════════════════════════

@app.route('/certificates', methods=['GET'])
@login_required
def get_certificates():
    """Liste tous les certificats — réservé aux utilisateurs connectés."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM certificates ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify({
        'certificates': [row_to_dict(r) for r in rows],
        'total':        len(rows),
    })


@app.route('/certificates/<cert_id>', methods=['GET'])
@login_required
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
@role_required("admin")
def issue_certificate():
    """Émet un nouveau certificat — admin seulement."""
    data = request.get_json() or {}

    # ─── VALIDATION ───────────────────────────────────────
    errors = {}
    
    # Nom du bénéficiaire
    valid, msg = validate_recipient_name(data.get('recipient_name', ''))
    if not valid:
        errors['recipient_name'] = msg
    
    # Email
    valid, msg = validate_email(data.get('email', ''))
    if not valid:
        errors['email'] = msg
    
    # Programme
    valid, msg = validate_program(data.get('program', ''))
    if not valid:
        errors['program'] = msg
    
    # Date d'émission
    issue_date = data.get('issue_date') or datetime.now().strftime('%Y-%m-%d')
    valid, msg = validate_date(issue_date)
    if not valid:
        errors['issue_date'] = msg
    
    if errors:
        log_action('ISSUE_FAILED', details=f"Validation errors: {errors}", severity='WARNING')
        return jsonify({'error': 'Données invalides', 'details': errors}), 400

    # ─── VÉRIFIER LES DOUBLONS ────────────────────────────
    email = data['email'].lower()
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM certificates WHERE email = ? AND status = 'Vérifié'",
        (email,)
    ).fetchone()
    
    if existing:
        conn.close()
        log_action(
            'ISSUE_REJECTED',
            cert_id=existing['id'],
            details=f"Duplicate certificate for {email}",
            severity='WARNING'
        )
        return jsonify({
            'error': 'Certificat déjà émis pour ce bénéficiaire',
            'existing_cert': existing['id']
        }), 409

    conn.close()

    # ─── GÉNÉRER LE CERTIFICAT ────────────────────────────
    cert_id     = generate_cert_id()
    institution = data.get('institution') or 'SmartCert University'

    hash_payload = {
        'id':             cert_id,
        'recipient_name': data['recipient_name'],
        'email':          email,
        'program':        data['program'],
        'institution':    institution,
        'issue_date':     issue_date,
    }
    
    blockchain_hash = compute_hash(hash_payload)
    tx_hash         = record_on_blockchain(blockchain_hash)

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
            email,
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
        log_action('ISSUE_ERROR', details=f"Database error occurred", severity='ERROR')
        return jsonify({'error': 'Erreur base de données'}), 500
    conn.close()

    cert = {
        'id':              cert_id,
        'recipient_name':  data['recipient_name'],
        'email':           email,
        'program':         data['program'],
        'institution':     institution,
        'issue_date':      issue_date,
        'status':          'Vérifié',
        'blockchain_hash': blockchain_hash,
        'tx_hash':         tx_hash,
    }

    # ─── ENVOI EMAIL AVEC PDF ─────────────────────────────
    email_ok = False
    try:
        from cert_services import generate_certificate_pdf, send_certificate_email
        pdf_buf  = generate_certificate_pdf(cert)
        email_ok = send_certificate_email(cert, pdf_buf)
        log_action(
            'EMAIL_SENT' if email_ok else 'EMAIL_FAILED',
            cert_id,
            email,
            severity='INFO' if email_ok else 'WARNING'
        )
    except ImportError:
        log_action('SERVICE_MISSING', cert_id, 'cert_services.py not found', severity='WARNING')
        print("⚠ cert_services.py introuvable — email non envoyé")
    except Exception as e:
        log_action('EMAIL_ERROR', cert_id, f"Error: {str(e)}", severity='ERROR')
        print(f"⚠ Email/PDF error: {e}")

    log_action('ISSUE', cert_id, f"Émis pour {data['recipient_name']}", severity='INFO')

    return jsonify({
        'message':         'Certificat émis avec succès',
        'cert_id':         cert_id,
        'blockchain_hash': blockchain_hash,
        'tx_hash':         tx_hash,
        'email_sent':      email_ok,
    }), 201


@app.route('/certificates/verify/<cert_id>', methods=['GET'])
def verify_certificate(cert_id):
    """
    Route PUBLIQUE — accessible sans login.
    Utilisée par : verify-cert.html, dashboard_candidat.html
    """
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
    log_action('VERIFY', cert['id'], performed_by='public')

    return jsonify({
        'valid':    is_valid,
        'verified': is_valid,
        'message':  'Certificat valide' if is_valid else f"Certificat {cert['status']}",
        **cert,
    })


@app.route('/certificates/<cert_id>', methods=['DELETE'])
@role_required("admin")
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
@role_required("admin")
def update_status(cert_id):
    """Met à jour le statut d'un certificat avec validation de transition."""
    data       = request.get_json() or {}
    new_status = data.get('status')

    # Valider le nouveau statut
    valid, msg = validate_status(new_status)
    if not valid:
        log_action('STATUS_UPDATE_FAILED', cert_id, f"Invalid status: {new_status}", severity='WARNING')
        return jsonify({'error': msg}), 400

    conn = get_db()
    row  = conn.execute(
        "SELECT id, status FROM certificates WHERE id = ?", (cert_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Certificat introuvable'}), 404

    current_status = row['status']

    # Vérifier si la transition est autorisée
    allowed, msg = can_transition(current_status, new_status)
    if not allowed:
        conn.close()
        log_action(
            'STATUS_TRANSITION_BLOCKED',
            cert_id,
            f"Attempted: {current_status} → {new_status}",
            severity='WARNING'
        )
        return jsonify({'error': msg}), 400

    # Appliquer la transition
    conn.execute("UPDATE certificates SET status = ? WHERE id = ?", (new_status, cert_id))
    conn.commit()
    conn.close()
    
    log_action(
        'STATUS_UPDATE',
        cert_id,
        f"Statut: {current_status} → {new_status}",
        severity='INFO'
    )
    
    return jsonify({
        'message': 'Statut mis à jour',
        'cert_id': cert_id,
        'old_status': current_status,
        'new_status': new_status
    })


# ═══════════════════════════════════════════════════════════
#  ROUTES — PDF & EMAIL
# ═══════════════════════════════════════════════════════════

@app.route('/certificates/<cert_id>/pdf', methods=['GET'])
def download_certificate_pdf(cert_id):
    """
    Génère le PDF du certificat.
    Route PUBLIQUE — accessible depuis verify-cert.html et dashboard_candidat.html
    sans nécessiter de login, car l'ID du certificat fait office d'accès.
    """
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM certificates WHERE id = ?", (cert_id,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Certificat introuvable'}), 404

    cert = row_to_dict(row)

    try:
        from cert_services import generate_certificate_pdf
        pdf_buffer = generate_certificate_pdf(cert)
    except ImportError:
        return jsonify({'error': 'Service PDF non disponible (cert_services.py manquant)'}), 503
    except Exception as e:
        return jsonify({'error': 'Erreur lors de la génération du PDF'}), 500

    log_action('DOWNLOAD_PDF', cert_id, f"PDF → {cert['recipient_name']}", performed_by='public')

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"certificat_{cert_id}.pdf"
    )


@app.route('/certificates/<cert_id>/send-email', methods=['POST'])
@login_required
def send_email_route(cert_id):
    """Renvoie le certificat PDF par email — utilisateurs connectés seulement."""
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM certificates WHERE id = ?", (cert_id,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Certificat introuvable'}), 404

    cert = row_to_dict(row)

    try:
        from cert_services import generate_certificate_pdf, send_certificate_email
        pdf_buffer = generate_certificate_pdf(cert)
        success    = send_certificate_email(cert, pdf_buffer)
    except ImportError:
        return jsonify({'error': 'Service email non disponible (cert_services.py manquant)'}), 503
    except Exception as e:
        return jsonify({'error': 'Erreur lors de l\'envoi de l\'email'}), 500

    if success:
        log_action('EMAIL_SENT', cert_id, f"Email → {cert['email']}")
        return jsonify({'message': f"Email envoyé à {cert['email']}", 'cert_id': cert_id})
    else:
        return jsonify({'error': 'Échec envoi email — vérifiez la config SMTP'}), 500


# ═══════════════════════════════════════════════════════════
#  ROUTES — STATS & AUDIT
# ═══════════════════════════════════════════════════════════

@app.route('/stats', methods=['GET'])
@login_required
def get_stats():
    conn     = get_db()
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


@app.route('/audit', methods=['GET'])
@role_required("admin")
def get_audit():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 100"
    ).fetchall()
    conn.close()
    return jsonify({'logs': [row_to_dict(r) for r in rows]})


# ═══════════════════════════════════════════════════════════
#  LAUNCH
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    # ──── INITIALISATION ────────────────────────────────
    init_db()
    ensure_default_users()
    cleanup_old_attempts()  # Nettoyage initial

    # ──── DÉMARRER LE THREAD DE NETTOYAGE ──────────────
    cleanup_thread = threading.Thread(
        target=cleanup_expired_sessions,
        daemon=True,
        name="SessionCleanupThread"
    )
    cleanup_thread.start()
    print("✅ Session cleanup thread started")

    # ──── VÉRIFICATION DES DÉPENDANCES ─────────────────
    print("\n📋 Vérification des dépendances :")
    
    try:
        from cert_services import _logo
        logo = _logo()
        if not logo:
            print("⚠  logo.png introuvable — certificats sans logo")
            log_action('STARTUP_WARNING', details='Logo not found', severity='WARNING')
        else:
            print("✅ logo.png trouvé")
    except ImportError:
        print("⚠  cert_services.py introuvable — fonctions PDF/Email désactivées")
        log_action('STARTUP_ERROR', details='cert_services.py missing', severity='ERROR')

    # ──── VÉRIFIER CONNEXION BLOCKCHAIN ────────────────
    if w3.is_connected():
        print(f"✅ Blockchain connectée: {w3.eth.chain_id}")
        log_action('STARTUP', details='Blockchain connection OK', severity='INFO')
    else:
        print("⚠  Blockchain non connectée (Ganache indisponible)")
        log_action('STARTUP_WARNING', details='Blockchain not available', severity='WARNING')

    # ──── AFFICHER INFO DÉMARRAGE ───────────────────────
    print("\n" + "="*60)
    print("🚀 SmartCert API démarrée")
    print("=" * 60)
    print(f"📡 URL: http://127.0.0.1:5000")
    print(f"🔐 Debug mode: {app.debug}")
    print(f"🔄 Session duration: {SESSION_DURATION_HOURS} hours")
    print(f"🚫 Max login attempts: {MAX_LOGIN_ATTEMPTS} / {ATTEMPT_WINDOW_MINUTES} min")
    print("\n📋 Comptes de test :")
    print("   👤 Admin:     admin@smartcert.tn / admin123")
    print("   👨‍🎓 Étudiant:  etudiant@smartcert.tn / etudiant123")
    print("\n" + "="*60 + "\n")

    app.run(debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true', host='0.0.0.0', port=5000, use_reloader=True)
