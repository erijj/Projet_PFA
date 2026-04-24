# SmartCert — Diagrammes UML (Version Française)

> Tous les diagrammes sont dérivés directement du code source de la branche principale (`app.py`, `auth.py`, `cert_services.py`, `login.js`).

---

## 1. Diagramme de Séquence — Authentification & Émission de Certificat

Ce diagramme couvre trois scénarios : la connexion d'un utilisateur, l'émission d'un certificat avec enregistrement blockchain et envoi automatique d'e-mail, puis la vérification publique.

```mermaid
sequenceDiagram
    autonumber
    actor Utilisateur
    participant Navigateur as "Navigateur (login.js)"
    participant Serveur as "API Flask (app.py / auth.py)"
    participant BaseDeDonnees as "SQLite (certificates.db)"
    participant Blockchain as "Testnet Ethereum (Web3.py)"
    participant ServeurEmail as "Serveur SMTP (Gmail)"

    %% ── Phase 1 : Connexion ───────────────────────────────
    rect rgb(232, 244, 232)
        Note over Utilisateur, BaseDeDonnees: Phase 1 — Connexion (POST /auth/login)
        Utilisateur->>Navigateur: Saisit adresse e-mail + mot de passe
        Navigateur->>Serveur: POST /auth/login { email, motDePasse }
        Serveur->>BaseDeDonnees: SELECT * FROM utilisateurs WHERE email = ?
        BaseDeDonnees-->>Serveur: Enregistrement utilisateur (hashMotDePasse, role, nom)
        Serveur->>Serveur: verifier_hash_mdp(hash_stocke, motDePasse)
        alt Identifiants valides
            Serveur->>Serveur: generer_jeton(email, role) → JWT (HS256, 8h)
            Serveur->>BaseDeDonnees: INSERT INTO journal_audit (action='CONNEXION', ...)
            Serveur-->>Navigateur: { jeton, utilisateur:{email, role, nom}, expireEn }
            Navigateur->>Navigateur: localStorage.setItem('smartcert_token', jeton)
            alt role == 'admin'
                Navigateur->>Utilisateur: Redirection → tableau-de-bord-admin.html
            else role == 'etudiant'
                Navigateur->>Utilisateur: Redirection → tableau-de-bord-candidat.html
            end
        else Identifiants invalides
            Serveur->>Serveur: time.sleep(0.4) [anti-force-brute]
            Serveur-->>Navigateur: 401 { erreur: "Adresse e-mail ou mot de passe incorrect" }
            Navigateur->>Utilisateur: Affiche alerte d'erreur
        end
    end

    %% ── Phase 2 : Émission d'un certificat ───────────────
    rect rgb(224, 247, 250)
        Note over Utilisateur, ServeurEmail: Phase 2 — Émission d'un certificat (POST /certificates)
        Utilisateur->>Navigateur: Remplit le formulaire d'émission
        Navigateur->>Serveur: POST /certificates { nom_destinataire, email, programme, ... }\n Autorisation: Bearer <JWT>
        Serveur->>Serveur: exiger_auth(roles=['admin'])\n → decrypter_jeton(JWT) → g.utilisateur
        Serveur->>Serveur: generer_id_cert() → "CERT-2026-XXXXXX"
        Serveur->>Serveur: calculer_hash(donnees) → hash_blockchain SHA-256
        Serveur->>Blockchain: envoyer_transaction({ de, vers, donnees: hash })
        alt Ganache connecté
            Blockchain-->>Serveur: hash_transaction (0x...)
        else Non connecté
            Serveur->>Serveur: repli → "0xtx_" + SHA256[:32]
        end
        Serveur->>BaseDeDonnees: INSERT INTO certificats (id, nom_destinataire, email,\n programme, institution, date_emission, nom_directeur,\n statut='Vérifié', hash_blockchain, hash_tx, cree_par)
        Serveur->>Serveur: generer_pdf_certificat(cert) → BytesIO (ReportLab)
        Serveur->>ServeurEmail: envoyer_email_certificat(cert, tampon_pdf)
        alt SMTP configuré
            ServeurEmail-->>Serveur: E-mail envoyé avec succès
            Serveur->>BaseDeDonnees: INSERT INTO journal_audit (action='EMAIL_ENVOYE')
        else SMTP non configuré
            Serveur->>BaseDeDonnees: INSERT INTO journal_audit (action='EMAIL_ECHOUE')
        end
        Serveur->>BaseDeDonnees: INSERT INTO journal_audit (action='EMISSION', id_cert, ...)
        Serveur-->>Navigateur: 201 { message, id_cert, hash_blockchain, hash_tx, email_envoye }
        Navigateur->>Utilisateur: Affiche confirmation + identifiant du certificat
    end

    %% ── Phase 3 : Vérification publique ──────────────────
    rect rgb(255, 243, 224)
        Note over Utilisateur, BaseDeDonnees: Phase 3 — Vérification publique (GET /certificates/verify/<id_cert>)
        Utilisateur->>Navigateur: Saisit l'identifiant ou le hash blockchain du certificat
        Navigateur->>Serveur: GET /certificates/verify/<id_cert> [route publique, sans JWT]
        Serveur->>BaseDeDonnees: SELECT * FROM certificats WHERE id=? OU hash_blockchain=?
        alt Certificat trouvé
            BaseDeDonnees-->>Serveur: Données du certificat
            Serveur->>Serveur: est_valide = (statut == 'Vérifié')
            Serveur-->>Navigateur: { valide, verifie, message, ...donnees_cert }
            Navigateur->>Utilisateur: Affiche badge ✅ Valide ou ❌ Révoqué
        else Certificat introuvable
            Serveur-->>Navigateur: 404 { valide: false, message: 'Aucun certificat trouvé' }
            Navigateur->>Utilisateur: Affiche message d'erreur
        end
    end
```

