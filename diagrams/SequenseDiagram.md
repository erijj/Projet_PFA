<!-- use this link to generate the diagram: https://mermaid.ai/app/dashboard or use a local mermaid live editor to visualize the diagram. Make sure to copy the entire code snippet below and paste it into the editor to see the sequence diagram for the login process of the SmartCert System. -->
```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant F as Frontend (login.html)
    participant B as Backend (Flask app.py)
    participant D as Base de données (SQLite)

    U->>F: Saisit email et mot de passe
    F->>B: POST /auth/login (email, password)
    B->>D: SELECT * FROM users WHERE email = ?
    D-->>B: Retourne l'utilisateur (avec password_hash)
    B->>B: check_password_hash(hash, password)
    alt Mot de passe correct
        B->>B: Création de la session Flask (cookie)
        B-->>F: 200 OK (Set-Cookie session)
        F->>F: Redirection vers dashboard.html
    else Mot de passe incorrect
        B-->>F: 401 Unauthorized
        F->>U: Affiche message d'erreur
    end
```