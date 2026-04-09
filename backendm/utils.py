"""
SmartCert — utils.py
Utilitaires partagés entre init_db.py et app.py
"""

import hashlib
import json
import uuid
import os
from datetime import datetime

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
