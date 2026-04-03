classDiagram
    class User {
        +String id
        +String email
        +String password_hash
        +String role
        +login(email, password) Session
        +logout(session_id) void
        +getInfo() UserInfo
    }

    class Session {
        +String session_id
        +Integer user_id
        +String email
        +String role
        +DateTime created_at
        +DateTime expires_at
        +isValid() bool
    }

    class Certificate {
        +String id
        +String recipient_name
        +String email
        +String program
        +String institution
        +String issue_date
        +String status
        +String blockchain_hash
        +String tx_hash
        +DateTime created_at
        +issue() Certificate
        +verify() Certificate
        +revoke() void
        +updateStatus(status) void
        +delete() void
    }

    class AuditLog {
        +Integer log_id
        +String action
        +String cert_id
        +String performed_by
        +String timestamp
        +String details
        +record() void
    }

    class BlockchainService {
        +String network
        +String contract_address
        +bool connected
        +recordHash(hash) String
        +getStatus() BlockchainStatus
    }

    User "1" --> "0..*" Session : crée
    User "1" --> "0..*" Certificate : émet/gère (Admin)
    User "1" --> "0..*" Certificate : consulte (Étudiant)
    User "1" --> "0..*" AuditLog : génère
    Certificate "1" --> "0..*" AuditLog : tracé par
    Certificate "1" --> "1" BlockchainService : enregistre hash via
