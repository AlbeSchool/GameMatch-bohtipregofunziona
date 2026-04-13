# 🎮 GameMatch — Piattaforma di Gestione Team e Match

**Studente:** Alberto Russo  
**Classe:** 5WDINF  
**A.A.:** 2025/2026  
**Docente:** Zhongli Filippo Hu

---

## 📋 Descrizione del Progetto

**GameMatch** è una piattaforma backend per la gestione organizzata di utenti, team e partite nel contesto del gaming multiplayer competitivo. L'applicazione permette ai giocatori di:

- ✅ Registrarsi sulla piattaforma
- ✅ Creare e gestire team
- ✅ Pianificare e partecipare a match
- ✅ Gestire i membri dei team

### 🎯 Target Audience

- Giocatori multiplayer online
- Community eSport amatoriali
- Studenti e giovani gamer (16–30 anni)

---

## 🧱 Stack Tecnologico

### Backend
- **FastAPI** — Framework API REST moderno e performante
- **Python 3.9+**
- **Pydantic** — Validazione dati e generazione schema
- **SQLAlchemy** — ORM per gestione database

### Database
- **PostgreSQL** — Database relazionale (produzione)
- **SQLite** — Database locale (sviluppo)

### Frontend (MVP)
- HTML, CSS, JavaScript Vanilla

### Deploy
- **Webdock (VPS)** — Hosting consigliato
- **Docker** — Containerizzazione (opzionale)

---

## 📁 Struttura del Progetto

```
GameMatch-bohtipregofunziona/
├── app/
│   ├── __init__.py                    # Package initialization
│   ├── main.py                        # FastAPI entry point
│   ├── database.py                    # Database configuration
│   ├── models.py                      # SQLAlchemy ORM models
│   ├── schemas.py                     # Pydantic schemas (validazione)
│   ├── crud.py                        # Database operations
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py                   # User endpoints
│   │   ├── teams.py                   # Team endpoints
│   │   └── matches.py                 # Match endpoints
│   │
│   └── utils/
│       ├── __init__.py
│       └── security.py                # Password hashing & JWT
│
├── requirements.txt                    # Python dependencies
├── .env.example                        # Environment variables template
├── examples.json                       # JSON examples for API
├── README.md                           # This file
└── .git/

```

---

## 🗄️ Modello dei Dati (UML)

### Entità Principali

#### 1. **User** (Utente)
```
id (PK) → Identificatore univoco
username → Nome utente univoco
email → Email univoca
password → Hash della password (non esposto nei response)
created_at → Data di creazione
```

#### 2. **Game** (Gioco)
```
id (PK) → Identificatore univoco
name → Nome del gioco
genre → Genere (MOBA, FPS, ecc.)
created_at → Data di creazione
```

#### 3. **Team** (Group/Squad di giocatori)
```
id (PK) → Identificatore univoco
name → Nome del team
creator_id (FK → User) → Creatore del team
created_at → Data di creazione
```

#### 4. **TeamMembership** (Tabella Ponte - Relazione N:M)
```
id (PK) → Identificatore univoco
user_id (FK → User) → Membro del team
team_id (FK → Team) → Team di appartenenza
```

#### 5. **Match** (Partita)
```
id (PK) → Identificatore univoco
scheduled_at → Data e ora della partita
game_id (FK → Game) → Gioco della partita
team1_id (FK → Team) → Primo team
team2_id (FK → Team) → Secondo team
created_at → Data di creazione
```

### Relazioni

| Tipo | Da | A | Descrizione |
|------|----|----|-------------|
| **1:N** | User | Team | Un utente può creare più team |
| **N:M** | User | Team | Un utente può appartenere a più team (tramite TeamMembership) |
| **1:N** | Game | Match | Un gioco ha più match |
| **1:N** | Team | Match | Un team partecipa a più match |

---

## 📡 API Endpoints (MVP)

### 1. **POST /users** — Creazione Utente
Crea un nuovo utente sulla piattaforma.

**Request:**
```json
{
  "username": "proGamer",
  "email": "pro@email.com",
  "password": "SecurePass123!"
}
```

**Response (201):**
```json
{
  "id": 1,
  "username": "proGamer",
  "email": "pro@email.com"
}
```

---

### 2. **POST /teams** — Creazione Team
Crea un nuovo team.

**Request:**
```json
{
  "name": "NightRaiders",
  "creator_id": 1
}
```

**Response (201):**
```json
{
  "id": 10,
  "name": "NightRaiders",
  "creator_id": 1,
  "members": []
}
```

---

### 3. **POST /matches** — Creazione Partita
Pianifica una nuova partita tra due team.

**Request:**
```json
{
  "scheduled_at": "2026-06-01T18:00:00",
  "game_id": 2,
  "team1_id": 10,
  "team2_id": 11
}
```

