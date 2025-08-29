# Gallery Twin - Development Backlog

## Přehled projektu

Virtuální galerie s expozicemi, dotazníky a admin rozhraním. FastAPI + SQLite + Jinja2 + Alpine.js.

## Milníky a úkoly

### M0: Příprava prostředí (0.5 dne)

- [x] **ENV-1**: Aktualizovat pyproject.toml s chybějícími dependencies
  - Přidat: sqlmodel, alembic, uvicorn, jinja2, python-multipart, pyyaml, httpx (testing)
  - Akceptační kritéria: `uv add` proběhne bez chyb
- [x] **ENV-2**: Vytvořit základní strukturu adresářů
  - Akceptační kritéria: Struktura podle PRD je vytvořená
- [x] **ENV-3**: Vytvořit .env.example s konfigurací
  - Akceptační kritéria: Obsahuje všechny potřebné proměnné (DB_PATH, SECRET_KEY, ADMIN_PASSWORD)
- [x] **ENV-4**: Inicializovat Alembic pro databázové migrace
  - Akceptační kritéria: `alembic init` proběhne a je nakonfigurovaný pro SQLite

### M1: Databázový model a migrace (0.5 dne)

- [x] **DB-1**: Vytvořit SQLModel modely (models.py)
  - Exhibits, Images, Questions, Sessions, Answers, Events
  - Akceptační kritéria: Modely odpovídají schématu z PRD
- [x] **DB-2**: Vytvořit database connection a session management (db.py)
  - Akceptační kritéria: Funkční SQLite připojení s async session
- [x] **DB-3**: Vytvořit první Alembic migraci
  - Akceptační kritéria: `alembic upgrade head` vytvoří všechny tabulky
- [x] **DB-4**: Vytvořit Pydantic schémata pro API (schemas.py)
  - Akceptační kritéria: Request/Response modely pro všechny endpointy

### M2: YAML Content Loader (0.5 dne)

- [x] **CONTENT-1**: Vytvořit YAML loader službu (services/content_loader.py)
  - Akceptační kritéria: Načte YAML soubory a parsuje je do Pydantic modelů
- [x] **CONTENT-2**: Implementovat ukládání obsahu do databáze
  - Akceptační kritéria: Idempotentní operace, content se načte při startu
- [x] **CONTENT-3**: Vytvořit ukázkový obsah (content/exhibits/)
  - 2-3 ukázkové exhibit YAML soubory s obrázky, textem, audio, otázkami
  - Akceptační kritéria: Obsah se úspěšně načte do databáze

### M3: Základní routing a šablony (0.5 dne)

- [x] **ROUTE-1**: Vytvořit FastAPI aplikaci s routingem (main.py, routers/)
  - Public router: /, /exhibit/{slug}, /thanks
  - Admin router: /admin, /admin/responses, /admin/export.csv
  - Akceptační kritéria: Všechny routy odpovídají s HTTP 200/404
- [x] **TMPL-1**: Vytvořit base template s Tailwind CSS
  - Akceptační kritéria: Responsive layout, navigation
- [x] **TMPL-2**: Vytvořit šablony pro public stránky
  - index.html, exhibit.html, thanks.html
  - Akceptační kritéria: Základní struktura s placeholder obsahem
- [x] **TMPL-3**: Vytvořit admin šablony
  - admin/dashboard.html, admin/responses.html
  - Akceptační kritéria: Tabulky a formuláře pro admin funkce

### M4: Session Management (0.5 dne)

- [x] **DB-5**: Na úvodni stránce přidat sebeevaluační dotazník (pohlaví, věk, vzdělání) a uložit do databáze
- [ ] **SESSION-1**: Implementovat session management s cookies
  - Akceptační kritéria: UUIDv4 session se vytvoří při první návštěvě
- [x] **SESSION-2**: Vytvořit middleware pro session handling
  - Akceptační kritéria: Session persists mezi requests, bezpečné cookie nastavení
- [x] **SESSION-3**: Implementovat session tracking v databázi
  - Akceptační kritéria: Sessions tabulka se plní s metadaty (user_agent, čas)

### M5: Exhibit zobrazení a navigace (0.5 dne)

- [x] **EXHIBIT-1**: Implementovat zobrazení exhibit obsahu
  - Markdown rendering, obrázky, audio
  - Akceptační kritéria: Kompletní exhibit se zobrazí s obsahem z YAML
- [x] **EXHIBIT-2**: Vytvořit image carousel s Alpine.js
  - Akceptační kritéria: Funkční navigace mezi obrázky
