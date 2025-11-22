from uuid import UUID

from scrum_master.modules.auth.application.dtos import LoginResultDTO, RefreshTokenDTO
from scrum_master.modules.auth.application.interfaces import ISessionRepository, IUserRepository
from scrum_master.modules.auth.infrastructure.security.jwt_service import JWTService


class RefreshTokenInteractor:
    def __init__(
        self,
        user_repository: IUserRepository,
        session_repository: ISessionRepository,
        jwt_service: JWTService,
    ):
        self._user_repo = user_repository
        self._session_repo = session_repository
        self._jwt = jwt_service

    async def __call__(self, dto: RefreshTokenDTO) -> LoginResultDTO:
        try:
            payload = self._jwt.verify_refresh_token(dto.refresh_token)
        except ValueError as e:
            raise ValueError('Invalid or expired refresh token') from e

        session = await self._session_repo.get_by_id(UUID(payload.session_id))
        if not session:
            raise ValueError('Session not found or expired')

        if session.user_id != UUID(payload.sub):
            raise ValueError('Session does not belong to user')

        user = await self._user_repo.get_by_id(UUID(payload.sub))
        if not user:
            raise ValueError('User not found')

        await self._session_repo.update(session)

        token_pair = self._jwt.create_token_pair(user, payload.session_id)

        return LoginResultDTO(
            user_id=user.id,
            username=user.username,
            email=user.email,
            avatar_url=user.avatar_url,
            role=user.role,
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in,
        )
