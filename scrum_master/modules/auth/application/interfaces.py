from abc import ABC, abstractmethod
from uuid import UUID

from scrum_master.modules.auth.domain.entities import (OAuthConnection,
                                                       OAuthProvider,
                                                       SessionData, User)


class IUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    async def update_last_login(self, user_id: UUID) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        raise NotImplementedError


class ISessionRepository(ABC):
    @abstractmethod
    async def create(self, session: SessionData) -> SessionData:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> SessionData | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> list[SessionData]:
        raise NotImplementedError

    @abstractmethod
    async def update(self, session: SessionData) -> SessionData:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, session_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_user_id(self, user_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_expired(self) -> int:
        raise NotImplementedError


class IOAuthConnectionRepository(ABC):
    @abstractmethod
    async def get_by_user_and_provider(
        self,
        user_id: UUID,
        provider: OAuthProvider,
    ) -> OAuthConnection | None:
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, connection: OAuthConnection) -> OAuthConnection:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, connection_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_user_and_provider(
        self,
        user_id: UUID,
        provider: OAuthProvider,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_all_by_user(self, user_id: UUID) -> list[OAuthConnection]:
        raise NotImplementedError
