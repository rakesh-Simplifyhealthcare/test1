"""Dev/test convenience only. Real environments should migrate with Alembic
(see the `alembic/` directory and the README), never create_all()."""

from app.db.base import Base
from app.db.session import engine


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
