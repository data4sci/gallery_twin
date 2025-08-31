import os
import shutil
from dotenv import load_dotenv

load_dotenv()

# Načti URL z .env, odstraň prefix a získej cestu k souboru
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./db/gallery.db")
DB_PATH = DATABASE_URL.replace("sqlite+aiosqlite:///", "")

if os.path.exists(DB_PATH):
    try:
        if os.path.isfile(DB_PATH) or os.path.islink(DB_PATH):
            os.remove(DB_PATH)
            print(f"Soubor databáze {DB_PATH} byl smazán.")
        elif os.path.isdir(DB_PATH):
            shutil.rmtree(DB_PATH)
            print(f"Adresář databáze {DB_PATH} byl smazán.")
    except Exception as e:
        print(f"Chyba při mazání {DB_PATH}: {e}")
else:
    print(f"Databáze {DB_PATH} neexistuje.")
