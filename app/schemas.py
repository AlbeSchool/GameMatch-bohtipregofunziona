"""
GameMatch — Modelli Pydantic per validazione dati
Compito 1B: Dal Design ai Modelli Pydantic
Studente: Alberto Russo
Classe: 5WDINF
Anno: 2025/2026
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ============================================================================
# 1. USER — Gestione Utenti
# ============================================================================

class UserBase(BaseModel):
    """Attributi comuni dell'utente"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """Modello di input per la creazione di un utente (POST /users)"""
    password: str = Field(..., min_length=6)


class UserRead(UserBase):
    """Modello di output per la lettura di un utente (GET /users/{id})"""
    id: int
    is_admin: int = 0

    class Config:
        from_attributes = True


# ============================================================================
# 2. GAME — Gestione Giochi
# ============================================================================

class GameBase(BaseModel):
    """Attributi comuni del gioco"""
    name: str = Field(..., min_length=2, max_length=100)
    genre: str = Field(..., min_length=2, max_length=50)


class GameCreate(GameBase):
    """Modello di input per la creazione di un gioco (POST /games)"""
    pass


class GameRead(GameBase):
    """Modello di output per la lettura di un gioco (GET /games/{id})"""
    id: int

    class Config:
        from_attributes = True


# ============================================================================
# 3. TEAM — Gestione Team
# ============================================================================

class TeamBase(BaseModel):
    """Attributi comuni del team"""
    name: str = Field(..., min_length=2, max_length=100)


class TeamCreate(TeamBase):
    """Modello di input per la creazione di un team (POST /teams)"""
    creator_id: int


class TeamMembershipRead(BaseModel):
    """Modello per visualizzare i membri di un team"""
    user_id: int
    username: str

    class Config:
        from_attributes = True


class TeamRead(TeamBase):
    """Modello di output per la lettura di un team (GET /teams/{id})"""
    id: int
    creator_id: int
    members: Optional[List[TeamMembershipRead]] = []

    class Config:
        from_attributes = True


# ============================================================================
# 4. TEAM MEMBERSHIP — Tabella Ponte (Relazione N:M)
# ============================================================================

class TeamMembershipBase(BaseModel):
    """Attributi comuni dell'appartenenza a un team"""
    user_id: int
    team_id: int


class TeamMembershipCreate(TeamMembershipBase):
    """Modello di input per l'aggiunta di un membro a un team"""
    pass


class TeamMembershipReadDetailed(TeamMembershipBase):
    """Modello di output completo per TeamMembership"""
    id: int

    class Config:
        from_attributes = True


# ============================================================================
# 5. MATCH — Gestione Partite
# ============================================================================

class MatchBase(BaseModel):
    """Attributi comuni della partita"""
    scheduled_at: datetime = Field(..., description="Data e ora della partita")
    game_id: int = Field(..., description="ID del gioco")
    team1_id: int = Field(..., description="ID del primo team")
    team2_id: int = Field(..., description="ID del secondo team")


class MatchCreate(MatchBase):
    """Modello di input per la creazione di una partita (POST /matches)"""
    pass


class MatchRead(MatchBase):
    """Modello di output per la lettura di una partita (GET /matches/{id})"""
    id: int
    game: Optional["GameRead"] = None
    team1: Optional["TeamRead"] = None
    team2: Optional["TeamRead"] = None

    class Config:
        from_attributes = True


# ============================================================================
# Modelli Alternativi con Relazioni Nested (Optional)
# ============================================================================

class UserWithTeams(UserBase):
    """
    Modello esteso: Utente con lista di team associati.
    Utilizzato per endpoint GET /users/{id} con dettagli completi.
    """
    id: int
    teams: Optional[List[TeamRead]] = []

    class Config:
        from_attributes = True


class TeamWithMembers(TeamBase):
    """
    Modello esteso: Team con lista completa di membri.
    Utilizzato per endpoint GET /teams/{id} con dettagli completi.
    """
    id: int
    creator_id: int
    members: Optional[List[UserRead]] = []

    class Config:
        from_attributes = True


class MatchWithDetails(MatchBase):
    """
    Modello esteso: Partita con dettagli dei team e del gioco.
    Utilizzato per endpoint GET /matches/{id} con dettagli completi.
    """
    id: int
    game: Optional[GameRead] = None
    team1: Optional[TeamRead] = None
    team2: Optional[TeamRead] = None

    class Config:
        from_attributes = True


# ============================================================================
# Modelli per Risposte Massicce e Paginazione (Optional)
# ============================================================================

class PaginatedResponse(BaseModel):
    """Wrapper per risposte paginate"""
    page: int
    per_page: int
    total: int
    items: List[dict]


# ============================================================================
# Forward Reference Resolution (per circular dependencies)
# ============================================================================

MatchRead.model_rebuild()


# ============================================================================
# LOGIN & REGISTRATION SCHEMAS
# ============================================================================

class LoginRequest(BaseModel):
    """Schema per login request"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Schema per login response"""
    id: int
    username: str
    email: str
    is_admin: int
    message: str


class RegisterRequest(BaseModel):
    """Schema per registrazione"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)


class RegisterResponse(BaseModel):
    """Schema per risposta registrazione"""
    id: int
    username: str
    email: str
    message: str
