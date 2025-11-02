# Gallery Twin

Webová aplikace pro virtuální galerii s interaktivními expozicemi a dotazníky pro návštěvníky. Administrátor má přístup k výsledkům a analytickým datům.

## Rychlý start

### Lokální vývoj

```bash
# 1. Klonování projektu
git clone https://github.com/data4sci/gallery_twin.git
cd gallery_twin

# 2. Instalace uv (pokud ještě nemáte)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Instalace závislostí
uv sync

# 4. Konfigurace (pro vývoj lze použít výchozí hodnoty)
cp .env.example .env

# 5. Inicializace databáze
uv run alembic upgrade head

# 6. Spuštění aplikace
uv run uvicorn app.main:app --reload
```

Aplikace běží na `http://localhost:8000`

### Deployment na server

```bash
# 1. Klonování na server
git clone https://github.com/data4sci/gallery_twin.git
cd gallery_twin

# 2. Konfigurace prostředí
cp .env.example .env
nano .env  # Nastavte SECRET_KEY a ADMIN_PASSWORD
# Vygenerujte SECRET_KEY: python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Spuštění
./deploy.sh
```

## Azure deployment

Startup Command: `gunicorn --bind=0.0.0.0:${PORT:-8000} --workers 1 --worker-class uvicorn.workers.UvicornWorker --timeout 20 app.main:app`

## Funkcionalita

**Návštěvníci:**

- Interaktivní expozice (obrázky, Markdown text, audio)
- Dotazníky (výběr z možností, Likertova škála, textové odpovědi)
- Automatické ukládání postupu

**Administrátor:**

- Přístup na `/admin` s přihlášením
- Dashboard s metrikami a statistikami
- Filtrování a export odpovědí do CSV

## Technologie

- **Backend:** FastAPI, SQLModel, SQLite
- **Frontend:** Jinja2, Tailwind CSS, Alpine.js
- **Deployment:** Docker, Docker Compose

## Struktura projektu

```
gallery_twin/
├── app/              # FastAPI aplikace
├── content/          # YAML soubory s obsahem expozic
├── static/           # CSS, JS, obrázky
├── alembic/          # Databázové migrace
├── db/               # SQLite databáze (ignorováno gitem)
└── tests/            # Testy
```

## Vývoj

### Testování

```bash
uv run pytest              # Základní testy
uv run pytest --cov=app    # S pokrytím
```

### Kontrola kódu

```bash
uv run ruff check .        # Linting
uv run mypy app/           # Type checking
```

## Konfigurace

### Proměnné prostředí (.env)

Před prvním spuštěním vytvořte `.env` soubor z šablony:

```bash
cp .env.example .env
```

Minimální konfigurace:

```bash
DATABASE_URL=sqlite+aiosqlite:///./db/gallery.db
SECRET_KEY=your-secret-key-min-32-chars
ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong-password
```

Generování bezpečného SECRET_KEY:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**DŮLEŽITÉ:** Vždy změňte `SECRET_KEY` a `ADMIN_PASSWORD` před nasazením na produkční server!

## Správa na serveru

### Běžné operace

```bash
docker compose restart          # Restart aplikace
docker compose logs -f          # Zobrazení logů
docker compose down             # Zastavení
./deploy.sh                     # Aktualizace po změnách
```

### Záloha databáze

```bash
# Vytvoření zálohy
cp db/gallery.db db/gallery_backup_$(date +%Y%m%d).db

# Obnovení ze zálohy
docker compose down
cp db/gallery_backup_YYYYMMDD.db db/gallery.db
docker compose up -d
```

## Reverse proxy (Nginx)

Příklad konfigurace pro integraci s univerzitní doménou:

```nginx
location / {
    proxy_pass http://localhost:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Health check endpoint: `http://localhost:8000/health`

## Troubleshooting

```bash
# Kontrola běhu aplikace
docker compose logs -f

# Restart při problémech
docker compose restart

# Oprávnění k databázi
chmod 755 db/
chmod 644 db/gallery.db

# Změna portu (v docker-compose.yml)
ports:
  - "8001:8000"
```
