# Database Migrations with Alembic

This project uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations, providing version-controlled, reversible database changes.

## Configuration

- **`backend/alembic.ini`** - Alembic configuration file. The `sqlalchemy.url` is set dynamically from `app.core.config.settings.DATABASE_URL` in `env.py`.
- **`backend/alembic/env.py`** - Migration environment that imports the application's `Base` metadata and database URL.
- **`backend/alembic/versions/`** - Directory containing migration scripts.
- **`backend/alembic/script.py.mako`** - Template for auto-generated migration files.

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

## How It Works

1. `env.py` imports `Base` from `app.core.database` and all models from `app.models.models`
2. The `DATABASE_URL` is read from `app.core.config.settings`, which loads from environment variables or `.env`
3. Alembic compares the current database schema against the SQLAlchemy model metadata to detect changes
4. Migration scripts in `versions/` are applied in order to bring the database to the desired state

## Adding a New Migration

1. Make changes to models in `backend/app/models/models.py`
2. Auto-generate the migration: `alembic revision --autogenerate -m "add new_column to table"`
3. Review the generated migration in `backend/alembic/versions/`
4. Apply: `alembic upgrade head`
5. Test rollback: `alembic downgrade -1` then `alembic upgrade head`
