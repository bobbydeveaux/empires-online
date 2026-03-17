from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(100), nullable=False)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    spawned_countries = relationship("SpawnedCountry", back_populates="player")
    created_games = relationship("Game", back_populates="creator")


class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    default_gold = Column(Integer, nullable=False)
    default_bonds = Column(Integer, nullable=False)
    default_territories = Column(Integer, nullable=False)
    default_goods = Column(Integer, nullable=False)
    default_people = Column(Integer, nullable=False)

    # Relationships
    spawned_countries = relationship("SpawnedCountry", back_populates="country")


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    rounds = Column(Integer, nullable=False, default=5)
    rounds_remaining = Column(Integer, nullable=False)
    phase = Column(
        String(20), nullable=False, default="waiting"
    )  # waiting, development, actions, completed
    creator_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    stability_checked = Column(Boolean, default=False)

    # Relationships
    creator = relationship("Player", back_populates="created_games")
    spawned_countries = relationship("SpawnedCountry", back_populates="game")
    game_history = relationship("GameHistory", back_populates="game")


class SpawnedCountry(Base):
    __tablename__ = "spawned_countries"

    id = Column(Integer, primary_key=True, index=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)

    # Game state
    gold = Column(Integer, nullable=False)
    bonds = Column(Integer, nullable=False, default=0)
    territories = Column(Integer, nullable=False)
    goods = Column(Integer, nullable=False)
    people = Column(Integer, nullable=False)
    banks = Column(Integer, nullable=False, default=0)
    supporters = Column(Integer, nullable=False, default=0)
    revolters = Column(Integer, nullable=False, default=0)

    # Phase tracking
    development_completed = Column(Boolean, default=False)
    actions_completed = Column(Boolean, default=False)

    # Relationships
    country = relationship("Country", back_populates="spawned_countries")
    game = relationship("Game", back_populates="spawned_countries")
    player = relationship("Player", back_populates="spawned_countries")
    history = relationship("GameHistory", back_populates="spawned_country")


class GameHistory(Base):
    __tablename__ = "game_history"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    spawned_country_id = Column(
        Integer, ForeignKey("spawned_countries.id"), nullable=False
    )
    round_number = Column(Integer, nullable=False)
    action_type = Column(
        String(50), nullable=False
    )  # development, buy_bond, build_bank, etc.
    details = Column(Text, nullable=True)  # JSON string with action details
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    game = relationship("Game", back_populates="game_history")
    spawned_country = relationship("SpawnedCountry", back_populates="history")
