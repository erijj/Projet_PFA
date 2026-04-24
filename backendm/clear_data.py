import sqlite3
import os

# Path to the database
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certificates.db')

def clear_db():
    if not os.path.exists(DATABASE):
        print(f"Erreur : La base de données '{DATABASE}' est introuvable.")
        return

    print(f"Nettoyage de la base de données : {DATABASE}...")
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # 1. Supprimer les certificats
        cursor.execute("DELETE FROM certificates")
        print("- Table 'certificates' vidée.")

        # 2. Supprimer les utilisateurs
        cursor.execute("DELETE FROM users")
        print("- Table 'users' vidée.")

        # 3. Supprimer les logs d'audit
        cursor.execute("DELETE FROM audit_log")
        print("- Table 'audit_log' vidée.")
        
        # 4. Réinitialiser les compteurs d'ID (auto-increment)
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('users', 'audit_log')")
        
        conn.commit()
        conn.close()
        print("\n[OK] Toutes les données ont été supprimées avec succès.")
        print("Note : Vous devrez recréer un compte ou relancer 'init_db.py' pour vous reconnecter.")
        
    except Exception as e:
        print(f"Une erreur est survenue : {e}")

if __name__ == '__main__':
    # Demander confirmation avant de supprimer
    confirm = input("Êtes-vous sûr de vouloir supprimer TOUTES les données (certificats et comptes) ? (y/n) : ")
    if confirm.lower() == 'y':
        clear_db()
    else:
        print("Opération annulée.")
