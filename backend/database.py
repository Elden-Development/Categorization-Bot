"""
Database configuration and session management for Categorization-Bot
Uses PostgreSQL with SQLAlchemy ORM
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT in ("production", "prod")

# Default credentials that indicate insecure configuration
INSECURE_DB_PATTERNS = [
    "postgres:postgres@",
    "root:root@",
    "admin:admin@",
    "user:password@",
    "password123",
    ":@localhost",  # Empty password
]


def _get_database_url() -> str:
    """
    Get and validate the DATABASE_URL.

    In production: Fails loudly if DATABASE_URL is not set or uses default credentials.
    In development: Warns but allows default credentials for convenience.
    """
    db_url = os.getenv("DATABASE_URL", "").strip()

    # Check if using default/missing URL
    is_missing = not db_url

    if is_missing:
        if IS_PRODUCTION:
            raise RuntimeError(
                "FATAL: DATABASE_URL environment variable is not set. "
                "This is required in production. "
                "Format: postgresql://username:password@host:port/database"
            )
        else:
            # Use default for development
            db_url = "postgresql://postgres:postgres@localhost:5432/categorization_bot"
            print("\n" + "=" * 70)
            print("⚠️  WARNING: DATABASE_URL not configured!")
            print("   Using default local development database.")
            print("\n   To fix, add to your .env file:")
            print('   DATABASE_URL="postgresql://user:pass@host:port/dbname"')
            print("=" * 70 + "\n")
            return db_url

    # Check for insecure credentials in production
    if IS_PRODUCTION:
        for pattern in INSECURE_DB_PATTERNS:
            if pattern in db_url:
                raise RuntimeError(
                    f"FATAL: DATABASE_URL appears to use insecure default credentials. "
                    f"Pattern '{pattern}' detected. "
                    "Please use secure credentials in production."
                )

    return db_url


# Database URL from environment variable
# Format: postgresql://username:password@localhost:5432/database_name
DATABASE_URL = _get_database_url()

# Create SQLAlchemy engine
# For production, use connection pooling: pool_size=10, max_overflow=20
# For development, NullPool is simpler
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # For development
    echo=False,  # Set to True for SQL query logging
    future=True  # Use SQLAlchemy 2.0 style
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True
)

# Base class for all models
Base = declarative_base()


# Dependency to get database session
def get_db():
    """
    FastAPI dependency that provides a database session.

    Usage in endpoints:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    Should be called on application startup.
    """
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def drop_db():
    """
    Drop all database tables.
    WARNING: This will delete all data!
    Only use for development/testing.
    """
    Base.metadata.drop_all(bind=engine)
    print("All database tables dropped!")


# Database connection test
def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("[OK] Database connection successful!")
            return True
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return False
