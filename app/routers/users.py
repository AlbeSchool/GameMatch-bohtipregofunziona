"""
GameMatch Routers — API Endpoints for Users
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import UserCreate, UserRead
from app.database import get_db

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.post("/", response_model=UserRead)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user (POST /users)"""
    # Implementation will be added
    pass


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Retrieve user details (GET /users/{id})"""
    # Implementation will be added
    pass
