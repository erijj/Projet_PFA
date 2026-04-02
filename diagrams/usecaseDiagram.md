'use this link to generate the diagram: https://mermaid.ai/app/dashboard or use a local mermaid live editor to visualize the diagram. Make sure to copy the entire code snippet below and paste it into the editor to see the use case diagram for the SmartCert System.'
'usecaseDiagram'
    actor "Administrateur" as Admin
    actor "Étudiant" as Etudiant
    actor "Public / Vérificateur" as Visiteur

    package "SmartCert System" {
        usecase "Se connecter" as UC_Login
        usecase "Émettre un certificat" as UC_Issue
        usecase "Révoquer/Gérer" as UC_Manage
        usecase "Voir le Dashboard" as UC_Dash
        usecase "Consulter ses certificats" as UC_View
        usecase "Vérifier un certificat (Publique)" as UC_Verify
    }

    Admin --> UC_Login
    Admin --> UC_Issue
    Admin --> UC_Manage
    Admin --> UC_Dash

    Etudiant --> UC_Login
    Etudiant --> UC_View

    Visiteur --> UC_Verify