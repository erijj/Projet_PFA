flowchart LR
    Admin(["👤 Administrateur"])
    Etudiant(["👤 Étudiant"])
    Visiteur(["👤 Public / Vérificateur"])

    subgraph SmartCert System
        UC1["Se connecter"]
        UC2["Se déconnecter"]
        UC3["Émettre un certificat"]
        UC4["Révoquer un certificat"]
        UC5["Mettre à jour le statut d'un certificat"]
        UC6["Supprimer un certificat"]
        UC7["Voir le Dashboard / Statistiques"]
        UC8["Consulter la liste des certificats"]
        UC9["Consulter un certificat"]
        UC10["Vérifier un certificat (par ID ou hash)"]
        UC11["Consulter les logs d'audit"]
        UC12["Voir le statut blockchain"]
        UC13["Utiliser le chatbot"]
    end

    Admin --> UC1
    Admin --> UC2
    Admin --> UC3
    Admin --> UC4
    Admin --> UC5
    Admin --> UC6
    Admin --> UC7
    Admin --> UC8
    Admin --> UC9
    Admin --> UC11
    Admin --> UC12

    Etudiant --> UC1
    Etudiant --> UC2
    Etudiant --> UC8
    Etudiant --> UC9
    Etudiant --> UC10

    Visiteur --> UC10
    Visiteur --> UC13
