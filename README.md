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

### Docker (doporučeno)

```bash
# 1. Build Docker image
docker build -t gallery-twin .

# 2. Spuštění kontejneru
docker run -d -p 8000:8000 \
  -v $(pwd)/db:/app/db \
  -e SECRET_KEY="your-secret-key" \
  -e ADMIN_USERNAME="admin" \
  -e ADMIN_PASSWORD="secure-password" \
  --name gallery-twin-app \
  gallery-twin

# 3. Zobrazení logů
docker logs -f gallery-twin-app

# 4. Zastavení a smazání kontejneru
docker stop gallery-twin-app
docker rm gallery-twin-app
```

**Poznámky:**

- `-v $(pwd)/db:/app/db` - persistentní databáze (přežije restart kontejneru)
- Citlivé proměnné (`SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`) musíte předat jako argumenty
- Ne-citlivé proměnné mají výchozí hodnoty v Dockerfile a lze je přepsat pomocí `-e`

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

Startup Command: `gunicorn --bind=0.0.0.0:${PORT:-8000} --workers 1 --worker-class uvicorn.workers.UvicornWorker --timeout 120 app.main:app`

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

## Docker - pokročilé operace

### Běžné operace

```bash
# Restart kontejneru
docker restart gallery-twin-app

# Zobrazení logů
docker logs -f gallery-twin-app

# Zastavení
docker stop gallery-twin-app

# Spuštění zastaveného kontejneru
docker start gallery-twin-app

# Připojení do běžícího kontejneru
docker exec -it gallery-twin-app /bin/bash

# Rebuild po změnách v kódu
docker stop gallery-twin-app
docker rm gallery-twin-app
docker build -t gallery-twin .
docker run -d -p 8000:8000 -v $(pwd)/db:/app/db --env-file .env --name gallery-twin-app gallery-twin
```

### Použití .env souboru

Místo předávání jednotlivých proměnných můžete použít `.env` soubor:

```bash
mkdir -p db
docker run -d -p 8000:8000 \
  -v $(pwd)/db:/app/db \
  --env-file .env \
  --name gallery-twin-app \
  gallery-twin
```

### Docker Compose (alternativa)

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

### Docker kontejner

```bash
# Kontrola běhu kontejneru
docker ps -a | grep gallery-twin

# Zobrazení logů
docker logs gallery-twin-app

# Zobrazení logů v reálném čase
docker logs -f gallery-twin-app

# Restart při problémech
docker restart gallery-twin-app

# Úplné přebudování (při změnách v kódu nebo Dockerfile)
docker stop gallery-twin-app
docker rm gallery-twin-app
docker build -t gallery-twin .
docker run -d -p 8000:8000 -v $(pwd)/db:/app/db --env-file .env --name gallery-twin-app gallery-twin

# Změna portu
docker run -d -p 8001:8000 ...  # Aplikace dostupná na portu 8001
```

### Databáze

```bash
# Oprávnění k databázi
chmod 755 db/
chmod 644 db/gallery.db

# Reset databáze (smaže všechna data!)
docker stop gallery-twin-app
rm db/gallery.db
docker start gallery-twin-app  # Migrace vytvoří novou databázi
```

### Docker Compose

```bash
# Kontrola běhu aplikace
docker compose logs -f

# Restart při problémech
docker compose restart

# Změna portu (v docker-compose.yml)
ports:
  - "8001:8000"
```