- [x] **EXHIBIT-3**: Implementovat audio přehrávač
  - Akceptační kritéria: HTML5 audio s custom controls
- [x] **EXHIBIT-4**: Vytvořit navigaci mezi exhibits
  - Akceptační kritéria: Tlačítka Další/Předchozí fungují podle order_index

### M6: Dotazníky a odpovědi (1 den)

- [ ] **FORM-1**: Vytvořit formulářové komponenty pro všechny typy otázek
  - Single choice, multiple choice, Likert scale, text
  - Akceptační kritéria: Všechny typy se renderují správně
- [ ] **FORM-2**: Implementovat validaci na straně serveru
  - Akceptační kritéria: Required validace, type checking
- [ ] **FORM-3**: Implementovat ukládání odpovědí
  - POST /exhibit/{slug}/answer endpoint
  - Akceptační kritéria: Odpovědi se ukládají do databáze s session_id
- [ ] **FORM-4**: Implementovat loading existujících odpovědí
  - Akceptační kritéria: Po refresh stránky jsou odpovědi předvyplněné
- [ ] **FORM-5**: Vytvořit CSRF protection
  - Akceptační kritéria: CSRF token v každém formuláři

### M7: Admin rozhraní (1 den)

- [ ] **ADMIN-1**: Implementovat HTTP Basic Auth pro admin
  - Akceptační kritéria: Přístup k /admin/* vyžaduje heslo z .env
- [ ] **ADMIN-2**: Vytvořit dashboard s KPI metrikami
  - Sessions count, completion rate, average time
  - Akceptační kritéria: Správné výpočty z databáze
- [ ] **ADMIN-3**: Implementovat tabulku odpovědí s filtry
  - Filtr podle data, exhibit, otázky
  - Akceptační kritéria: Funkční filtrace a pagination
- [ ] **ADMIN-4**: Implementovat CSV export
  - Akceptační kritéria: CSV stream s formátem podle PRD
- [ ] **ADMIN-5**: Vytvořit analytics službu (services/analytics.py)
  - Akceptační kritéria: Agregace dat pro dashboard

### M8: UX vylepšení (0.5 dne)

- [ ] **UX-1**: Implementovat responsive design
  - Akceptační kritéria: Funguje na mobilu, tabletu, desktopu
- [ ] **UX-2**: Přidat klávesové zkratky
  - Šipky pro navigaci, mezera pro play/pause
  - Akceptační kritéria: Klávesy fungují na exhibit stránkách
- [ ] **UX-3**: Implementovat loading states a error handling
  - Akceptační kritéria: Feedback pro uživatele při operacích
- [ ] **UX-4**: Přidat accessibility features
  - Alt texty, ARIA labely, focus management
  - Akceptační kritéria: Základní a11y compliance

### M9: Testování (0.5 dne)

- [ ] **TEST-1**: Vytvořit unit testy pro content loader
  - Akceptační kritéria: Pokrytí YAML parsingu a validace
- [ ] **TEST-2**: Vytvořit integration testy pro API
  - Akceptační kritéria: Testy pro všechny public a admin endpointy
- [ ] **TEST-3**: Vytvořit testy pro analytics službu
  - Akceptační kritéria: Správnost výpočtů agregací
- [ ] **TEST-4**: Nastavit pytest konfigurace a test databázi
  - Akceptační kritéria: `pytest` běží všechny testy

### M10: Deployment příprava (0.5 dne)

- [ ] **DEPLOY-1**: Vytvořit Dockerfile
  - Multi-stage build s uvicorn
  - Akceptační kritéria: `docker build` proběhne úspěšně
- [ ] **DEPLOY-2**: Vytvořit docker-compose pro local development
  - Akceptační kritéria: `docker-compose up` spustí aplikaci
- [ ] **DEPLOY-3**: Přidat health check endpoint
  - Akceptační kritéria: /health vrací status aplikace a databáze
- [ ] **DEPLOY-4**: Dokumentace deployment procesu
  - Akceptační kritéria: README s instrukcemi pro Railway/Fly.io

## Aktuální status

- **Celkový pokrok**: 11/44 úkolů dokončeno (25%)
- **Aktuální milník**: M3 - Základní routing a šablony
- **Další úkol**: ROUTE-1 - Vytvořit FastAPI aplikaci s routingem

## Poznámky

- Každý úkol by měl trvat max 2-4 hodiny
- Po dokončení každého úkolu je potřeba otestovat funkcionalita
- Commit po každém dokončeném úkolu
- Milníky M1-M3 jsou kritické pro základní funkcionalitu
