"""
SmartCert — init_db.py
Script pour initialiser la base de données SQLite
et insérer des données de test.

Usage :
    python init_db.py
"""

import sqlite3
import hashlib
import json
import os
from datetime import datetime, timedelta
import random
import uuid

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

# ─── SCHÉMA ───────────────────────────────────────────────
SCHEMA = """
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
    log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    action       TEXT NOT NULL,
    cert_id      TEXT,
    performed_by TEXT DEFAULT 'admin',
    timestamp    TEXT DEFAULT (datetime('now')),
    details      TEXT
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
        'program':        'Diplôme d\'Ingénieur en Réseaux',
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
    {
        'recipient_name': 'Lina Bouaziz',
        'email':          'lina.b@student.tn',
        'program':        'Licence en Cybersécurité',
        'institution':    'Université de Carthage',
        'issue_date':     '2025-01-18',
        'status':         'Vérifié',
    },
    {
        'recipient_name': 'Omar Slimani',
        'email':          'o.slimani@mail.tn',
        'program':        'Formation DevOps & Cloud',
        'institution':    'ISET Sousse',
        'issue_date':     '2025-03-01',
        'status':         'En attente',
    },
]


def compute_hash(data: dict) -> str:
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return "0x" + hashlib.sha256(payload.encode()).hexdigest()


def fake_tx_hash(cert_hash: str) -> str:
    return "0xtx_" + hashlib.md5(cert_hash.encode()).hexdigest()


def generate_cert_id(index: int) -> str:
    year = datetime.now().year
    short = str(uuid.uuid4()).upper()[:6]
    return f"CERT-{year}-{short}"


def init_db():
    print(f"📁 Base de données : {DATABASE}")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Créer les tables
    cursor.executescript(SCHEMA)
    print("✅ Tables créées")

    # Insérer les données de test
    inserted = 0
    for i, cert in enumerate(SAMPLE_CERTS):
        cert_id = generate_cert_id(i)
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
        except Exception as e:
            print(f"  ⚠ Erreur : {e}")

    # Log d'audit initial
    cursor.execute("""
        INSERT INTO audit_log (action, cert_id, details)
        VALUES ('INIT', NULL, 'Base de données initialisée avec données de test')
    """)

    conn.commit()
    conn.close()

    print(f"\n🎉 Terminé : {inserted} certificats insérés dans database.db")
    print("▶ Lancez le backend : python app.py")


if __name__ == '__main__':
    init_db()