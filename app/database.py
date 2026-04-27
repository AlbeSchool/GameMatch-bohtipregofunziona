"""
GameMatch — Database Configuration
Supporto per PostgreSQL (produzione) e SQLite (sviluppo)
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database URL - seleziona a seconda dell'ambiente
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./gamematch.db"  # Default per sviluppo locale
)

# Abilita check_same_thread solo per SQLite
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL o altri database
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def init_db() -> None:
    """Inizializza il database creando tutte le tabelle"""
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    seed_users()


def ensure_schema_compatibility() -> None:
    """Aggiunge colonne mancanti per installazioni esistenti senza migrazioni Alembic."""
    inspector = inspect(engine)
    if "user" not in inspector.get_table_names():
        return

    user_columns = [col["name"] for col in inspector.get_columns("user")]
    if "is_team_creator" not in user_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE user ADD COLUMN is_team_creator INTEGER DEFAULT 0"))

    if "team_creator_request" in inspector.get_table_names():
        creator_columns = [col["name"] for col in inspector.get_columns("team_creator_request")]
        if "seen_by_user" not in creator_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE team_creator_request ADD COLUMN seen_by_user INTEGER DEFAULT 0"))


def seed_users() -> None:
    """Popola il database con utenti di default"""
    from app.auth import create_user, get_user_by_username
    from app.models import TeamRequest, User
    
    db = SessionLocal()
    
    # Admin user
    admin = get_user_by_username(db, "Russo")
    if not admin:
        create_user(db, "Russo", "russo@admin.com", "1234", is_admin=1)
        print("✅ Admin user created: Russo / 1234")
    
    # Regular users
    test_users = [
        ("Marco", "marco@email.com", "password123"),
        ("Sofia", "sofia@email.com", "password123"),
        ("Luca", "luca@email.com", "password123"),
        ("Emma", "emma@email.com", "password123"),
        ("Alex", "alex@email.com", "password123"),
        ("Nina", "nina@email.com", "password123"),
        ("Diego", "diego@email.com", "password123"),
        ("Sara", "sara@email.com", "password123"),
        ("Tommaso", "tommaso@email.com", "password123"),
        ("Giulia", "giulia@email.com", "password123"),
        ("Elena", "elena@email.com", "password123"),
        ("Francesco", "francesco@email.com", "password123"),
        ("Chiara", "chiara@email.com", "password123"),
        ("Matteo", "matteo@email.com", "password123"),
        ("Irene", "irene@email.com", "password123"),
        ("Davide", "davide@email.com", "password123"),
        ("Aurora", "aurora@email.com", "password123"),
        ("Simone", "simone@email.com", "password123"),
        ("Noemi", "noemi@email.com", "password123"),
        ("Leonardo", "leonardo@email.com", "password123"),
    ]
    
    for username, email, password in test_users:
        user = get_user_by_username(db, username)
        if not user:
            create_user(db, username, email, password, is_admin=0, is_team_creator=0)
            print(f"✅ User created: {username}")

    # Team creator users (not site admins)
    team_creators = [
        ("TeamAlphaAdmin", "teamalpha@creators.com", "creator123"),
        ("TeamBravoAdmin", "teambravo@creators.com", "creator123"),
        ("TeamDeltaAdmin", "teamdelta@creators.com", "creator123"),
    ]

    for username, email, password in team_creators:
        creator = get_user_by_username(db, username)
        if not creator:
            create_user(db, username, email, password, is_admin=0, is_team_creator=1)
            print(f"✅ Team creator created: {username}")
        elif not getattr(creator, "is_team_creator", 0):
            creator.is_team_creator = 1
            db.commit()
            print(f"✅ Team creator role updated: {username}")

    users_by_username = {user.username: user for user in db.query(User).all()}

    request_seeds = [
        {"username": "Marco", "game": "Valorant", "rank": "Gold", "role": "Duelist", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Night Ravens", "response_message": "Match trovato: Night Ravens. Ruolo richiesto: Controller."},
        {"username": "Sofia", "game": "Fortnite", "rank": "Platinum", "role": "Fragger", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Build Masters", "response_message": "Match trovato: Build Masters. Ruolo richiesto: Fragger."},
        {"username": "Luca", "game": "Rainbow Six Siege", "rank": "Silver", "role": "", "preferred_mode": "Entry", "attack_main": "Ash", "defense_main": "Mute", "recommended_team": "Breach Protocol", "response_message": "Match trovato: Breach Protocol. Profilo valido per il mode Entry."},
        {"username": "Emma", "game": "Rocket League", "rank": "Diamond", "role": "Striker", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Blue Strikers", "response_message": "Match trovato: Blue Strikers. Ruolo richiesto: Striker."},
        {"username": "Alex", "game": "Valorant", "rank": "Platinum", "role": "Sentinel", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Night Ravens", "response_message": "Match trovato: Night Ravens. Ruolo richiesto: Controller."},
        {"username": "Nina", "game": "Fortnite", "rank": "Gold", "role": "Support", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Build Masters", "response_message": "Match trovato: Build Masters. Ruolo richiesto: Fragger."},
        {"username": "Diego", "game": "Rainbow Six Siege", "rank": "Gold", "role": "", "preferred_mode": "Anchor", "attack_main": "Sledge", "defense_main": "Rook", "recommended_team": "Site Holders", "response_message": "Match trovato: Site Holders. Profilo valido per il mode Anchor."},
        {"username": "Sara", "game": "Rocket League", "rank": "Champion", "role": "Playmaker", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Supersonic Trio", "response_message": "Match trovato: Supersonic Trio. Ruolo richiesto: Flex."},
        {"username": "Tommaso", "game": "Valorant", "rank": "Ascendant", "role": "Initiator", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Pulse Alpha", "response_message": "Match trovato: Pulse Alpha. Ruolo richiesto: Initiator."},
        {"username": "Giulia", "game": "Rainbow Six Siege", "rank": "Platinum", "role": "", "preferred_mode": "Flex", "attack_main": "Iana", "defense_main": "Mira", "recommended_team": "Silent Drones", "response_message": "Match trovato: Silent Drones. Profilo valido per il mode Flex."},
        {"username": "Elena", "game": "Fortnite", "rank": "Diamond", "role": "Flex", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Storm Breakers", "response_message": "Match trovato: Storm Breakers. Ruolo richiesto: IGL."},
        {"username": "Francesco", "game": "Valorant", "rank": "Silver", "role": "Controller", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Night Ravens", "response_message": "Match trovato: Night Ravens. Ruolo richiesto: Controller."},
        {"username": "Chiara", "game": "Rocket League", "rank": "Gold", "role": "Defender", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Goal Keepers", "response_message": "Match trovato: Goal Keepers. Ruolo richiesto: Defender."},
        {"username": "Matteo", "game": "Rainbow Six Siege", "rank": "Emerald", "role": "", "preferred_mode": "Roamer", "attack_main": "Flores", "defense_main": "Vigil", "recommended_team": "Site Holders", "response_message": "Match trovato: Site Holders. Profilo valido per il mode Anchor."},
        {"username": "Irene", "game": "Valorant", "rank": "Gold", "role": "Duelist", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Vortex Elite", "response_message": "Match trovato: Vortex Elite. Ruolo richiesto: Duelist."},
        {"username": "Davide", "game": "Fortnite", "rank": "Platinum", "role": "IGL", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Build Masters", "response_message": "Match trovato: Build Masters. Ruolo richiesto: Fragger."},
        {"username": "Aurora", "game": "Rocket League", "rank": "Platinum", "role": "Flex", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Blue Strikers", "response_message": "Match trovato: Blue Strikers. Ruolo richiesto: Striker."},
        {"username": "Simone", "game": "Rainbow Six Siege", "rank": "Gold", "role": "", "preferred_mode": "Support", "attack_main": "Twitch", "defense_main": "Echo", "recommended_team": "Breach Protocol", "response_message": "Match trovato: Breach Protocol. Profilo valido per il mode Entry."},
        {"username": "Noemi", "game": "Valorant", "rank": "Platinum", "role": "Controller", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Night Ravens", "response_message": "Match trovato: Night Ravens. Ruolo richiesto: Controller."},
        {"username": "Leonardo", "game": "Fortnite", "rank": "Diamond", "role": "Flex", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Zero Ping", "response_message": "Match trovato: Zero Ping. Ruolo richiesto: Flex."},
        {"username": "TeamAlphaAdmin", "game": "Valorant", "rank": "Diamond", "role": "Initiator", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Pulse Alpha", "response_message": "Match trovato: Pulse Alpha. Ruolo richiesto: Initiator."},
        {"username": "TeamBravoAdmin", "game": "Rainbow Six Siege", "rank": "Silver", "role": "", "preferred_mode": "Entry", "attack_main": "Ace", "defense_main": "Kapkan", "recommended_team": "Breach Protocol", "response_message": "Match trovato: Breach Protocol. Profilo valido per il mode Entry."},
        {"username": "TeamDeltaAdmin", "game": "Rocket League", "rank": "Champion", "role": "Striker", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Supersonic Trio", "response_message": "Match trovato: Supersonic Trio. Ruolo richiesto: Flex."},
        {"username": "Marco", "game": "Fortnite", "rank": "Gold", "role": "Support", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Storm Breakers", "response_message": "Match trovato: Storm Breakers. Ruolo richiesto: IGL."},
        {"username": "Sofia", "game": "Valorant", "rank": "Diamond", "role": "Initiator", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Pulse Alpha", "response_message": "Match trovato: Pulse Alpha. Ruolo richiesto: Initiator."},
        {"username": "Luca", "game": "Rocket League", "rank": "Gold", "role": "Defender", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Goal Keepers", "response_message": "Match trovato: Goal Keepers. Ruolo richiesto: Defender."},
        {"username": "Emma", "game": "Rainbow Six Siege", "rank": "Platinum", "role": "", "preferred_mode": "Flex", "attack_main": "Zofia", "defense_main": "Maestro", "recommended_team": "Silent Drones", "response_message": "Match trovato: Silent Drones. Profilo valido per il mode Flex."},
        {"username": "Alex", "game": "Valorant", "rank": "Bronze", "role": "Sentinel", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Night Ravens", "response_message": "Match trovato: Night Ravens. Ruolo richiesto: Controller."},
        {"username": "Nina", "game": "Fortnite", "rank": "Diamond", "role": "IGL", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Zero Ping", "response_message": "Match trovato: Zero Ping. Ruolo richiesto: Flex."},
        {"username": "Giulia", "game": "Valorant", "rank": "Silver", "role": "Controller", "preferred_mode": "", "attack_main": "", "defense_main": "", "recommended_team": "Night Ravens", "response_message": "Match trovato: Night Ravens. Ruolo richiesto: Controller."},
    ]

    for seed in request_seeds:
        user = users_by_username.get(seed["username"])
        if not user or user.is_admin:
            continue

        existing_request = (
            db.query(TeamRequest)
            .filter(
                TeamRequest.user_id == user.id,
                TeamRequest.game == seed["game"],
                TeamRequest.rank == seed["rank"],
                TeamRequest.role == (seed["role"] or None),
                TeamRequest.attack_main == (seed["attack_main"] or None),
                TeamRequest.defense_main == (seed["defense_main"] or None),
                TeamRequest.preferred_mode == (seed["preferred_mode"] or None),
            )
            .first()
        )
        if existing_request:
            continue

        db.add(
            TeamRequest(
                user_id=user.id,
                game=seed["game"],
                rank=seed["rank"],
                role=seed["role"] or None,
                attack_main=seed["attack_main"] or None,
                defense_main=seed["defense_main"] or None,
                preferred_mode=seed["preferred_mode"] or None,
                notes="Richiesta demo generata automaticamente.",
                recommended_team=seed["recommended_team"],
                response_message=seed["response_message"],
            )
        )

    db.commit()
    
    db.close()


def get_db():
    """Dependency injection per sessioni database"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
