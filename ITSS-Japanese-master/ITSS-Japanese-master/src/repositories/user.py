from fastapi import HTTPException
from typing import Optional
import secrets
from sqlmodel import Session, select
from src.core.security import get_password_hash, verify_password
from src.models.models import User, UserCreate


class UserRepository:
    def register(self, db: Session, *, obj_in: UserCreate) -> User:
        """Creates a new user if the email is not already in use."""
        user = self.get_by_email(db, email=obj_in.email)
        if user:
            raise HTTPException(
                status_code=409,  # 409 Conflict is often more appropriate here
                detail="A user with this email already exists.",
            )
        return self.create(db, obj_in=obj_in)

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Finds and returns a user by their email address."""
        return db.exec(select(User).where(User.email == email)).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """Creates a new user record in the database,
        hashing the provided password for storage."""
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            is_superuser=obj_in.is_superuser,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        """Validates a user's credentials by checking their email and verifying their password."""
        user = self.get_by_email(db, email=email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        elif not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return user

    def get_or_create_oauth_user(
        self, db: Session, *, email: str, full_name: Optional[str]
    ) -> User:
        """Returns an existing user or creates a new one for OAuth-based login."""
        user = self.get_by_email(db, email=email)
        if user:
            if not user.is_active:
                raise HTTPException(status_code=400, detail="Inactive user")
            if full_name and not user.full_name:
                user.full_name = full_name
                db.add(user)
                db.commit()
                db.refresh(user)
            return user

        random_password = secrets.token_urlsafe(32)
        db_obj = User(
            email=email,
            hashed_password=get_password_hash(random_password),
            full_name=full_name,
            is_active=True,
            is_superuser=False,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


user_repo = UserRepository()
