from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from scrum_master.modules.auth.application.interfaces import IOAuthConnectionRepository
from scrum_master.modules.auth.domain.entities import OAuthConnection, OAuthProvider


class SQLAlchemyOAuthConnectionRepository(IOAuthConnectionRepository):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_user_and_provider(
        self,
        user_id: UUID,
        provider: OAuthProvider,
    ) -> OAuthConnection | None:
        result = await self._db.execute(
            select(OAuthConnection).where(
                OAuthConnection.user_id == user_id,
                OAuthConnection.provider == provider,
            )
        )
        return result.scalars().first()

    async def upsert(self, connection: OAuthConnection) -> OAuthConnection:
        stmt = insert(OAuthConnection).values(
            id=connection.id,
            user_id=connection.user_id,
            provider=connection.provider,
            provider_user_id=connection.provider_user_id,
            access_token=connection.access_token,
            refresh_token=connection.refresh_token,
            token_expires_at=connection.token_expires_at,
            scopes=connection.scopes,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )

        stmt = stmt.on_conflict_do_update(
            constraint='uq_user_provider_account',
            set_={
                'access_token': connection.access_token,
                'refresh_token': connection.refresh_token,
                'token_expires_at': connection.token_expires_at,
                'scopes': connection.scopes,
                'updated_at': connection.updated_at,
            },
        )

        await self._db.execute(stmt)
        await self._db.commit()

        result = await self._db.execute(
            select(OAuthConnection).where(
                OAuthConnection.user_id == connection.user_id,
                OAuthConnection.provider == connection.provider,
            )
        )
        return result.scalars().first()

    async def delete(self, connection_id: UUID) -> None:
        await self._db.execute(
            delete(OAuthConnection).where(OAuthConnection.id == connection_id)
        )
        await self._db.commit()

    async def delete_by_user_and_provider(
        self,
        user_id: UUID,
        provider: OAuthProvider,
    ) -> None:
        await self._db.execute(
            delete(OAuthConnection).where(
                OAuthConnection.user_id == user_id,
                OAuthConnection.provider == provider,
            )
        )
        await self._db.commit()

    async def get_all_by_user(self, user_id: UUID) -> list[OAuthConnection]:
        result = await self._db.execute(
            select(OAuthConnection).where(OAuthConnection.user_id == user_id)
        )
        return list(result.scalars().all())
