# GameMatch

Backend FastAPI per community gaming: login/registrazione, dashboard utente, richieste di matchmaking, gestione team da parte dei team creator e pannello admin.

## Panoramica

Il progetto nasce come compito didattico e oggi include:

- interfaccia web server-side (HTML/CSS generato da FastAPI)
- autenticazione con session token in cookie
- ruoli utente: utente base, team creator, admin
- database relazionale via SQLAlchemy
- endpoint tecnici per health check, introspezione tabelle e esempi schema

## Stack

- Python 3.9+
- FastAPI
- SQLAlchemy
- Pydantic
- Passlib (hash password)
- PostgreSQL (Docker/produzione) o SQLite (default locale)

## Avvio Rapido (locale)

```bash
cd /workspaces/GameMatch-bohtipregofunziona
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

App disponibile su:

- http://localhost:8000
- http://localhost:8000/docs

## Avvio con Make

```bash
make install
make dev
```

Comandi utili:

- `make test`
- `make lint`
- `make format`
- `make docker-build`
- `make docker-run`
- `make docker-down`

## Avvio con Docker Compose

```bash
docker-compose up --build
```

Servizi:

- `db`: PostgreSQL 15
- `backend`: FastAPI + Uvicorn su porta 8000

## Credenziali Seed (sviluppo)

Alla partenza il database viene inizializzato e popolato con utenti di test.

- admin: `Russo` / `1234.abcd`
- utenti standard: `Marco`, `Sofia`, `Luca`, `Emma`, `Alex` (password `password123`)
- team creator: `TeamAlphaAdmin`, `TeamBravoAdmin`, `TeamDeltaAdmin` (password `creator123`)
- sono presenti anche altri 20 utenti demo e 30 richieste matchmaking generate all'avvio

## Endpoint principali

### Pubblici

- `GET /` home
- `GET /health` dashboard stato server
- `GET /health/json` check JSON rapido
- `GET /status` alias di health
- `GET /tables` schema tabelle DB
- `GET /examples` esempi JSON per gli schemi

### Autenticazione

- `GET /login`
- `POST /login/submit`
- `GET /register`
- `POST /register/submit`
- `GET /logout`

### Area utente autenticato

- `GET /dashboard`
- `GET /request/new`
- `POST /request/submit`
- `POST /creator/request`
- `POST /creator/request/{request_id}/ack`

### Area team creator

- `POST /creator/teams/create`
- `POST /creator/teams/{team_id}/recruitment`
- `POST /creator/teams/{team_id}/tryouts/create`
- `POST /creator/teams/{team_id}/delete`
- `POST /creator/tryouts/{tryout_id}/delete`

### Area admin

- `POST /admin/users/{target_user_id}/update`
- `POST /admin/users/{target_user_id}/delete`
- `POST /admin/users/{target_user_id}/set-creator`
- `POST /admin/users/{target_user_id}/unset-creator`
- `POST /admin/creator-requests/{request_id}/approve`
- `POST /admin/creator-requests/{request_id}/reject`

## Modello dati

Entita principali in `app/models.py`:

- `User`
- `Game`
- `Team`
- `Match`
- `PlayerProfile`
- `TeamRequest`
- `TeamCreatorRequest`
- `TeamRecruitment`
- `TryoutSession`

Gli schemi Pydantic principali sono in `app/schemas.py`, mentre esempi payload sono in `examples.json`.

## Struttura progetto

```text
app/
  main.py          # App FastAPI, pagine HTML e route principali
  database.py      # Engine, sessioni, init schema e seed utenti
  models.py        # ORM SQLAlchemy
  schemas.py       # Schemi Pydantic
  auth.py          # Hash password e autenticazione
  routers/         # Router didattici (placeholder)
  utils/           # Utility sicurezza
```

## Configurazione ambiente

Variabili in `.env.example`:

- `DATABASE_URL`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `ENVIRONMENT`

## Note importanti

- I file in `app/routers/` sono stub didattici e non rappresentano la logica principale attiva.
- L'app usa sessioni in memoria (`ACTIVE_SESSIONS`): adatta a sviluppo, non ideale per produzione distribuita.
- Il database locale di default e `gamematch.db` (SQLite).

## Documentazione correlata

- `QUICK_START.md`
- `COMPITO_1B_SUMMARY.md`
- `INTEGRAZIONI_MAIN_PY.md`
- `RIEPILOGO_FINALE.md`

## Autore

Alberto Russo - Classe 5WDINF - A.A. 2025/2026