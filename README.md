# Projet_PFA

Système sécurisé de gestion et de vérification de certificats basé sur la blockchain

Titre du Projet: SmartCert

Besoin réel : Les institutions  éducatives souhaitent disposer d’un système fiable et sécurisé pour  émettre et vérifier des certificats numériques 

Changements apportés : Suppression de la dépendance aux processus administratifs manuels, réduction des risques de fraude, accélération des vérifications et amélioration de l’expérience utilisateur.

Idée globale : Création d’une application web intégrant une blockchain (Ethereum Testnet) pour l’émission et la vérification de certificats numériques s ́ecurisés, avec une interface intuitive accessible via navigateur.

Fonctionnalités principales :
• Emission de certificats avec identifiant unique et cachet numérique 
• Vérification en temps réel via un lien de vérification
• Gestion des certificats via une interface web sécurisée
• Enregistrement automatique sur la blockchain via MetaMask
• Fonctionnalités secondaires :
• Téléchargement du certificat au format PDF 
• Envoi d’email automatique au bénéficiaire
• Innovation : Combinaison de technologies web (Flask) et blockchain (Web3.py) pour une solution robuste, s ́ecuris ́ee et  ́evolutive .



• Technologies utilisées :
• Frontend : HTML + CSS + JavaScript...
• Backend : Python + Flask
• Base de donn ́ees : SQLite
• Blockchain : Ethereum Testnet + Web3.py 
• Portefeuille : MetaMask



5 Intégration d’un Chatbot via n8n
• Assistance automatisée aux utilisateurs
• Réponses aux questions fréquentes sur les certificats
• Vérification guidée d’un certificat via son identifiant
 Fonctionnement technique :
• Le chatbot est implémenté à l’aide de workflows n8n
• Communication avec l’application Flask via des API REST



---

## 🚀 Démarrage rapide

### 1. Prérequis

```bash
pip install flask flask-cors werkzeug web3
```

### 2. Initialiser la base de données et démarrer le backend

```bash
cd backend
python app.py
```

Cela va :
- Créer `database.db` avec toutes les tables (certificates, audit_log, users, sessions)
- Insérer les comptes démo par défaut
- Démarrer l'API sur http://127.0.0.1:5000

### 3. Ouvrir le frontend

Ouvrez `frontend/login.html` dans votre navigateur (via un serveur local comme Live Server sur le port 5500).

---

## 🔐 Comptes démo

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| Admin | admin@smartcert.tn | admin123 |
| Étudiant | etudiant@smartcert.tn | etudiant123 |

---

## 🔒 Authentification & Sécurité

- **Sessions serveur** : chaque connexion crée une entrée dans la table `sessions` (SQLite), valable 8 heures.
- **Cookie HttpOnly** : `smartcert_session` — non accessible via JavaScript.
- **Mots de passe hachés** avec Werkzeug (PBKDF2-SHA256).
- **Décorateurs de protection** :
  - `@login_required` — nécessite une session valide
  - `@role_required("admin")` — réservé aux administrateurs

### Routes protégées

| Endpoint | Méthode | Protection |
|----------|---------|------------|
| `/auth/login` | POST | Public |
| `/auth/logout` | POST | Public |
| `/auth/me` | GET | Public |
| `/certificates` | GET | Authentifié |
| `/certificates` | POST | Admin seulement |
| `/certificates/<id>` | DELETE | Admin seulement |
| `/certificates/<id>/status` | PATCH | Admin seulement |
| `/certificates/verify/<id>` | GET | Authentifié |
| `/stats` | GET | Authentifié |
| `/audit` | GET | Admin seulement |
| `/chain/status` | GET | Authentifié |

---

## 🧪 Test manuel des endpoints

```bash
# Login admin
curl -c cookies.txt -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@smartcert.tn","password":"admin123"}'

# Accéder aux certificats (avec cookie)
curl -b cookies.txt http://127.0.0.1:5000/certificates

# Vérifier la session
curl -b cookies.txt http://127.0.0.1:5000/auth/me

# Logout
curl -b cookies.txt -c cookies.txt -X POST http://127.0.0.1:5000/auth/logout
```
