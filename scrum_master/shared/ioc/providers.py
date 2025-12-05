from collections.abc import AsyncIterable

from dishka import Provider, Scope, from_context, provide
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scrum_master.shared.auth.jwt_service import JWTService
from scrum_master.shared.config import Settings
from scrum_master.shared.persistence.sqlalchemy.database import \
    new_session_maker


class SharedInfrastructureProvider(Provider):
    settings = from_context(provides=Settings, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def get_session_maker(self, config: Settings) -> async_sessionmaker[AsyncSession]:
        return new_session_maker(config.postgres)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self, session_maker: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AsyncSession]:
        async with session_maker() as session:
            yield session

    @provide(scope=Scope.APP)
    async def get_redis(self, settings: Settings) -> AsyncIterable[Redis]:
        redis = Redis.from_url(settings.redis.url, decode_responses=True)
        yield redis
        await redis.aclose()

    @provide(scope=Scope.APP)
    def get_jwt_service(self, settings: Settings) -> JWTService:
        return JWTService(
            secret_key=settings.jwt.secret_key,
            algorithm=settings.jwt.algorithm,
            access_token_expire_minutes=settings.jwt.access_token_expire_minutes,
            refresh_token_expire_days=settings.jwt.refresh_token_expire_days,
        )
