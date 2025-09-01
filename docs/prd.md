# Product Requirements Document (MVP)

## Cíl

Jednoduchá webová aplikace pro „virtuální galerii“: návštěvník si projde sérii „expozic“ (obrázky + text + audio), zodpoví krátký dotazník; odpovědi se uloží do SQLite. Na konci se zobrazí závěrečná stránka. Admin uvidí agregace odpovědí a vyexportuje data.

## Role

* **Visitor**: projde obsah, přehraje audio, vyplní dotazník. Bez registrace.
* **Admin**: zobrazí agregace, základní filtry, export CSV. Přístup přes jednoduché heslo (HTTP Basic/Token v .env).

## User flow

1. **Úvod** (`/`): název, krátké intro, tlačítko „Začít“. Při vstupu vznikne **SessionID** (cookie, UUIDv4).
2. **Expozice** (`/exhibit/:slug`):

   * obrázek/y (carousel / mřížka), text (Markdown), audio (play/pause, čas).
   * navigace **Další / Předchozí**.
   * dotazník (1–12 otázek; typy: single, multi, likert, text).
   * validace a uložení **po každé stránce** (optimisticky).
3. **Závěr** (`/thanks`): poděkování, volitelný odkaz na zpětnou vazbu.
4. **Admin** (`/admin`): metriky, tabulka odpovědí, filtry (datum, exhibit, otázka), export CSV.

## Obsah

* **Exhibit** = jednotka obsahu: `title`, `slug`, `text_md`, `images[]`, `audio`, `order`.
* **Questionnaire**: sadu otázek lze vázat na exhibit nebo na celou návštěvu.
* Obsah se spravuje přes **YAML manifesty** v repo (MVP), nikoli přes CMS.

## Ne-funkční požadavky

* **MVP do 2–4 dnů práce**; monolit.
* Rychlý start bez registrací, **SQLite** jako jediný perzistentní store.
* Privacy: žádná PII; SessionID je pseudonymní. Cookie `SameSite=Lax`, expirace 30 dní.
* Výkon: do stovek současných návštěv (statická média servovaná ze /static).

## Out of scope (MVP)

* Upload obsahu v adminu, složité role, full-text vyhledávání, verzování dotazníků, analytika třetích stran.

## Akceptační kritéria (shrnutí)

* Projdu **lineárně** N expozic → všude vidím obrázky, text, pustím audio, dotazník uloží odpovědi do SQLite.
* Hard-refresh neztratí již uložené odpovědi; SessionID váže odpovědi k návštěvě.
* Admin po zadání hesla vidí: počty návštěv, completion rate, rozpad odpovědí, **Export CSV**.
* Obsah lze definovat v `content/exhibits/*.yml` a načte se při prvním startu aplikace.
* Závěrečná stránka se zobrazí po poslední expozici.

---

# Tech-stack & Architektura

## Přehled

**Monolit FastAPI + Jinja + Alpine + SQLite.** Statická média v `/static`. Data model přes **SQLModel/SQLAlchemy**. Migrations **Alembic**. Admin jako interní view s jednoduchým heslem. Deployment: Docker na **Railway/Fly.io/Render** (bez správy serveru).

## Konkrétní volby

* **Backend**: FastAPI, Uvicorn.
* **ORM/DB**: SQLModel (na SQLAlchemy 2.x), SQLite (`sqlite:///./gallery.db`), Alembic.
* **Šablony/Frontend**: Jinja2, Alpine.js (drobné stavy), **Tailwind via CDN**.
* **Audio**: HTML5 `<audio>` element (nativní ovládání); volitelně vlastní play/pause tlačítko přes JS.
* **Validace**: Pydantic v request modelech.
* **Auth (admin)**: HTTP Basic (FastAPI `HTTPBasic`) nebo Bearer token z `.env`.
* **DevX**: `uv`/Poetry, `ruff`, `mypy`, `pytest`.
* **Export**: `pandas` → CSV stream.
* **Docker**: 2-stage build (uvicorn worker).

## Datový model (SQLite)

**Tabulky (minimální jádro):**

* `exhibits`
  `id PK`, `slug UNIQUE`, `title`, `text_md`, `audio_path`, `audio_transcript`, `order_index INT`
