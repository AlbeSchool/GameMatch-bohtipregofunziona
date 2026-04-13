# 🚀 GameMatch — Quick Start Guide

Avvia GameMatch in 3 minuti!

## Installazione Rapida

```bash
# 1. Entra nella cartella
cd /workspaces/GameMatch-bohtipregofunziona

# 2. Crea environment virtuale (opzionale ma consigliato)
python -m venv venv
source venv/bin/activate

# 3. Installa dipendenze
pip install -r requirements.txt
```

## Avvia il Server

```bash
uvicorn app.main:app --reload --port 8000
```

Output atteso:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

## Accedi alle Risorse

Apri il browser:

### 📄 Home Page
```
http://localhost:8000/
```

### 🎨 Dashboard Status
```
http://localhost:8000/health
```

### 📖 Documentazione Interattiva
```
http://localhost:8000/docs          # Swagger UI
http://localhost:8000/redoc        # ReDoc
```

### 📊 Database Info
```
http://localhost:8000/tables       # Schema DB
http://localhost:8000/examples     # Esempi JSON
```

## Test CURL

```bash
# Health check
curl http://localhost:8000/health/json

# Vedi schema database
curl http://localhost:8000/tables

# Vedi esempi schemi
curl http://localhost:8000/examples | jq .

# Vedi Swagger UI su browser
open http://localhost:8000/docs
```

## Struttura Cartelle

```
app/
├── main.py          ← FastAPI app (entry point)
├── schemas.py       ← Modelli Pydantic
├── models.py        ← ORM SQLAlchemy
├── database.py      ← Config database
├── crud.py          ← Templates CRUD
├── routers/         ← Endpoint stubs
└── utils/           ← Security utilities
```

## File Importanti

- 📘 **README.md** — Documentazione completa
- 📘 **RIEPILOGO_FINALE.md** — Overview progetto
- 📘 **examples.json** — Schemi JSON request/response
- 📋 **requirements.txt** — Dipendenze Python

## Prossimi Passi

1. ✅ Server FastAPI è avviato
2. ⏳ Implementare CRUD operations
3. ⏳ Aggiungere autenticazione JWT
4. ⏳ Collegare i router
5. ⏳ Sviluppare Frontend React

## Help

Per maggiori informazioni:
```bash
# Leggi documentazione
cat README.md
cat RIEPILOGO_FINALE.md

# Verifica setup
python verify_setup.py

# Run tests
pytest
```

---

Buona codifica! 🚀
