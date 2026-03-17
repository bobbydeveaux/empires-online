# Database Migrations with Alembic

## Overview

Empires Online uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations. Migrations run automatically on application startup via `init_db.py`, replacing the previous `Base.metadata.create_all()` approach.

## Configuration

- **`backend/alembic.ini`** - Alembic configuration file. The database URL is set programmatically from `app.core.config.Settings`.
- **`backend/alembic/env.py`** - Environment setup that imports `Base` metadata from `app.core.database` and all models for autogenerate support.
- **`backend/alembic/versions/`** - Migration scripts directory.

## How It Works

On startup, `backend/app/init_db.py`:

1. Loads the Alembic config from `alembic.ini`
2. Sets the database URL from application settings
3. Runs `alembic upgrade head` programmatically
4. Seeds initial data (countries, test user) if not already present

## Creating New Migrations

From the `backend/` directory:

```bash
# Auto-generate a migration from model changes
alembic revision --autogenerate -m "description of change"

# Create an empty migration to fill in manually
alembic revision -m "description of change"
```

## Common Commands

```bash
cd backend

# Check current migration version
alembic current

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Migration Files

| Revision | Description |
|----------|-------------|
| `001` | Initial schema - all tables (players, countries, games, spawned_countries, game_history) with `stability_checked` column on games |
