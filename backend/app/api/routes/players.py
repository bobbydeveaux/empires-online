from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Player, Country
from app.schemas.schemas import Player as PlayerSchema, Country as CountrySchema
from app.api.routes.auth import get_current_user

router = APIRouter()


@router.get("/me", response_model=PlayerSchema)
def get_current_player(current_user: Player = Depends(get_current_user)):
    """Get current player information."""
    return current_user


@router.get("/", response_model=List[PlayerSchema])
def list_players(db: Session = Depends(get_db)):
    """List all players (for leaderboards, etc.)."""
    return db.query(Player).all()


@router.get("/countries", response_model=List[CountrySchema])
def list_countries(db: Session = Depends(get_db)):
    """List all available countries."""
    return db.query(Country).all()
