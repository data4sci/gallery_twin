# Virtuální Galerie (gallery_twin)

Jednoduchá webová aplikace pro „virtuální galerii“. Návštěvníci procházejí sérií expozic (obrázky, text, audio) a odpovídají na krátký dotazník. Odpovědi se ukládají do databáze SQLite. Administrátor má přístup k agregovaným datům a exportům.

Projekt je postaven na základě [Product Requirements Document](docs/prd.md).

## Klíčové vlastnosti

### Pro návštěvníky

* Lineární procházení expozic.
* Zobrazení obrázků, textů (Markdown) a přehrávání audio doprovodu.
* Vyplňování dotazníků (single choice, multiple choice, Likertova škála, text).
* Postup se ukládá automaticky a je vázán na anonymní session.

### Pro administrátory

* Zabezpečený přístup (`/admin`).
* Dashboard s klíčovými metrikami (počet návštěv, míra dokončení).
* Tabulkový přehled odpovědí s možností filtrování.
* Export dat ve formátu CSV.

## Technologie

* **Backend**: FastAPI, Uvicorn
* **Databáze**: SQLite
* **ORM**: SQLModel (postaveno na SQLAlchemy)
* **Migrace**: Alembic
* **Frontend**: Šablony Jinja2, Tailwind CSS (přes CDN), Alpine.js (pro minimální interaktivitu)
* **Vývojové nástroje**: `uv`, `ruff`, `mypy`, `pytest`
* **Kontejnerizace**: Docker

## Struktura projektu

```
gallery_twin/
  app/
    main.py
    deps.py
    auth.py
    routers/
      public.py
      admin.py
    models.py
    schemas.py
    db.py
    services/
      content_loader.py
      analytics.py
    templates/
      ...
    static/
      ...
  content/
    exhibits/
      01_room-1.yml
      ...
  alembic/
  tests/
  .env.example
  Dockerfile
  pyproject.toml
  README.md
```

## Lokální spuštění

1. **Klonování repozitáře** (pokud jste tak již neučinili):

    ```bash
    git clone <URL_REPOZITARE>
    cd gallery_twin
    ```

2. **Vytvoření a aktivace virtuálního prostředí**:

    ```bash
    uv venv
    source .venv/bin/activate
    ```

3. **Instalace závislostí**:

    ```bash
    uv pip install -e .
    ```

4. **Instalace vývojových nástrojů** (volitelné):

    ```bash
    uv pip install ruff mypy pytest black isort
    ```

5. **Konfigurace**:
    Vytvořte soubor `.env` (můžete kopírovat z `.env.example`, pokud existuje) a nastavte potřebné proměnné, např. `ADMIN_PASSWORD`.

6. **Spuštění databázových migrací**:

    ```bash
    alembic upgrade head
    ```

7. **Spuštění aplikace**:

    ```bash
    uvicorn app.main:app --reload
    ```

    Aplikace bude dostupná na `http://127.0.0.1:8000`.

## Testování

Pro spuštění testů použijte příkaz:

```bash
pytest
```
