from uuid import UUID

from scrum_master.modules.auth.application.dtos import UserResponseOutputDTO
from scrum_master.modules.auth.application.interfaces import ISessionRepository, IUserRepository
from scrum_master.modules.auth.infrastructure.security.jwt_service import JWTService


class GetUserInteractor:
    def __init__(
        self,
        jwt_service: JWTService,
        user_repository: IUserRepository,
        session_repository: ISessionRepository,
    ) -> None:
        self._jwt_service = jwt_service
        self._user_repository = user_repository
        self._session_repository = session_repository

    async def __call__(self, user_access_token: str) -> UserResponseOutputDTO:
        payload = self._jwt_service.verify_access_token(user_access_token)

        session = await self._session_repository.get_by_id(UUID(payload.session_id))
        if not session:
            raise ValueError('Session expired or invalid')

        user = await self._user_repository.get_by_id(UUID(payload.sub))
        if not user:
            raise ValueError('User not found')

        return UserResponseOutputDTO(
            id=user.id,
            email=user.email,
            username=user.username,
            role=user.role,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            updated_at=user.updated_at,
        )
