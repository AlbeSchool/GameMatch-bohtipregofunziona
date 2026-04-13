"""
GameMatch — Authentication Module
Gestione login, registrazione e sessioni utente
"""

from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import Optional
from app.models import User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate user by username and password"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    is_admin: int = 0,
    is_team_creator: int = 0,
) -> User:
    """Create a new user"""
    hashed_password = hash_password(password)
    user = User(
        username=username,
        email=email,
        password=hashed_password,
        is_admin=is_admin,
        is_team_creator=is_team_creator,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_all_users(db: Session):
    """Get all users"""
    return db.query(User).all()
