<!-- use this link to generate the diagram: https://mermaid.ai/app/dashboard or use a local mermaid live editor to visualize the diagram. Make sure to copy the entire code snippet below and paste it into the editor to see the use case diagram for the SmartCert System. -->
```mermaid
flowchart LR
    Admin([Administrateur])
    Etudiant([Étudiant])
    Visiteur([Public / Vérificateur])

    subgraph SmartCert["SmartCert System"]
        UC_Login(Se connecter)
        UC_Issue(Émettre un certificat)
        UC_Manage(Révoquer/Gérer)
        UC_Dash(Voir le Dashboard)
        UC_View(Consulter ses certificats)
        UC_Verify(Vérifier un certificat - Publique)
    end

    Admin --> UC_Login
    Admin --> UC_Issue
    Admin --> UC_Manage
    Admin --> UC_Dash

    Etudiant --> UC_Login
    Etudiant --> UC_View

    Visiteur --> UC_Verify
```