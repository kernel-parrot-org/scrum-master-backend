from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from scrum_master.modules.auth.application.dtos import LoginResultDTO, OAuthCallbackDTO
from scrum_master.modules.auth.application.interfaces import (
    IOAuthConnectionRepository,
    ISessionRepository,
    IUserRepository,
)
from scrum_master.modules.auth.domain.entities import (
    OAuthConnection,
    OAuthProvider,
    SessionData,
    User,
    UserRole,
)
from scrum_master.modules.auth.infrastructure.oauth.github_oauth_provider import GithubOauthProvider
from scrum_master.modules.auth.infrastructure.security.jwt_service import JWTService


class GitHubOAuthLoginInteractor:
    def __init__(
        self,
        user_repository: IUserRepository,
        session_repository: ISessionRepository,
        oauth_connection_repository: IOAuthConnectionRepository,
        jwt_service: JWTService,
        github_provider: GithubOauthProvider,
    ):
        self._user_repo = user_repository
        self._session_repo = session_repository
        self._oauth_repo = oauth_connection_repository
        self._jwt = jwt_service
        self._github = github_provider

    async def __call__(self, dto: OAuthCallbackDTO) -> LoginResultDTO:
        github_access_token = await self._github.exchange_code(dto.code)
        oauth_user_info = await self._github.get_user_info(github_access_token)
        user = await self._user_repo.get_by_email(oauth_user_info.email)

        now = datetime.now(UTC)

        if not user:
            user = User(
                id=uuid4(),
                email=oauth_user_info.email,
                username=oauth_user_info.username,
                avatar_url=oauth_user_info.avatar_url,
                role=UserRole.USER,
                created_at=now,
                updated_at=now,
                last_login_at=None,
            )
            user = await self._user_repo.save(user)
        else:
            user = await self._user_repo.update_last_login(user_id=user.id)

        oauth_connection = OAuthConnection(
            id=uuid4(),
            user_id=user.id,
            provider=OAuthProvider.GITHUB,
            provider_user_id=oauth_user_info.oauth_id,
            access_token=github_access_token,
            refresh_token=None,
            token_expires_at=None,
            scopes='read:user,user:email,repo',
            created_at=now,
            updated_at=now,
        )
        await self._oauth_repo.upsert(oauth_connection)

        session_expires_at = now + timedelta(days=30)

        session_data = SessionData(
            id=uuid4(),
            user_id=user.id,
            device_info=dto.device_info,
            ip_address=dto.ip_address,
            created_at=now,
            last_activity=now,
            expires_at=session_expires_at,
        )

        session = await self._session_repo.create(session_data)

        token_pair = self._jwt.create_token_pair(user, session.id)

        return LoginResultDTO(
            user_id=UUID(str(user.id)),
            username=str(user.username),
            email=str(user.email),
            avatar_url=str(user.avatar_url) if user.avatar_url else None,
            role=str(user.role),
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in,
        )
