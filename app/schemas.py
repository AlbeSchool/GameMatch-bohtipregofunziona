"""
GameMatch — Modelli Pydantic per validazione dati
Compito 1B: Dal Design ai Modelli Pydantic
Studente: Alberto Russo
Classe: 5WDINF
Anno: 2025/2026
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
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

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "proGamer",
                    "email": "pro@email.com",
                    "password": "SecurePass123!",
                }
            ]
        }
    )


class UserRead(UserBase):
    """Modello di output per la lettura di un utente (GET /users/{id})"""
    id: int
    is_admin: int = 0

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "username": "proGamer",
                    "email": "pro@email.com",
                    "is_admin": 0,
                }
            ]
        },
    )


# ============================================================================
# 2. GAME — Gestione Giochi
# ============================================================================

class GameBase(BaseModel):
    """Attributi comuni del gioco"""
    name: str = Field(..., min_length=2, max_length=100)
    genre: str = Field(..., min_length=2, max_length=50)


class GameCreate(GameBase):
    """Modello di input per la creazione di un gioco (POST /games)"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "Valorant", "genre": "Tactical Shooter"}
            ]
        }
    )


class GameRead(GameBase):
    """Modello di output per la lettura di un gioco (GET /games/{id})"""
    id: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {"id": 2, "name": "Valorant", "genre": "Tactical Shooter"}
            ]
        },
    )


# ============================================================================
# 3. TEAM — Gestione Team
# ============================================================================

class TeamBase(BaseModel):
    """Attributi comuni del team"""
    name: str = Field(..., min_length=2, max_length=100)


class TeamCreate(TeamBase):
    """Modello di input per la creazione di un team (POST /teams)"""
    creator_id: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "NightRaiders", "creator_id": 1}
            ]
        }
    )


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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 10,
                    "name": "NightRaiders",
                    "creator_id": 1,
                    "members": [
                        {"user_id": 1, "username": "proGamer"},
                        {"user_id": 2, "username": "shadowNinja"},
                    ],
                }
            ]
        },
    )


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
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "scheduled_at": "2026-06-01T18:00:00",
                    "game_id": 2,
                    "team1_id": 10,
                    "team2_id": 11,
                }
            ]
        }
    )


class MatchRead(MatchBase):
    """Modello di output per la lettura di una partita (GET /matches/{id})"""
    id: int
    game: Optional["GameRead"] = None
    team1: Optional["TeamRead"] = None
    team2: Optional["TeamRead"] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 100,
                    "scheduled_at": "2026-06-01T18:00:00",
                    "game_id": 2,
                    "team1_id": 10,
                    "team2_id": 11,
                }
            ]
        },
    )


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

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"username": "Russo", "password": "1234"}
            ]
        }
    )


class LoginResponse(BaseModel):
    """Schema per login response"""
    id: int
    username: str
    email: str
    is_admin: int
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "username": "Russo",
                    "email": "russo@admin.com",
                    "is_admin": 1,
                    "message": "Login effettuato con successo",
                }
            ]
        }
    )


class RegisterRequest(BaseModel):
    """Schema per registrazione"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "newPlayer",
                    "email": "newplayer@email.com",
                    "password": "StrongPass123!",
                    "confirm_password": "StrongPass123!",
                }
            ]
        }
    )


class RegisterResponse(BaseModel):
    """Schema per risposta registrazione"""
    id: int
    username: str
    email: str
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 42,
                    "username": "newPlayer",
                    "email": "newplayer@email.com",
                    "message": "Registrazione completata con successo",
                }
            ]
        }
    )


class AdminUserUpdateRequest(BaseModel):
    """Schema JSON per aggiornare username/email di un utente"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "MarcoPro",
                    "email": "marcopro@email.com",
                }
            ]
        }
    )


class AdminUserRenameRequest(BaseModel):
    """Schema JSON per rinominare un utente"""
    new_username: str = Field(..., min_length=3, max_length=50)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "new_username": "MarcoLegend",
                }
            ]
        }
    )


class ActionResponse(BaseModel):
    """Risposta standard per azioni amministrative"""
    status: str
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "message": "Operazione completata",
                }
            ]
        }
    )
