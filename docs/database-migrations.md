# Database Migrations with Alembic

## Overview

Empires Online uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations, providing version-controlled, reversible database changes. Migrations run automatically on application startup via `init_db.py`, replacing the previous `Base.metadata.create_all()` approach.

## Configuration

- **`backend/alembic.ini`** - Alembic configuration file. The `sqlalchemy.url` is set dynamically from `app.core.config.settings.DATABASE_URL` in `env.py`.
- **`backend/alembic/env.py`** - Migration environment that imports `Base` metadata from `app.core.database` and all models for autogenerate support.
- **`backend/alembic/versions/`** - Directory containing migration scripts.
- **`backend/alembic/script.py.mako`** - Template for auto-generated migration files.

## How It Works

On startup, `backend/app/init_db.py`:

1. Loads the Alembic config from `alembic.ini`
2. Sets the database URL from application settings
3. Runs `alembic upgrade head` programmatically
4. Seeds initial data (countries, test user) if not already present

Internally, `env.py`:

1. Imports `Base` from `app.core.database` and all models from `app.models.models`
2. Reads `DATABASE_URL` from `app.core.config.settings`, which loads from environment variables or `.env`
3. Alembic compares the current database schema against the SQLAlchemy model metadata to detect changes
4. Migration scripts in `versions/` are applied in order to bring the database to the desired state

## Common Commands

All commands should be run from the `backend/` directory.

### Check current migration status
```bash
alembic current
```

### Apply all pending migrations
```bash
alembic upgrade head
```

### Rollback the last migration
```bash
alembic downgrade -1
```

### Auto-generate a new migration from model changes
```bash
alembic revision --autogenerate -m "description of changes"
```

### Create a blank migration script
```bash
alembic revision -m "description of changes"
```

### View migration history
```bash
alembic history
```

## Adding a New Migration

1. Make changes to models in `backend/app/models/models.py`
2. Auto-generate the migration: `alembic revision --autogenerate -m "add new_column to table"`
3. Review the generated migration in `backend/alembic/versions/`
4. Verify the `revision` and `down_revision` identifiers form a valid chain (each revision ID must be unique, and `down_revision` must point to the previous migration)
5. Apply: `alembic upgrade head`
6. Test rollback: `alembic downgrade -1` then `alembic upgrade head`

## Migration Files

| Revision | Description |
|----------|-------------|
| `001` | Initial schema - all tables (players, countries, games, spawned_countries, game_history) with `stability_checked` column on games |
| `002` | Add `game_results` table for recording game outcomes (winner, rankings, duration) |
