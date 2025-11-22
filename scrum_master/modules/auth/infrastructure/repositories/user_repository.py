from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from scrum_master.modules.auth.application.interfaces import IUserRepository
from scrum_master.modules.auth.domain.entities import User


class SQLAlchemyUserRepository(IUserRepository):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalars().first()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._db.execute(
            select(User).where(User.email == email)
        )
        return result.scalars().first()

    async def get_by_username(self, username: str) -> User | None:
        result = await self._db.execute(
            select(User).where(User.username == username)
        )
        return result.scalars().first()

    async def save(self, user: User) -> User:
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)
        return user

    async def update_last_login(self, user_id: UUID) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.last_login_at = datetime.now()
        await self._db.commit()
        await self._db.refresh(user)

        return user

    async def delete(self, user_id: UUID) -> None:
        await self._db.execute(
            delete(User).where(User.id == user_id)
        )
        await self._db.commit()
