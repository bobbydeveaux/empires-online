"""
Database initialization script for Empires Online.
Creates tables and seeds initial data.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.core.config import settings
from app.models.models import Country, Player
from app.api.routes.auth import get_password_hash


def init_db():
    """Initialize database with tables and seed data."""
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Check if countries already exist
        existing_countries = db.query(Country).count()
        if existing_countries == 0:
            # Seed countries based on the game design
            countries_data = [
                {
                    "name": "France",
                    "default_gold": 5,
                    "default_bonds": 1,
                    "default_territories": 4,
                    "default_goods": 2,
                    "default_people": 3,
                },
                {
                    "name": "England",
                    "default_gold": 6,
                    "default_bonds": 1,
                    "default_territories": 3,
                    "default_goods": 3,
                    "default_people": 3,
                },
                {
                    "name": "Spain",
                    "default_gold": 4,
                    "default_bonds": 2,
                    "default_territories": 5,
                    "default_goods": 2,
                    "default_people": 4,
                },
                {
                    "name": "Russia",
                    "default_gold": 3,
                    "default_bonds": 0,
                    "default_territories": 6,
                    "default_goods": 1,
                    "default_people": 5,
                },
                {
                    "name": "Austria",
                    "default_gold": 5,
                    "default_bonds": 2,
                    "default_territories": 3,
                    "default_goods": 3,
                    "default_people": 2,
                },
                {
                    "name": "Prussia",
                    "default_gold": 4,
                    "default_bonds": 1,
                    "default_territories": 3,
                    "default_goods": 2,
                    "default_people": 4,
                },
            ]

            for country_data in countries_data:
                country = Country(**country_data)
                db.add(country)

            print("Seeded countries data")

        # Create a test user if none exists
        existing_users = db.query(Player).count()
        if existing_users == 0:
            test_user = Player(
                username="testuser",
                email="test@example.com",
                password_hash=get_password_hash("testpass123"),
                email_verified=True,
            )
            db.add(test_user)
            print("Created test user: testuser / testpass123")

        db.commit()
        print("Database initialization completed successfully")

    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
