# Database Migrations

Empires Online uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations.

## Setup

Alembic configuration lives in `backend/`:

- `backend/alembic.ini` — Alembic configuration (connection URL, logging)
- `backend/alembic/env.py` — Migration environment (loads SQLAlchemy models and metadata)
- `backend/alembic/script.py.mako` — Template for new migration files
- `backend/alembic/versions/` — Migration scripts

The `DATABASE_URL` environment variable overrides the default connection string in `alembic.ini`.

## Running Migrations

From the `backend/` directory:

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## Creating New Migrations

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "description of change"

# Create empty migration
alembic revision -m "description of change"
```

## Migration History

| Revision | Description |
|----------|-------------|
| `001` | Add `stability_checked` column to `games` table |
