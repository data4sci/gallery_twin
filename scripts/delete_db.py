import os

DB_PATH = "gallery.db"

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"Databáze {DB_PATH} byla smazána.")
else:
    print(f"Soubor {DB_PATH} neexistuje.")
