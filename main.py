import customtkinter as ctk
import database
from ui import BaseballTrackerModern

def main():
    database.create_tables()
    
    # Úprava vkládání: Jméno, Příjmení, Tým, Číslo, Hází, Pálí
    """
    if not database.get_all_players():
        print("Vytvářím testovací hráče...")
        database.insert_player("Tomáš", "Satoranský", "Draci Brno", 8, "R", "R")
        database.insert_player("Jan", "Novák", "Eagles Praha", 12, "L", "L")
        database.insert_player("Pepa", "Zdepa", "Hroši Brno", 99, "R", "L")
    """
    root = ctk.CTk()
    app = BaseballTrackerModern(root)
    root.mainloop()

if __name__ == "__main__":
    main()