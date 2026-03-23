from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime


# Player schemas
class PlayerBase(BaseModel):
    username: str
    email: EmailStr


class PlayerCreate(PlayerBase):
    password: str


class PlayerLogin(BaseModel):
    username: str
    password: str


class Player(PlayerBase):
    id: int
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Country schemas
class CountryBase(BaseModel):
    name: str
    default_gold: int
    default_bonds: int
    default_territories: int
    default_goods: int
    default_people: int


class Country(CountryBase):
    id: int

    class Config:
        from_attributes = True


# Game schemas
class GameCreate(BaseModel):
    rounds: int = 5
    countries: List[str]


class GameJoin(BaseModel):
    country_id: int


class Game(BaseModel):
    id: int
    rounds: int
    rounds_remaining: int
    phase: str
    creator_id: int
    created_at: datetime
    started_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# SpawnedCountry schemas
class SpawnedCountryBase(BaseModel):
    gold: int
    bonds: int
    territories: int
    goods: int
    people: int
    banks: int
    supporters: int
    revolters: int


class SpawnedCountry(SpawnedCountryBase):
    id: int
    country_id: int
    game_id: int
    player_id: int
    development_completed: bool
    actions_completed: bool

    class Config:
        from_attributes = True


class SpawnedCountryWithDetails(SpawnedCountry):
    country: Country
    player: Player


# Action schemas
class GameAction(BaseModel):
    action: str
    quantity: int = 1


# Response schemas
class DevelopmentResult(BaseModel):
    success: bool
    new_state: Dict[str, Any]
    changes: Dict[str, Any]


class ActionResult(BaseModel):
    success: bool
    new_state: Optional[Dict[str, Any]] = None
    changes: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class VictoryPoints(BaseModel):
    total_score: float
    breakdown: Dict[str, Any]


class GameResult(BaseModel):
    id: int
    game_id: int
    winner_country_id: int
    winner_player_id: int
    duration_rounds: int
    finished_at: Optional[datetime] = None
    final_rankings: str  # JSON string

    class Config:
        from_attributes = True


class GameState(BaseModel):
    game: Game
    players: List[SpawnedCountryWithDetails]
    leaderboard: List[Dict[str, Any]]


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
