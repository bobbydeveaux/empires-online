import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, games, players, trades, ws
from app.core.config import settings
from app.services.ws_manager import manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown.

    On startup: connect to PostgreSQL and start LISTEN for game events.
    On shutdown: close the LISTEN connection and NOTIFY pool.
    """
    try:
        await manager.start_listening()
        logger.info("PostgreSQL NOTIFY/LISTEN started")
    except Exception:
        logger.warning("Could not start PostgreSQL listener — running without cross-process fanout")
    yield
    await manager.stop_listening()


app = FastAPI(
    title="Empires Online API",
    description="Backend API for the Empires Online game",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(games.router, prefix="/api/games", tags=["games"])
app.include_router(trades.router, prefix="/api/games", tags=["trades"])
app.include_router(players.router, prefix="/api/players", tags=["players"])
app.include_router(ws.router, tags=["websocket"])


@app.get("/")
async def root():
    return {"message": "Empires Online API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
