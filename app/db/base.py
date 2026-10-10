from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. Import all models here so Alembic autogenerate sees them."""


from app.models.user import User  # noqa: E402,F401
