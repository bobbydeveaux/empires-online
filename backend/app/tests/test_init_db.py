"""Unit tests for database initialization and Alembic migration setup."""

import os
from unittest.mock import patch, MagicMock, call

import pytest

from app.init_db import run_migrations, init_db


class TestRunMigrations:
    """Verify run_migrations() invokes Alembic upgrade correctly."""

    @patch("app.init_db.command")
    @patch("app.init_db.Config")
    def test_run_migrations_calls_upgrade_head(self, mock_config_cls, mock_command):
        mock_cfg = MagicMock()
        mock_config_cls.return_value = mock_cfg

        run_migrations()

        # Should create an Alembic Config pointing at alembic.ini
        mock_config_cls.assert_called_once()
        config_path = mock_config_cls.call_args[0][0]
        assert config_path.endswith("alembic.ini")

        # Should set the database URL from settings
        mock_cfg.set_main_option.assert_called_once()
        args = mock_cfg.set_main_option.call_args[0]
        assert args[0] == "sqlalchemy.url"

        # Should run upgrade to head
        mock_command.upgrade.assert_called_once_with(mock_cfg, "head")


class TestInitDb:
    """Verify init_db() runs migrations and seeds data."""

    @patch("app.init_db.get_password_hash", return_value="hashed")
    @patch("app.init_db.sessionmaker")
    @patch("app.init_db.create_engine")
    @patch("app.init_db.run_migrations")
    def test_init_db_runs_migrations_first(
        self, mock_run_migrations, mock_engine, mock_sessionmaker, mock_hash
    ):
        mock_session = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        # No existing countries or users
        mock_session.query.return_value.count.return_value = 0

        init_db()

        mock_run_migrations.assert_called_once()

    @patch("app.init_db.get_password_hash", return_value="hashed")
    @patch("app.init_db.sessionmaker")
    @patch("app.init_db.create_engine")
    @patch("app.init_db.run_migrations")
    def test_init_db_seeds_countries_when_empty(
        self, mock_run_migrations, mock_engine, mock_sessionmaker, mock_hash
    ):
        mock_session = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        mock_session.query.return_value.count.return_value = 0

        init_db()

        # Should add 6 countries + 1 test user = 7 add() calls
        assert mock_session.add.call_count == 7
        mock_session.commit.assert_called_once()

    @patch("app.init_db.get_password_hash", return_value="hashed")
    @patch("app.init_db.sessionmaker")
    @patch("app.init_db.create_engine")
    @patch("app.init_db.run_migrations")
    def test_init_db_skips_seed_when_data_exists(
        self, mock_run_migrations, mock_engine, mock_sessionmaker, mock_hash
    ):
        mock_session = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        # Data already exists
        mock_session.query.return_value.count.return_value = 5

        init_db()

        mock_session.add.assert_not_called()
        mock_session.commit.assert_called_once()

    @patch("app.init_db.get_password_hash", return_value="hashed")
    @patch("app.init_db.sessionmaker")
    @patch("app.init_db.create_engine")
    @patch("app.init_db.run_migrations")
    def test_init_db_rolls_back_on_error(
        self, mock_run_migrations, mock_engine, mock_sessionmaker, mock_hash
    ):
        mock_session = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        mock_session.query.side_effect = Exception("db error")

        init_db()

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
