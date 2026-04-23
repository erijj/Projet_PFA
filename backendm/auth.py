"""
SmartCert — auth.py
Blueprint d'authentification : login, logout, vérification JWT,
protection des routes par rôle, journalisation des accès.

Intégration dans app.py :
    from auth import auth_bp
    app.register_blueprint(auth_bp)

Dépendances :
    pip install PyJWT flask flask-cors werkzeug
"""

from flask import Blueprint, jsonify, request, g
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import time
import jwt
import os
from datetime import datetime, timedelta

# ─── BLUEPRINT ────────────────────────────────────────────
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# ─── CONFIG ───────────────────────────────────────────────
JWT_SECRET   = os.getenv("JWT_SECRET", "smartcert-dev-secret-CHANGE-IN-PROD")
JWT_ALGO     = "HS256"
JWT_EXPIRY_H = int(os.getenv("JWT_EXPIRY_HOURS", 8))
# Fix P11: use certificates.db to match the rest of the backend
DATABASE     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "certificates.db")

# ─── UTILISATEURS ─────────────────────────────────────────
# Les utilisateurs sont désormais gérés dans la base de données (table 'users').

def get_user_by_email(email: str):
    """Récupère un utilisateur depuis la base de données."""
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        return dict(user) if user else None
    except sqlite3.Error as e:
        print(f"Database error in get_user_by_email: {e}")
        return None



# ═══════════════════════════════════════════════════════════
#  HELPERS JWT
# ═══════════════════════════════════════════════════════════

def generate_token(email: str, role: str) -> str:
    """Génère un JWT signé avec expiration."""
    payload = {
        "email": email,
        "role":  role,
        "iat":   datetime.utcnow(),
        "exp":   datetime.utcnow() + timedelta(hours=JWT_EXPIRY_H),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token: str) -> dict:
    """Décode et valide un JWT. Lève jwt.ExpiredSignatureError ou jwt.InvalidTokenError."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])


def extract_token() -> str | None:
    """Extrait le Bearer token depuis l'en-tête Authorization ou le paramètre ?token=."""
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    # Also accept token as a query-string parameter (used for window.open PDF downloads)
    return request.args.get("token") or None


# ─── DÉCORATEUR DE PROTECTION ─────────────────────────────
def require_auth(roles: list[str] | None = None):
    """
    Décorateur qui protège une route Flask.

    Usage :
        @app.route('/admin/stats')
        @require_auth(roles=['admin'])
        def stats(): ...

        @app.route('/profile')
        @require_auth()         # tout utilisateur connecté
        def profile(): ...

    Injecte g.user = {'email': ..., 'role': ...} si valide.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = extract_token()
            if not token:
                return jsonify({"error": "Token manquant", "code": "missing_token"}), 401

            try:
                payload = decode_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Session expirée", "code": "session_expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Token invalide", "code": "invalid_token"}), 401

            if roles and payload.get("role") not in roles:
                return jsonify({"error": "Accès refusé — rôle insuffisant", "code": "forbidden"}), 403

            g.user = payload
            return f(*args, **kwargs)
        return decorated
    return decorator


# ─── JOURNALISATION ───────────────────────────────────────
def _log_auth(action: str, email: str, role: str, ip: str):
    """Insère une entrée dans audit_log (silencieux si la BDD n'est pas dispo)."""
    try:
        conn = sqlite3.connect(DATABASE)
        conn.execute(
            "INSERT INTO audit_log (action, performed_by, details) VALUES (?, ?, ?)",
            (action, email, f"rôle={role} ip={ip}"),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"⚠ Auth log error: {e}")


# ═══════════════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════════════

# ─── POST /auth/login ──────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Corps JSON attendu : { "email": "...", "password": "..." }
    Retourne : { "token": "...", "user": {...}, "expires_in": 28800 }
    """
    data     = request.get_json(silent=True) or {}
    email    = data.get("email", "").lower().strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    user = get_user_by_email(email)
    
    if not user or not check_password_hash(user["password_hash"], password):
        time.sleep(0.4)  # délai anti-brute-force
        return jsonify({"error": "Email ou mot de passe incorrect", "code": "invalid_credentials"}), 401


    token = generate_token(email, user["role"])
    ip    = request.remote_addr or "unknown"
    _log_auth("LOGIN", email, user["role"], ip)

    return jsonify({
        "token":      token,
        "user": {
            "email": email,
            "role":  user["role"],
            "name":  user["name"],
        },
        "expires_in": JWT_EXPIRY_H * 3600,
    })


# ─── POST /auth/logout ─────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
@require_auth()
def logout():
    """
    Invalide la session côté audit (le JWT reste techniquement valide
    jusqu'à expiration — en prod : utiliser une blacklist Redis).
    """
    email = g.user.get("email", "?")
    role  = g.user.get("role", "?")
    ip    = request.remote_addr or "unknown"
    _log_auth("LOGOUT", email, role, ip)
    return jsonify({"message": "Déconnecté avec succès"})


@auth_bp.route("/me", methods=["GET"])
@require_auth()
def me():
    """Retourne le profil de l'utilisateur actuellement connecté."""
    email = g.user.get("email", "")
    user  = get_user_by_email(email)
    
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    return jsonify({
        "authenticated": True,
        "email":         email,
        "role":          g.user.get("role"),
        "name":          user.get("name", ""),
        "user": {
            "email": email,
            "role":  g.user.get("role"),
            "name":  user.get("name", ""),
        },
    })



# ─── GET /auth/verify-token ────────────────────────────────
@auth_bp.route("/verify-token", methods=["GET"])
def verify_token():
    """
    Vérifie la validité d'un JWT sans nécessiter d'état serveur.
    Retourne : { "valid": true, "user": {...} }
    """
    token = extract_token()
    if not token:
        return jsonify({"valid": False, "error": "Token manquant", "code": "missing_token"}), 401

    try:
        payload = decode_token(token)
        return jsonify({
            "valid": True,
            "user": {
                "email": payload.get("email"),
                "role":  payload.get("role"),
            },
        })
    except jwt.ExpiredSignatureError:
        return jsonify({"valid": False, "error": "Session expirée", "code": "session_expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"valid": False, "error": "Token invalide", "code": "invalid_token"}), 401


# ─── GET /auth/sessions (admin seulement) ─────────────────
@auth_bp.route("/sessions", methods=["GET"])
@require_auth(roles=["admin"])
def list_sessions():
    """Retourne les dernières entrées d'audit (connexions/déconnexions)."""
    try:
        conn  = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        rows  = conn.execute(
            "SELECT * FROM audit_log WHERE action IN ('LOGIN','LOGOUT') "
            "ORDER BY timestamp DESC LIMIT 50"
        ).fetchall()
        conn.close()
        return jsonify({"sessions": [dict(r) for r in rows]})
    except sqlite3.Error as e:
        print(f"⚠ Sessions query error: {e}")
        return jsonify({"error": "Erreur interne lors de la récupération des sessions"}), 500
