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
    
    db.close()


def get_db():
    """Dependency injection per sessioni database"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
