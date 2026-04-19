"""
SmartCert — utils.py
Utilitaires partagés entre init_db.py et app.py
Inclut: validation, génération ID, hash, et helpers
"""

import hashlib
import json
import uuid
import os
import re
from datetime import datetime, timezone

# ─── CHEMIN BASE DE DONNÉES ───────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'certificates.db')


# ─── GÉNÉRATION ID ────────────────────────────────────────
def generate_cert_id() -> str:
    """Génère un identifiant unique CERT-YYYY-XXXXXX."""
    year  = datetime.now().year
    short = str(uuid.uuid4()).upper()[:6]
    return f"CERT-{year}-{short}"


# ─── HASH SHA-256 ─────────────────────────────────────────
def compute_hash(data: dict) -> str:
    """Calcule le hash SHA-256 des données du certificat."""
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return "0x" + hashlib.sha256(payload.encode()).hexdigest()


# ─── TX HASH SIMULÉ ───────────────────────────────────────
def fake_tx_hash(blockchain_hash: str) -> str:
    """Génère un tx_hash simulé (avant connexion Ethereum réelle)."""
    return "0xtx_" + hashlib.md5(blockchain_hash.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════
#  VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════

VALID_STATUSES = ['Vérifié', 'En attente', 'Révoqué']
MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 255
MAX_PROGRAM_LENGTH = 200

ALLOWED_TRANSITIONS = {
    'En attente': ['Vérifié', 'Révoqué'],
    'Vérifié': ['Révoqué'],
    'Révoqué': []  # Une fois révoquée, elle reste révoquée
}


def validate_email(email: str) -> tuple[bool, str]:
    """
    Valide le format d'un email.
    Retourne: (is_valid, error_message)
    """
    email = email.strip().lower()
    
    if not email or len(email) > MAX_EMAIL_LENGTH:
        return False, f"Email invalide (max {MAX_EMAIL_LENGTH} caractères)"
    
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._%-]*[a-zA-Z0-9]@[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Format d'email invalide"
    
    return True, ""


def validate_recipient_name(name: str) -> tuple[bool, str]:
    """
    Valide le nom du bénéficiaire.
    Retourne: (is_valid, error_message)
    """
    name = (name or "").strip()
    
    if not name:
        return False, "Nom du bénéficiaire requis"
    
    if len(name) > MAX_NAME_LENGTH:
        return False, f"Nom trop long (max {MAX_NAME_LENGTH} caractères)"
    
    if len(name) < 2:
        return False, "Nom trop court (minimum 2 caractères)"
    
    # Vérifier que contient surtout des lettres et espaces
    if not re.match(r'^[a-zA-ZÀ-ÿ\s\-\.]{2,}$', name):
        return False, "Nom contient des caractères invalides"
    
    return True, ""


def validate_date(date_str: str) -> tuple[bool, str]:
    """
    Valide une date au format YYYY-MM-DD.
    Retourne: (is_valid, error_message)
    """
    date_str = (date_str or "").strip()
    
    if not date_str:
        return False, "Date requise"
    
    try:
        parsed = datetime.strptime(date_str, '%Y-%m-%d')
        # Vérifier que la date ne soit pas dans le futur
        if parsed.date() > datetime.now().date():
            return False, "La date ne peut pas être dans le futur"
        return True, ""
    except ValueError:
        return False, "Format de date invalide (utilisez YYYY-MM-DD)"


def validate_program(program: str) -> tuple[bool, str]:
    """
    Valide le nom du programme.
    Retourne: (is_valid, error_message)
    """
    program = (program or "").strip()
    
    if not program:
        return False, "Programme requis"
    
    if len(program) > MAX_PROGRAM_LENGTH:
        return False, f"Programme trop long (max {MAX_PROGRAM_LENGTH} caractères)"
    
    if len(program) < 2:
        return False, "Programme trop court (minimum 2 caractères)"
    
    return True, ""


def validate_status(status: str) -> tuple[bool, str]:
    """
    Valide le statut d'un certificat.
    Retourne: (is_valid, error_message)
    """
    if not status or status not in VALID_STATUSES:
        return False, f"Statut invalide. Acceptés: {', '.join(VALID_STATUSES)}"
    return True, ""


def can_transition(from_status: str, to_status: str) -> tuple[bool, str]:
    """
    Vérifie si une transition de statut est autorisée.
    Retourne: (is_allowed, error_message)
    """
    allowed = ALLOWED_TRANSITIONS.get(from_status, [])
    if to_status not in allowed:
        return False, f"Transition non autorisée: {from_status} → {to_status}"
    return True, ""


def get_utc_now() -> str:
    """Retourne l'heure actuelle en UTC format ISO."""
    return datetime.now(timezone.utc).isoformat()
