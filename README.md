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

## Deployment

Projekt je kontejnerizován pomocí Dockeru pro snadné nasazení.

### Lokální spuštění s Docker Compose

Ujistěte se, že máte nainstalovaný Docker a Docker Compose.

1.  **Sestavení a spuštění kontejnerů**:

    ```bash
    docker compose up --build
    ```

    Tento příkaz sestaví Docker image, spustí aplikaci a provede databázové migrace. Aplikace bude dostupná na `http://localhost:8000`.

2.  **Zastavení kontejnerů**:

    ```bash
    docker compose down
    ```

### Deployment na produkční prostředí

Pro produkční nasazení doporučujeme použít platformy jako Railway, Fly.io nebo Render, které podporují Docker.

1.  **Příprava `.env` souboru**:
    Ujistěte se, že váš `.env` soubor obsahuje produkční hodnoty pro `SECRET_KEY`, `ADMIN_USERNAME` a `ADMIN_PASSWORD`.

2.  **Databáze**:
    Projekt používá SQLite, což je pro malé aplikace v cloudu dostačující. Ujistěte se, že vaše deployment platforma podporuje perzistentní úložiště pro `gallery.db` (např. persistent volumes na Railway/Fly.io).

3.  **Health Check**:
    Aplikace obsahuje health check endpoint na `/health`, který můžete použít pro monitorování stavu aplikace na vaší platformě.

    ```bash
    curl http://localhost:8000/health
    ```

4.  **Build a Push Docker Image** (pokud vaše platforma vyžaduje ruční build):

    ```bash
    docker build -t your-repo/gallery-twin:latest .
    docker push your-repo/gallery-twin:latest
    ```

    Poté nakonfigurujte vaši platformu tak, aby používala tento image.

5.  **Environment Variables**:
    Nastavte environment proměnné (`DB_PATH`, `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`) přímo na vaší deployment platformě.

Další informace naleznete v dokumentaci vaší vybrané deployment platformy.


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
