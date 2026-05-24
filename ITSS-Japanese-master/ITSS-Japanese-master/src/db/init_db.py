from sqlmodel import Session

from src.core.config import settings
from src.core.security import get_password_hash
from src.db.session import engine
from src.models.models import UserCreate
from src.repositories.user import user_repo


def init_first_superuser() -> None:
    """Ensure the FIRST_SUPERUSER from .env exists and can sign in with password."""
    with Session(engine) as db:
        user = user_repo.get_by_email(db, email=settings.FIRST_SUPERUSER)
        if user:
            user.is_superuser = True
            user.is_active = True
            user.hashed_password = get_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
            db.add(user)
            db.commit()
            return

        user_repo.create(
            db,
            obj_in=UserCreate(
                email=settings.FIRST_SUPERUSER,
                password=settings.FIRST_SUPERUSER_PASSWORD,
                is_superuser=True,
            ),
        )
