from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from scrum_master.shared.config import PostgresConfig


def new_session_maker(db_config: PostgresConfig) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        db_config.url,
        pool_size=15,
        max_overflow=15,
    )
    return async_sessionmaker(
        engine, class_=AsyncSession, autoflush=False, expire_on_commit=False
    )
