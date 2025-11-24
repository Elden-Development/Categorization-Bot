"""Quick script to create a test user for local testing"""
import sys
from database import SessionLocal
from auth import hash_password
import models

def create_test_user():
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(models.User).filter(
            models.User.email == "test@example.com"
        ).first()

        if existing_user:
            print("[OK] Test user already exists!")
            print(f"  Email: test@example.com")
            print(f"  Password: password123")
            return

        # Create new test user
        hashed_password = hash_password("password123")
        test_user = models.User(
            email="test@example.com",
            username="testuser",
            hashed_password=hashed_password,
            full_name="Test User",
            role="admin"
        )

        db.add(test_user)
        db.commit()
        db.refresh(test_user)

        print("[OK] Test user created successfully!")
        print(f"  Email: test@example.com")
        print(f"  Password: password123")
        print(f"  Role: admin")
        print(f"  User ID: {test_user.id}")

    except Exception as e:
        print(f"[ERROR] Error creating test user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