**Response (201):**
```json
{
  "id": 100,
  "scheduled_at": "2026-06-01T18:00:00",
  "game_id": 2,
  "team1_id": 10,
  "team2_id": 11
}
```

---

## 📦 Modelli Pydantic

Vedi [app/schemas.py](app/schemas.py) per i dettagli completi.

### Struttura dei Modelli

Per ogni entità sono definiti 3 modelli:

1. **XBase** — Attributi comuni
2. **XCreate** — Modello di input (POST request)
3. **XRead** — Modello di output (Response)

**Regole di progettazione:**
- ✅ `id` compare solo nei modelli `Read`
- ✅ `password` non è presente nei modelli `Read`
- ✅ Relazioni 1:N rappresentate tramite FK
- ✅ Relazioni N:M rappresentate tramite tabella ponte
- ✅ Campi opzionali dichiarati con `Optional[...]`
- ✅ Validazione con `Field` e `EmailStr`

---

## 📝 Documenti Consegnati (Compito 1B)

### 1. **schemas.py**
File con modelli Pydantic per:
- User (UserBase, UserCreate, UserRead)
- Game (GameBase, GameCreate, GameRead)
- Team (TeamBase, TeamCreate, TeamRead)
- Match (MatchBase, MatchCreate, MatchRead)
- TeamMembership (TeamMembershipBase, etc.)

Modelli estesi per relazioni nested:
- UserWithTeams
- TeamWithMembers
- MatchWithDetails

### 2. **examples.json**
Contiene almeno 3 esempi JSON validi:
- User example (POST /users response)
- Team example (POST /teams response)
- Match example (POST /matches response)

Includes anche endpoint MVP examples e extended nested examples.

---

## ⚙️ Setup & Installazione

### Prerequisiti
- Python 3.9+
- Git
- PostgreSQL (opzionale, per produzione)

### Passo 1: Clone del Repository
```bash
git clone <repository-url>
cd GameMatch-bohtipregofunziona
```

### Passo 2: Creazione Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate
```

### Passo 3: Installazione Dipendenze
```bash
pip install -r requirements.txt
```

### Passo 4: Configurazione Environment
```bash
cp .env.example .env
# Modifica .env con le tue impostazioni
```

### Passo 5: Setup Database (da implementare)
```bash
# Per SQLite (automatico)
# Per PostgreSQL: alembic upgrade head
```

### Passo 6: Run del Server
```bash
uvicorn app.main:app --reload
```

Il server sarà disponibile a: **http://localhost:8000**

Documentazione interattiva: **http://localhost:8000/docs** (Swagger UI)

---

## 🔐 Scelte Progettuali

| Scelta | Motivazione |
|--------|-------------|
| **FastAPI** | Framework moderno, veloce, con validazione automatica e documentazione Swagger |
| **Pydantic** | Validazione forte dei dati e separazione model di input/output |
| **SQLAlchemy ORM** | Astrazione database, protezione da SQL injection, supporto a più DB |
| **PostgreSQL** | Database robusto, supporta relazioni complesse, ideale per produzione |
| **JWT** | Autenticazione stateless, scalabile, standard di mercato |
| **Separazione Base/Create/Read** | Sicurezza (password non esposta), flessibilità, chiarezza API |

---

## 🔄 Flusso di Funzionamento

```
1. Utente interagisce con Frontend
   ↓
2. Frontend invia HTTP request a Backend (FastAPI)
   ↓
3. Router riceve request e valida con Pydantic schema
   ↓
4. CRUD esegue operazione sul database
   ↓
5. Database salva/recupera dati
   ↓
6. Response JSON ritorna al Frontend
```

---

## 📈 Sviluppi Futuri

- [ ] Autenticazione con JWT e refresh tokens
- [ ] Sistema ranking ELO
- [ ] Chat in tempo reale (WebSocket)
- [ ] Sistema tornei
- [ ] Integrazione API giochi esterni (League of Legends, Valorant)
- [ ] Dashboard admin
- [ ] Email notifications
- [ ] Rate limiting
- [ ] Analytics e statistiche

---

## 🐛 Problemi Conosciuti & Criticità

1. **Doppia FK verso Team in Match** — Modellato correttamente con explicit foreign_keys
2. **Relazione N:M** — Managed tramite tabella ponte con backref bilaterale
3. **Password in Response** — Esclusa dal modello `UserRead` per sicurezza
4. **Gestione Errori** — Da completare negli endpoint

---

## 📚 Riferimenti & Best Practices

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [REST API Design Best Practices](https://restfulapi.net/)

---

## 📄 Licenza

Progetto didattico — Scuola/Università

---

## 👤 Autore

**Alberto Russo**  
Classe 5WDINF | A.A. 2025/2026  
Docente: Zhongli Filippo Hu

---

**Data Consegna:** Aprile 2026  
**Status:** ✅ Compito 1B Consegnato