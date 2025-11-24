"""
Create a test user for the database
"""
from database import SessionLocal
from auth import hash_password
import models

def create_test_user():
    db = SessionLocal()

    try:
        # Check if user already exists
        existing_user = db.query(models.User).filter(
            models.User.username == "testuser"
        ).first()

        if existing_user:
            print("Test user already exists!")
            print(f"  Username: {existing_user.username}")
            print(f"  Email: {existing_user.email}")
            return

        # Create test user with shorter password
        password_hash = hash_password("test123")

        test_user = models.User(
            username="testuser",
            email="test@example.com",
            password_hash=password_hash,
            is_active=True
        )

        db.add(test_user)
        db.commit()
        db.refresh(test_user)

        print("[OK] Test user created successfully!")
        print(f"  Username: testuser")
        print(f"  Password: test123")
        print(f"  Email: test@example.com")
        print(f"  User ID: {test_user.id}")

    except Exception as e:
        print(f"[ERROR] Failed to create test user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
