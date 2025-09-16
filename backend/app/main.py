from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, games, players
from app.core.config import settings

app = FastAPI(
    title="Empires Online API",
    description="Backend API for the Empires Online game",
    version="1.0.0"
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
app.include_router(players.router, prefix="/api/players", tags=["players"])

@app.get("/")
async def root():
    return {"message": "Empires Online API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}