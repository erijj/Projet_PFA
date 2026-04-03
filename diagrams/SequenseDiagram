sequenceDiagram
    participant U as Utilisateur
    participant F as Frontend (login.html)
    participant B as Backend (Flask)
    participant D as SQLite DB

    U->>F: Saisit email + mot de passe
    F->>B: POST /auth/login {email, password}
    B->>D: SELECT * FROM users WHERE email = ?
    D-->>B: Ligne utilisateur (id, password_hash, role)
    B->>B: check_password_hash(hash, password)

    alt Mot de passe correct
        B->>D: INSERT INTO sessions (session_id, user_id, expires_at)
        B-->>F: 200 OK + Set-Cookie (session_id, HttpOnly)
        F->>F: Redirection → dashboard.html
    else Mot de passe incorrect
        B-->>F: 401 Unauthorized {error: "Identifiants invalides"}
        F->>U: Affiche message d'erreur
    end
