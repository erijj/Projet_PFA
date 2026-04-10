<!-- use this link to generate the diagram: https://mermaid.ai/app/dashboard or use a local mermaid live editor to visualize the diagram. Make sure to copy the entire code snippet below and paste it into the editor to see the class diagram for the SmartCert System. -->
```mermaid
classDiagram
    class User {
        +String id
        +String email
        +String password_hash
        +String role
        +login()
        +logout()
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
        +String created_at
        +issue()
        +verify()
        +revoke()
    }

    class AuditLog {
        +Integer log_id
        +String action
        +String cert_id
        +String performed_by
        +String timestamp
        +String details
        +record()
    }

    User "1" -- "*" Certificate : "émet/gère (Admin)"
    User "1" -- "*" Certificate : "consulte (Etudiant)"
    User "1" -- "*" AuditLog : "génère"
    Certificate "1" -- "*" AuditLog : "tracé par"
```