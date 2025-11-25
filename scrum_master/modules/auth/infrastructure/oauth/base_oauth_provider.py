from abc import ABC, abstractmethod

from scrum_master.modules.auth.presentation.api.auth.schemas import \
    OAuthUserInfo


class BaseOAuthProvider(ABC):
    @abstractmethod
    async def get_authorization_url(self, state: str | None = None) -> str:
        pass

    @abstractmethod
    async def exchange_code(self, code: str) -> str:
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        pass


