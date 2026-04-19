"""
SmartCert — init_db.py
Initialise la base de données SQLite certificates.db
"""

import sqlite3
import hashlib
import json
import os
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'certificates.db')

# ─── SCHEMA ───────────────────────────────────────────────
SCHEMA = """
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
"""

# ─── DONNÉES DE TEST ──────────────────────────────────────
SAMPLE_CERTS = [
    {
        'recipient_name': 'Ahmed Ben Ali',
        'email':          'ahmed.benali@email.tn',
        'program':        'Licence en Informatique',
        'institution':    'Université de Tunis',
        'issue_date':     '2024-06-15',
        'status':         'Vérifié',
    },
    {
        'recipient_name': 'Sana Trabelsi',
        'email':          'sana.trabelsi@email.tn',
        'program':        'Master en Génie Logiciel',
        'institution':    'INSAT Tunis',
        'issue_date':     '2024-07-20',
        'status':         'Vérifié',
    },
    {
        'recipient_name': 'Mohamed Gharbi',
        'email':          'm.gharbi@email.tn',
        'program':        "Diplôme d'Ingénieur en Réseaux",
        'institution':    'ENIT',
        'issue_date':     '2024-09-01',
        'status':         'En attente',
    },
    {
        'recipient_name': 'Rania Khelifi',
        'email':          'r.khelifi@mail.tn',
        'program':        'Licence en Data Science',
        'institution':    'Université de Sfax',
        'issue_date':     '2024-05-10',
        'status':         'Vérifié',
    },
    {
        'recipient_name': 'Yassine Mansour',
        'email':          'y.mansour@mail.tn',
        'program':        'Master en Intelligence Artificielle',
        'institution':    'ESPRIT',
        'issue_date':     '2024-10-05',
        'status':         'Révoqué',
    },
]


# ─── FONCTIONS UTILITAIRES ────────────────────────────────

def generate_cert_id() -> str:
    """Génère un identifiant unique CERT-YYYY-XXXXXX."""
    year  = datetime.now().year
    short = str(uuid.uuid4()).upper()[:6]
    return f"CERT-{year}-{short}"


def compute_hash(data: dict) -> str:
    """Calcule le hash SHA-256 des données du certificat."""
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return "0x" + hashlib.sha256(payload.encode()).hexdigest()


def fake_tx_hash(blockchain_hash: str) -> str:
    """Génère un tx_hash simulé (avant connexion Ethereum réelle)."""
    return "0xtx_" + hashlib.md5(blockchain_hash.encode()).hexdigest()


# ─── FONCTION PRINCIPALE ──────────────────────────────────
def init_db():
    print(f"📁 Base de données : {DATABASE}")
    conn   = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Créer les tables
    cursor.executescript(SCHEMA)
    print("✅ Tables créées (certificates + audit_log + users + sessions)")

    # Comptes démo
    from werkzeug.security import generate_password_hash
    defaults = [
        ("admin@smartcert.tn",    "admin123",    "admin"),
        ("etudiant@smartcert.tn", "etudiant123", "etudiant"),
    ]
    for email, pw, role in defaults:
        pw_hash = generate_password_hash(pw)
        cursor.execute(
            "INSERT OR IGNORE INTO users (email, password_hash, role) VALUES (?, ?, ?)",
            (email.lower(), pw_hash, role),
        )
    print("✅ Comptes démo créés : admin@smartcert.tn / etudiant@smartcert.tn")

    # Insérer les certificats de test
    inserted = 0
    for cert in SAMPLE_CERTS:
        cert_id = generate_cert_id()
        hash_payload = {
            'id':             cert_id,
            'recipient_name': cert['recipient_name'],
            'email':          cert['email'],
            'program':        cert['program'],
            'institution':    cert['institution'],
            'issue_date':     cert['issue_date'],
        }
        blockchain_hash = compute_hash(hash_payload)
        tx_hash         = fake_tx_hash(blockchain_hash)

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO certificates
                (id, recipient_name, email, program, institution,
                 issue_date, status, blockchain_hash, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cert_id,
                cert['recipient_name'],
                cert['email'],
                cert['program'],
                cert['institution'],
                cert['issue_date'],
                cert['status'],
                blockchain_hash,
                tx_hash,
            ))
            inserted += 1
            print(f"  ➕ {cert_id} — {cert['recipient_name']} [{cert['status']}]")

            cursor.execute(
                "INSERT INTO audit_log (action, cert_id, details) VALUES (?, ?, ?)",
                ('INIT', cert_id, f"Certificat créé pour {cert['recipient_name']}")
            )
        except Exception as e:
            print(f"  ⚠ Erreur : {e}")

    conn.commit()
    conn.close()
    print(f"\n🎉 Terminé : {inserted} certificats insérés dans certificates.db")
    print("▶ Lancez le backend : python app.py")


if __name__ == '__main__':
    init_db()
