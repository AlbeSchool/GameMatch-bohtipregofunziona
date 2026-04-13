"""
GameMatch — SQLAlchemy ORM Models
Definizioni delle tabelle del database
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


# Tabella associativa per la relazione N:M tra User e Team
team_membership = Table(
    'team_membership',
    Base.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('user_id', Integer, ForeignKey('user.id', ondelete='CASCADE')),
    Column('team_id', Integer, ForeignKey('team.id', ondelete='CASCADE')),
)


class User(Base):
    """Modello User — Utenti della piattaforma"""
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_admin = Column(Integer, default=0)
    is_team_creator = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relazioni
    teams_created = relationship("Team", back_populates="creator")
    teams_member = relationship(
        "Team",
        secondary=team_membership,
        back_populates="members"
    )
    profile = relationship(
        "PlayerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    team_requests = relationship(
        "TeamRequest",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    creator_role_requests = relationship(
        "TeamCreatorRequest",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Game(Base):
    """Modello Game — Giochi supportati"""
    __tablename__ = "game"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    genre = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relazioni
    matches = relationship("Match", back_populates="game")


class Team(Base):
    """Modello Team — Team di gioco"""
    __tablename__ = "team"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    creator_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relazioni
    creator = relationship("User", back_populates="teams_created", foreign_keys=[creator_id])
    members = relationship(
        "User",
        secondary=team_membership,
        back_populates="teams_member"
    )
    matches_as_team1 = relationship(
        "Match",
        back_populates="team1",
        foreign_keys="[Match.team1_id]"
    )
    matches_as_team2 = relationship(
        "Match",
        back_populates="team2",
        foreign_keys="[Match.team2_id]"
    )
    recruitment_posts = relationship(
        "TeamRecruitment",
        back_populates="team",
        cascade="all, delete-orphan"
    )
    tryout_sessions = relationship(
        "TryoutSession",
        back_populates="team",
        cascade="all, delete-orphan"
    )


class Match(Base):
    """Modello Match — Partite pianificate"""
    __tablename__ = "match"

    id = Column(Integer, primary_key=True, index=True)
    scheduled_at = Column(DateTime, nullable=False)
    game_id = Column(Integer, ForeignKey('game.id'), nullable=False)
    team1_id = Column(Integer, ForeignKey('team.id'), nullable=False)
    team2_id = Column(Integer, ForeignKey('team.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relazioni
    game = relationship("Game", back_populates="matches")
    team1 = relationship(
        "Team",
        back_populates="matches_as_team1",
        foreign_keys=[team1_id]
    )
    team2 = relationship(
        "Team",
        back_populates="matches_as_team2",
        foreign_keys=[team2_id]
    )


class PlayerProfile(Base):
    """Profilo competitivo di un utente per il matchmaking"""
    __tablename__ = "player_profile"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)
    preferred_game = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)
    rank = Column(String(30), nullable=False)
    weekly_hours = Column(Integer, default=5, nullable=False)
    notes = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class TeamRequest(Base):
    """Richiesta matchmaking inviata da utente normale"""
    __tablename__ = "team_request"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    game = Column(String(50), nullable=False)
    rank = Column(String(30), nullable=False)
    role = Column(String(50), nullable=True)
    attack_main = Column(String(50), nullable=True)
    defense_main = Column(String(50), nullable=True)
    preferred_mode = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    recommended_team = Column(String(100), nullable=True)
    response_message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="team_requests")


class TeamCreatorRequest(Base):
    """Richiesta utente normale per diventare creatore di team"""
    __tablename__ = "team_creator_request"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    message = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    seen_by_user = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="creator_role_requests")


class TeamRecruitment(Base):
    """Informazioni di recruiting di un team creato da un creatore team"""
    __tablename__ = "team_recruitment"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('team.id', ondelete='CASCADE'), nullable=False, index=True)
    game = Column(String(100), nullable=False)
    looking_for = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    team = relationship("Team", back_populates="recruitment_posts")


class TryoutSession(Base):
    """Sessione di provino aperta da un creatore team"""
    __tablename__ = "tryout_session"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('team.id', ondelete='CASCADE'), nullable=False, index=True)
    scheduled_at = Column(DateTime, nullable=False)
    slots = Column(Integer, nullable=False, default=4)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="open")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    team = relationship("Team", back_populates="tryout_sessions")
