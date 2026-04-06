"""
SmartCert — init_db.py
initialiser la base de données SQLite database.db
"""

import sqlite3
import hashlib
import json
import os
import uuid
from datetime import datetime
"""الأصلي — فيه زيادة imports
from datetime import datetime, timedelta  # timedelta ما تستعملتش
import random                            # ما تستعملتش 
"""


# المسار — نفس مجلد init_db.py

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')


# SCHEMA — جدولين

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
    details      TEXT
);
"""


# بيانات تجريبية — تتوافق مع الـ Dashboard

SAMPLE_CERTS = [ #حذفت شهادتين (lina,omar)
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


# توليد ID فريد — CERT-2026-XXXXXX

def generate_cert_id() -> str: #  'index' n'est pas utilisé, peut ètre supprimé .
    year  = datetime.now().year
    short = str(uuid.uuid4()).upper()[:6]
    return f"CERT-{year}-{short}"


# توليد blockchain_hash من بيانات الشهادة

def compute_blockchain_hash(data: dict) -> str: # le nom de la fonction est changé de 'compute_hash' en 'compute_blockchain_hash' pour être plus explicite et éviter toute confusion avec d'autres types de hash qui pourraient être utilisés dans le projet.
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return "0x" + hashlib.sha256(payload.encode()).hexdigest()


# توليد tx_hash وهمي (قبل ربط Ethereum حقيقي)

def fake_tx_hash(blockchain_hash: str) -> str:
    return "0xtx_" + hashlib.md5(blockchain_hash.encode()).hexdigest()


# الفونكسيون الرئيسية

def init_db():
    print(f"📁 Base de données : {DATABASE}")
    conn   = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # إنشاء الجدولين
    cursor.executescript(SCHEMA)
    print("✅ Tables créées (certificates + audit_log)")

    # إدخال البيانات التجريبية
    inserted = 0
    for cert in SAMPLE_CERTS:
        cert_id = generate_cert_id()

        # البيانات اللي يتحسب منها الـ hash
        hash_payload = {
            'id':             cert_id,
            'recipient_name': cert['recipient_name'],
            'email':          cert['email'],
            'program':        cert['program'],
            'institution':    cert['institution'],
            'issue_date':     cert['issue_date'],
        }

        blockchain_hash = compute_blockchain_hash(hash_payload)
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

            # سجل في audit_log
            cursor.execute("""
                INSERT INTO audit_log (action, cert_id, details)
                VALUES (?, ?, ?)
            """, ('INIT', cert_id, f"Certificat créé pour {cert['recipient_name']}"))
            
            #الكود الاصلي:cursor.execute("""
    # INSERT INTO audit_log (action, cert_id, details)
    # VALUES (?, ?, ?)
# """, ('INIT', cert_id, f"Certificat créé pour {cert['recipient_name']}"))

        except Exception as e:
            print(f"  ⚠ Erreur : {e}")

    conn.commit()
    conn.close()
    print(f"\n🎉 Terminé : {inserted} certificats insérés dans database.db")
    print("▶ Lancez le backend : python app.py")


if __name__ == '__main__':
    init_db()