* `images`
  `id PK`, `exhibit_id FK`, `path`, `alt_text`, `sort_order INT`
* `questions`
  `id PK`, `exhibit_id FK NULLABLE` (NULL = globální), `text`, `type ENUM('single','multi','likert','text')`, `options_json` (pro single/multi/likert), `required BOOL`
* `sessions`
  `id PK`, `uuid UNIQUE`, `created_at`, `user_agent`, `accept_lang`
* `answers`
  `id PK`, `session_id FK`, `question_id FK`, `value_text NULL`, `value_json NULL`, `created_at`
* `events` (volitelné)
  `id PK`, `session_id FK`, `exhibit_id FK`, `event_type` (view\_start, view\_end, audio\_play, audio\_pause), `ts`

**Pozn.:** multi-choice do `answers.value_json` (array). Likert jako číslo v `value_text` nebo `value_json`.

## API & Routy

* **Public**

  * `GET /` – intro
  * `GET /exhibit/{slug}` – render obsahu + form
  * `POST /exhibit/{slug}/answer` – uloží odpovědi
  * `GET /thanks` – závěr
* **Admin** (guard)

  * `GET /admin` – dashboard (karty: návštěvy, vyplněné sezení, completion rate)
  * `GET /admin/responses` – tabulka s filtry (datum, exhibit, question)
  * `GET /admin/export.csv` – CSV stream

## Načítání obsahu (YAML manifest)

* Umístění: `content/exhibits/{order}_{slug}.yml`
* Struktura (příklad):

  ```yaml
  slug: room-1
  title: "Room 1 — Abstrakce"
  text_md: |
    **Úvod** … (Markdown)
  audio: "audio/room1.mp3"
  images:
    - path: "img/room1/a.jpg"
      alt: "Detail A"
    - path: "img/room1/b.jpg"
      alt: "Detail B"
  questions:
    - type: "likert"
      text: "Jak na vás expozice působila?"
      options: [1,2,3,4,5]
      required: true
    - type: "text"
      text: "Krátká zpětná vazba?"
  ```

* **Loader** při startu: vytvoří/aktualizuje `exhibits`, `images`, `questions` (idempotentně).

## Šablonování & UX

* Layout: hlavička (název), obsah, sticky spodní lišta (Play/Pause, Další/Back).
* Obrázky: jednoduchý carousel (CSS + Alpine).
* Form: každý blok otázek má **Uložit & Další** (POST → redirect na další exhibit). Required validace na serveru. Nutné zodpovědět povinné otázky (označené `*`)

## Bezpečnost & Privacy

* Admin chráněn Basic Auth, heslo v `.env` (např. `ADMIN_PASSWORD`).
* Session cookie: `HttpOnly`, `SameSite=Lax`.
* Žádné externí trackery; logy pouze agregované metriky.
* CSRF: u POST formulářů **CSRF token** v šabloně (tajný klíč v `.env`).

## Testy

* Unit: loader YAML, validace odpovědí, agregace.
* Integration: posty na `/exhibit/:slug/answer`, export CSV.
* E2E (rychlé): `pytest` + `httpx.AsyncClient`.

## Deployment

* **Dockerfile** (Uvicorn, gunicorn není nutný pro MVP).
* **Railway/Render/Fly.io**: persistentní volume pro `gallery.db` + `/static` (nebo build-time bundling). Pro produkci zvaž `sqlite PRAGMA journal_mode=WAL`.
* Build pipeline: `ruff + mypy + pytest` v CI.

## Struktura repa (návrh)

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
      base.html
      index.html
      exhibit.html
      thanks.html
      admin/
        dashboard.html
        responses.html
    static/
      css/, js/, img/, audio/
  content/
    exhibits/
      01_room-1.yml
      02_room-2.yml
  alembic/
  tests/
  .env.example
  Dockerfile
  pyproject.toml
  README.md
```

## Agregace v adminu (minimální)

* **KPI karty**: `#Sessions`, `#Completed`, `Completion Rate = completed/sessions`, `Avg time per exhibit` (z `events` pokud zapnuto).
* **Odpovědi**: pivot (otázka × odpověď → počet), detailní tabulka s filtrem.
* **Export**: CSV s poli: `session_uuid, ts, exhibit_slug, question_id, question_text, answer_value`, `selfeval_json`.
