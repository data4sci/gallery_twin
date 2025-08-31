# Virtuální Galerie (gallery_twin)

Webová aplikace pro virtuální galerii. Návštěvníci procházejí expozicemi (obrázky, text, audio) a vyplňují dotazníky. Administrátor má přístup k datům a exportům.

## Funkcionalita

**Návštěvníci:**

- Procházení expozic s obrázky, textem (Markdown) a audio
- Vyplňování dotazníků (výběr z možností, Likertova škála, text)
- Automatické ukládání postupu v anonymní session

**Administrátor:**

- Zabezpečený přístup na `/admin`
- Dashboard s metrikami (návštěvy, míra dokončení)
- Přehled a filtrování odpovědí
- CSV export

## Technologie

- **Backend:** FastAPI, SQLModel, SQLite
- **Frontend:** Jinja2, Tailwind CSS, Alpine.js
- **Migrace:** Alembic
- **Nástroje:** uv, ruff, mypy, pytest

## Struktura

```
gallery_twin/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── routers/
├── alembic/
├── tests/
└── Dockerfile
```

## Instalace

```bash
# Klonování a setup
git clone <URL>
cd gallery_twin
uv sync

# Konfigurace
cp .env.example .env  # upravte ADMIN_PASSWORD

# Databáze a spuštění
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Aplikace běží na `http://127.0.0.1:8000`

## Testování

```bash
pytest
```

## Docker

```bash
docker compose up --build
```

## Deployment

### Azure Web Apps

```bash
# Build a push
docker build -t <acr-name>.azurecr.io/gallery-twin:latest .
az acr login --name <acr-name>
docker push <acr-name>.azurecr.io/gallery-twin:latest

# Nastavte env proměnné: SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD
# Připojte Azure Files pro SQLite databázi na /app/gallery.db
```

### AWS ECS/Fargate

```bash
# ECR setup
aws ecr create-repository --repository-name gallery-twin
docker build -t gallery-twin .
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker tag gallery-twin:latest <account>.dkr.ecr.<region>.amazonaws.com/gallery-twin:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/gallery-twin:latest

# Nastavte env proměnné a EFS volume pro databázi
```

### Health Check

Aplikace poskytuje health check na `/health` pro monitoring.