---

## 2. Diagramme de Classes — Architecture du Système

Ce diagramme représente tous les modules Python, les tables SQLite, le client blockchain et le frontend JavaScript avec leurs responsabilités et leurs relations.

```mermaid
classDiagram
    direction LR

    class ApplicationFlask {
        +application: Flask
        +clientWeb3: Web3
        +CHEMIN_BDD: str
        +FOURNISSEUR_WEB3: str
        +obtenir_bdd() Connexion
        +initialiser_bdd() vide
        +generer_id_certificat() str
        +calculer_hash(donnees) str
        +enregistrer_blockchain(hash) str
        +journaliser_action(action, id_cert, details) vide
        +ligne_vers_dict(ligne) dict
    }

    class BlueprintAuthentification {
        +SECRET_JWT: str
        +ALGO_JWT: str = "HS256"
        +DUREE_JWT_H: int = 8
        +CHEMIN_BDD: str
        +obtenir_utilisateur_par_email(email) dict
        +generer_jeton(email, role) str
        +decrypter_jeton(jeton) dict
        +extraire_jeton() str
        +exiger_auth(roles) Decorateur
        +journaliser_auth(action, email, role, ip) vide
    }

    class RoutesCertificats {
        <<Routes Flask - Certificats>>
        +POST /certificates [admin]
        +GET /certificates [authentifie]
        +GET /certificates-{id} [authentifie]
        +DELETE /certificates-{id} [admin]
        +PATCH /certificates-{id}-statut [admin]
        +GET /certificates-verify-{id} [public]
        +GET /certificates-{id}-pdf [authentifie]
        +POST /certificates-{id}-envoyer-email [admin]
    }

    class RoutesAuthentification {
        <<Blueprint /auth>>
        +POST /auth/inscrire
        +POST /auth/connexion
        +POST /auth/deconnexion [authentifie]
        +GET /auth/moi [authentifie]
        +GET /auth/verifier-jeton
        +GET /auth/sessions [admin]
    }

    class RoutesStatistiques {
        <<Routes Flask - Stats et Audit>>
        +GET /stats [authentifie]
        +GET /audit [admin]
        +GET /chaine/statut [authentifie]
    }

    class ServicesCertificats {
        +HOTE_SMTP: str
        +PORT_SMTP: int
        +UTILISATEUR_SMTP: str
        +MOT_DE_PASSE_SMTP: str
        +generer_pdf_certificat(cert) BytesIO
        +envoyer_email_certificat(cert, pdf) bool
        -html_email(cert) str
        -chemin_logo() str
    }

    class Certificat {
        <<Table SQLite : certificates>>
        +id: TEXTE CleP
        +nom_destinataire: TEXTE
        +email: TEXTE
        +programme: TEXTE
        +institution: TEXTE
        +date_emission: TEXTE
        +nom_directeur: TEXTE
        +statut: TEXTE
        +hash_blockchain: TEXTE
        +hash_tx: TEXTE
        +cree_par: TEXTE
        +cree_le: TEXTE
    }

    class Utilisateur {
        <<Table SQLite : users>>
        +id: ENTIER CleP
        +email: TEXTE UNIQUE
        +hash_mdp: TEXTE
        +role: TEXTE
        +nom: TEXTE
        +cree_le: TEXTE
    }

    class JournalAudit {
        <<Table SQLite : audit_log>>
        +id_log: ENTIER CleP
        +action: TEXTE
        +id_cert: TEXTE
        +realise_par: TEXTE
        +horodatage: TEXTE
        +details: TEXTE
    }

    class ClientBlockchain {
        <<Externe : Ganache / Ethereum>>
        +est_connecte() bool
        +eth.comptes: liste
        +eth.envoyer_transaction(tx) octets
    }

    class InterfaceLoginJS {
        <<JavaScript : login.js>>
        +roleActuel: chaine
        +changerRole(role) vide
        +seConnecter() async vide
        +sInscrire() async vide
        +afficherAlerte(id, msg) vide
        +afficherMentionsLegales(type) vide
    }

    ApplicationFlask --> RoutesCertificats : definit
    ApplicationFlask --> RoutesStatistiques : definit
    ApplicationFlask --> BlueprintAuthentification : register_blueprint()
    BlueprintAuthentification --> RoutesAuthentification : definit
    ApplicationFlask --> ServicesCertificats : importe
    ApplicationFlask --> ClientBlockchain : utilise via Web3.py
    RoutesCertificats --> Certificat : CRUD SQLite
    RoutesCertificats --> JournalAudit : INSERT
    BlueprintAuthentification --> Utilisateur : SELECT et INSERT
    BlueprintAuthentification --> JournalAudit : INSERT connexion/deconnexion
    ServicesCertificats --> Certificat : lit les champs
    InterfaceLoginJS --> RoutesAuthentification : fetch() HTTP
    InterfaceLoginJS --> RoutesCertificats : fetch() HTTP
```

