"""
Database Initialization Script for Categorization-Bot
Run this script to set up the database tables
"""

import sys
import os
from sqlalchemy import create_engine, text
from database import Base, engine, test_connection, DATABASE_URL
import models  # Import all models to register them with Base
from auth import hash_password


def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] All tables created successfully!")
        return True
    except Exception as e:
        print(f"[ERROR] Error creating tables: {e}")
        return False


def create_extensions():
    """Create PostgreSQL extensions (for full-text search)"""
    print("Creating PostgreSQL extensions...")
    try:
        with engine.connect() as connection:
            # Create pg_trgm extension for full-text search
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            connection.commit()
            print("[OK] Extensions created successfully!")
        return True
    except Exception as e:
        print(f"[ERROR] Error creating extensions: {e}")
        print("  Note: This might fail if you don't have superuser privileges.")
        print("  Full-text search will still work, but may be less efficient.")
        return False


def create_test_user():
    """Create a test user for development"""
    print("\nCreating test user...")
    from sqlalchemy.orm import Session

    try:
        db = Session(bind=engine)

        # Check if user already exists
        existing_user = db.query(models.User).filter(
            models.User.username == "testuser"
        ).first()

        if existing_user:
            print("  Test user already exists. Skipping...")
            db.close()
            return True

        # Create test user
        test_user = models.User(
            username="testuser",
            email="test@example.com",
            password_hash=hash_password("password123"),
            is_active=True
        )

        db.add(test_user)
        db.commit()
        db.close()

        print("[OK] Test user created successfully!")
        print("  Username: testuser")
        print("  Password: password123")
        print("  Email: test@example.com")
        return True

    except Exception as e:
        print(f"[ERROR] Error creating test user: {e}")
        return False


def verify_tables():
    """Verify that all tables were created"""
    print("\nVerifying tables...")
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))

            tables = [row[0] for row in result]

            expected_tables = [
                'users', 'documents', 'transactions', 'vendor_research',
                'categorizations', 'user_corrections', 'bank_statements',
                'bank_transactions', 'reconciliation_matches',
                'activity_log', 'saved_searches'
            ]

            print(f"\n  Found {len(tables)} tables:")
            for table in tables:
                status = "[OK]" if table in expected_tables else "?"
                print(f"    {status} {table}")

            missing = set(expected_tables) - set(tables)
            if missing:
                print(f"\n  [WARNING] Missing tables: {', '.join(missing)}")
                return False

            print("\n[OK] All expected tables found!")
            return True

    except Exception as e:
        print(f"[ERROR] Error verifying tables: {e}")
        return False


def show_database_info():
    """Display database connection information"""
    print("\n" + "=" * 60)
    print("DATABASE INFORMATION")
    print("=" * 60)

    # Parse DATABASE_URL to show connection details (hide password)
    from urllib.parse import urlparse

    try:
        parsed = urlparse(DATABASE_URL)
        print(f"  Host: {parsed.hostname}")
        print(f"  Port: {parsed.port}")
        print(f"  Database: {parsed.path[1:]}")  # Remove leading /
        print(f"  Username: {parsed.username}")
        print(f"  Password: {'*' * 8}")
    except:
        print(f"  Connection String: {DATABASE_URL}")

    print("=" * 60 + "\n")


def main():
    """Main initialization routine"""
    print("\n" + "=" * 60)
    print("CATEGORIZATION-BOT DATABASE INITIALIZATION")
    print("=" * 60 + "\n")

    show_database_info()

    # Test connection
    print("Step 1: Testing database connection...")
    if not test_connection():
        print("\n[ERROR] Database connection failed!")
        print("\nPlease check:")
        print("  1. PostgreSQL is running")
        print("  2. DATABASE_URL in .env is correct")
        print("  3. Database exists and user has permissions")
        sys.exit(1)

    print()

    # Create extensions
    print("Step 2: Creating PostgreSQL extensions...")
    create_extensions()
    print()

    # Create tables
    print("Step 3: Creating database tables...")
    if not create_tables():
        print("\n[ERROR] Failed to create tables!")
        sys.exit(1)

    print()

    # Verify tables
    print("Step 4: Verifying tables...")
    if not verify_tables():
        print("\n[WARNING] Some tables may be missing!")

    # Create test user
    print("\nStep 5: Creating test user...")
    create_test_user()

    print("\n" + "=" * 60)
    print("[OK] DATABASE INITIALIZATION COMPLETE!")
    print("=" * 60)
    print("\nYour database is ready to use!")
    print("\nNext steps:")
    print("  1. Start the backend server: uvicorn main:app --reload")
    print("  2. Start the frontend server: npm start")
    print("  3. Login with test credentials:")
    print("     Username: testuser")
    print("     Password: password123")
    print("\n")


if __name__ == "__main__":
    main()
