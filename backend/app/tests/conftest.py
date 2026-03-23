"""Shared fixtures for integration tests.

Uses an in-memory SQLite database so tests run without an external
PostgreSQL instance while still exercising the full SQLAlchemy stack.
"""

import pytest
from datetime import timedelta

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app
from app.models.models import Player, Country, Game, SpawnedCountry
from app.api.routes.auth import get_current_user, create_access_token, get_password_hash


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_engine():
    """Create an in-memory SQLite engine with FK support."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Enable foreign-key enforcement for SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Provide a transactional database session for each test."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Seed data helpers
# ---------------------------------------------------------------------------

def _seed_countries(db):
    """Insert a standard set of countries and return them."""
    countries = [
        Country(
            name="England",
            default_gold=10,
            default_bonds=0,
            default_territories=5,
            default_goods=4,
            default_people=6,
        ),
        Country(
            name="France",
            default_gold=8,
            default_bonds=1,
            default_territories=6,
            default_goods=5,
            default_people=5,
        ),
    ]
    db.add_all(countries)
    db.commit()
    for c in countries:
        db.refresh(c)
    return countries


def _seed_player(db, username="player1", email="player1@example.com"):
    """Create and return a Player."""
    player = Player(
        username=username,
        email=email,
        password_hash=get_password_hash("testpass"),
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@pytest.fixture()
def seed_data(db_session):
    """Seed two countries and two players; return a dict of entities."""
    countries = _seed_countries(db_session)
    p1 = _seed_player(db_session, "alice", "alice@example.com")
    p2 = _seed_player(db_session, "bob", "bob@example.com")
    return {
        "countries": countries,
        "player1": p1,
        "player2": p2,
    }


# ---------------------------------------------------------------------------
# FastAPI client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(db_session, seed_data):
    """TestClient wired to the in-memory database."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _auth_header(player: Player) -> dict:
    """Build an Authorization header for *player*."""
    token = create_access_token(
        data={"sub": player.username},
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_client(client, db_session, seed_data):
    """Return (client, seed_data, auth_header_helper)."""

    def _override_current_user(player):
        """Return a dependency override for get_current_user."""
        async def _inner():
            return player
        return _inner

    return client, seed_data, _override_current_user