---

## 3. Diagramme d'États — Cycle de Vie d'un Certificat

Ce diagramme modélise tous les états possibles d'un objet `Certificat` depuis sa création jusqu'à sa suppression définitive, avec les transitions déclenchées par les actions administrateur, la blockchain et le système d'e-mail.

```mermaid
stateDiagram-v2
    [*] --> FormulaireRempli : L'administrateur remplit le formulaire d'émission

    FormulaireRempli --> ValidationChamps : Soumission → POST /certificates
    ValidationChamps --> ErreurValidation : Champ obligatoire manquant\n(nom_destinataire, email, programme)
    ErreurValidation --> FormulaireRempli : L'administrateur corrige le formulaire

    ValidationChamps --> GenerationHash : Tous les champs sont valides
    GenerationHash --> EnregistrementBlockchain : calculer_hash() → SHA-256

    state EnregistrementBlockchain {
        [*] --> TentativeTransaction
        TentativeTransaction --> TransactionReussie : Ganache connecté\nw3.eth.send_transaction()
        TentativeTransaction --> TransactionRepli : Ganache indisponible\n→ hash SHA-256 local
        TransactionReussie --> [*]
        TransactionRepli --> [*]
    }

    EnregistrementBlockchain --> SauvegardeBaseDeDonnees : hash_tx obtenu
    SauvegardeBaseDeDonnees --> ErreurBaseDeDonnees : Erreur SQLite (500)
    SauvegardeBaseDeDonnees --> Verifie : INSERT réussi\nstatut = Verifie

    Verifie --> EnvoiEmail : generer_pdf_certificat()\n+ envoyer_email_certificat()

    state EnvoiEmail {
        [*] --> TentativeSMTP
        TentativeSMTP --> EmailEnvoye : SMTP configuré\njournal_audit: EMAIL_ENVOYE
        TentativeSMTP --> EmailEchoue : SMTP absent\njournal_audit: EMAIL_ECHOUE
        EmailEnvoye --> [*]
        EmailEchoue --> [*]
    }

    EnvoiEmail --> Verifie : Certificat actif\njournal_audit: EMISSION

    %% ── Transitions administrateur ────────────────────────
    Verifie --> EnAttente : PATCH /certificates/{id}/statut\n{ statut: En attente }
    Verifie --> Revoque : PATCH /certificates/{id}/statut\n{ statut: Revoque }
    EnAttente --> Verifie : PATCH → statut: Verifie\njournal_audit: MAJ_STATUT
    EnAttente --> Revoque : PATCH → statut: Revoque
    Revoque --> Verifie : PATCH → statut: Verifie\n(ré-activation par l'administrateur)

    %% ── Téléchargement PDF ────────────────────────────────
    Verifie --> PDFTelecharge : GET /certificates/{id}/pdf\njournal_audit: TELECHARGEMENT_PDF
    PDFTelecharge --> Verifie : PDF transmis, état inchangé

    %% ── Vérification publique ─────────────────────────────
    Verifie --> VerificationPublique : GET /certificates/verify/{id}\n[route publique sans JWT]
    EnAttente --> VerificationPublique : Résultat: non valide
    Revoque --> VerificationPublique : Résultat: non valide
    VerificationPublique --> Verifie : est_valide = vrai
    VerificationPublique --> EnAttente : est_valide = faux
    VerificationPublique --> Revoque : est_valide = faux

    %% ── Suppression définitive ────────────────────────────
    Verifie --> Supprime : DELETE /certificates/{id}\n[admin uniquement]\njournal_audit: SUPPRESSION
    EnAttente --> Supprime : DELETE /certificates/{id}
    Revoque --> Supprime : DELETE /certificates/{id}
    Supprime --> [*]
```

---

## Correspondance Code Source → Diagrammes

| Élément UML | Fichier source | Fonction / Méthode |
|---|---|---|
| Flux connexion | `auth.py` | `login()` + `generer_jeton()` |
| Décorateur d'authentification | `auth.py` | `exiger_auth()` |
| Flux émission | `app.py` | `emettre_certificat()` |
| Calcul de hash | `app.py` | `calculer_hash()` + `hashlib.sha256` |
| Enregistrement blockchain | `app.py` | `enregistrer_blockchain()` + `w3.eth.send_transaction()` |
| Génération PDF | `cert_services.py` | `generer_pdf_certificat()` via ReportLab |
| Envoi e-mail | `cert_services.py` | `envoyer_email_certificat()` via smtplib |
| États `Vérifié / En attente / Révoqué` | `app.py` | `mettre_a_jour_statut()` + liste `autorisés` |
| Insertions journal d'audit | `app.py` + `auth.py` | `journaliser_action()` + `journaliser_auth()` |
| Requêtes HTTP frontend | `frontend/login.js` | `seConnecter()` + `sInscrire()` |
