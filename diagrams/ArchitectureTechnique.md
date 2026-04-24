# Environnement & Architecture Technique - SmartCert

Ce document décrit l'architecture technique du projet **SmartCert**, en remplacement de l'ancienne architecture (PHP/JSON/APIs Islamiques) pour correspondre à la branche principale actuelle (Flask/SQLite/Blockchain).

## Diagramme d'Architecture (Mermaid)

```mermaid
flowchart LR
    %% Styles
    classDef frontend fill:#e8f4e5,stroke:#4caf50,stroke-width:2px,color:#333;
    classDef backend fill:#e0f7fa,stroke:#00bcd4,stroke-width:2px,color:#333;
    classDef data fill:#fff3e0,stroke:#ff9800,stroke-width:2px,color:#333;
    classDef tech fill:#ffffff,stroke:#bdbdbd,stroke-width:1px,color:#333;

    subgraph Couche_Presentation ["Frontend (Couche Présentation)"]
        direction TB
        F_Tech["Technologies\nHTML5 | CSS3 | JavaScript\nMetaMask (Portefeuille)"]:::tech
        F_Session["Gestion de Session\nCookies HttpOnly\n(smartcert_session)"]:::tech
        F_Nav["Navigateur\nDesktop | Mobile"]:::tech
        F_Sec["Sécurité\nSessions serveur\nDécorateurs de protection"]:::tech
        
        F_Tech ~~~ F_Session ~~~ F_Nav ~~~ F_Sec
    end
    class Couche_Presentation frontend

    subgraph Backend_Server ["Backend (Python + Flask)"]
        direction TB
        B_Routes["Endpoints API\n- /auth/login\n- /certificates\n- /certificates/verify\n- /stats & /audit"]:::tech
        B_Web3["Intégration Blockchain\nWeb3.py"]:::tech
        B_Server["Serveur\nServeur Flask / WSGI"]:::tech
        B_Bot["Chatbot\nAPI REST vers n8n"]:::tech

        B_Routes ~~~ B_Web3 ~~~ B_Server ~~~ B_Bot
    end
    class Backend_Server backend

    subgraph Couche_Donnees ["Données & Réseaux Externes"]
        direction TB
        D_SQL["Base de données SQLite\ncertificates.db\n(Tables: certificates, sessions, audit_log)"]:::tech
        D_Block["Blockchain Ethereum\nEthereum Testnet\nSmart Contracts"]:::tech
        D_N8N["Automatisation\nWorkflows n8n"]:::tech

        D_SQL ~~~ D_Block ~~~ D_N8N
    end
    class Couche_Donnees data

    %% Connections
    Couche_Presentation -- "Requêtes HTTP/REST\n(avec cookies)" --> Backend_Server
    Backend_Server -- "Lecture/Écriture" --> D_SQL
    Backend_Server -- "Transactions Web3" --> D_Block
    Backend_Server -- "Webhooks" --> D_N8N
```

## Résumé des modifications par rapport à l'image fournie

### 1. Bloc "Frontend"
*   **Technologies :** Conservation de HTML5, CSS3, et JavaScript. Ajout de **MetaMask** qui est essentiel pour interagir avec la blockchain.
*   **Session :** Remplacement de `localStorage` par des **Cookies HttpOnly** (`smartcert_session`), comme défini dans votre README, ce qui est plus sécurisé car non accessible via JavaScript.
*   **Sécurité :** Remplacement des mentions Bcrypt/Anti-injection par les méthodes utilisées dans votre projet : **Sessions côté serveur**, hashage avec **Werkzeug (PBKDF2-SHA256)**, et les **Décorateurs Flask** (`@login_required`, `@role_required`).

### 2. Bloc "Backend"
*   **Serveur :** Remplacement de `Apache + PHP` par **Python + Flask**.
*   **Modules :** Remplacement des modules (signup, forgot-pass...) par les routes réelles de l'application : **`/auth/login`**, **`/certificates`**, **`/verify`**, **`/stats`**, **`/audit`**.
*   **Ajouts :** Intégration de **Web3.py** pour faire le lien entre le backend et la blockchain, et l'API de communication avec **n8n**.

### 3. Bloc "Données (Stockage)"
*   **Base de données locale :** Remplacement des `Fichiers JSON` par **SQLite** (`certificates.db` contenant les tables `certificates`, `audit_log`, `sessions`).
*   **APIs Externes :** Remplacement des APIs (Coran, Prière, Hadiths) par :
    *   **Ethereum Testnet** pour l'enregistrement et la vérification des certificats sur la blockchain.
    *   **Workflows n8n** pour la logique du chatbot d'assistance.
