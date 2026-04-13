"""
GameMatch Routers — API Endpoints for Matches
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import MatchCreate, MatchRead
from app.database import get_db

router = APIRouter(
    prefix="/matches",
    tags=["matches"],
)


@router.post("/", response_model=MatchRead)
def create_match(match: MatchCreate, db: Session = Depends(get_db)):
    """Create a new match (POST /matches)"""
    # Implementation will be added
    pass


@router.get("/{match_id}", response_model=MatchRead)
def get_match(match_id: int, db: Session = Depends(get_db)):
    """Retrieve match details (GET /matches/{id})"""
    # Implementation will be added
    pass
