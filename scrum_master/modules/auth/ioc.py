from dishka import Provider, Scope, provide
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from scrum_master.modules.auth.application.interactors.get_github_token import \
    GetGitHubTokenInteractor
from scrum_master.modules.auth.application.interactors.get_user import \
    GetUserInteractor
from scrum_master.modules.auth.application.interactors.github_oauth_login import \
    GitHubOAuthLoginInteractor
from scrum_master.modules.auth.application.interactors.google_oauth_login import \
    GoogleOAuthLoginInteractor
from scrum_master.modules.auth.application.interactors.logout import \
    LogoutInteractor
from scrum_master.modules.auth.application.interactors.refresh_token import \
    RefreshTokenInteractor
from scrum_master.modules.auth.application.interfaces import (
    IOAuthConnectionRepository, ISessionRepository, IUserRepository)
from scrum_master.modules.auth.config import AuthModuleConfig
from scrum_master.modules.auth.infrastructure.oauth.github_oauth_provider import \
    GithubOauthProvider
from scrum_master.modules.auth.infrastructure.oauth.google_oauth_provider import \
    GoogleOAuthProvider
from scrum_master.modules.auth.infrastructure.redis.session_repository import \
    RedisSessionRepository
from scrum_master.modules.auth.infrastructure.repositories.oauth_connection_repository import \
    SQLAlchemyOAuthConnectionRepository
from scrum_master.modules.auth.infrastructure.repositories.user_repository import \
    SQLAlchemyUserRepository
from scrum_master.modules.auth.infrastructure.security.jwt_service import \
    JWTService as AuthJWTService
from scrum_master.shared.config import Settings


class AuthModuleProvider(Provider):
    @provide(scope=Scope.APP)
    def get_auth_config(self) -> AuthModuleConfig:
        return AuthModuleConfig()

    @provide(scope=Scope.REQUEST, provides=IUserRepository)
    def get_user_repository(self, session: AsyncSession) -> SQLAlchemyUserRepository:
        return SQLAlchemyUserRepository(session)

    @provide(scope=Scope.REQUEST, provides=ISessionRepository)
    def get_session_repository(self, redis: Redis) -> RedisSessionRepository:
        return RedisSessionRepository(redis)

    @provide(scope=Scope.REQUEST, provides=IOAuthConnectionRepository)
    def get_oauth_repository(self, session: AsyncSession) -> SQLAlchemyOAuthConnectionRepository:
        return SQLAlchemyOAuthConnectionRepository(session)

    @provide(scope=Scope.APP)
    def get_github_oauth_provider(self, config: AuthModuleConfig) -> GithubOauthProvider:
        return GithubOauthProvider(
            client_id=config.github.client_id,
            client_secret=config.github.client_secret,
            redirect_uri=config.github.redirect_uri,
        )

    @provide(scope=Scope.APP)
    def get_google_oauth_provider(self, config: AuthModuleConfig) -> GoogleOAuthProvider:
        return GoogleOAuthProvider(
            client_id=config.google.client_id,
            client_secret=config.google.client_secret,
            redirect_uri=config.google.redirect_uri,
        )

    @provide(scope=Scope.APP)
    def get_auth_jwt_service(self, settings: Settings) -> AuthJWTService:
        return AuthJWTService(
            secret_key=settings.jwt.secret_key,
            algorithm=settings.jwt.algorithm,
            access_token_expire_minutes=settings.jwt.access_token_expire_minutes,
            refresh_token_expire_days=settings.jwt.refresh_token_expire_days,
        )

    @provide(scope=Scope.REQUEST)
    def get_github_oauth_login_interactor(
        self,
        user_repo: IUserRepository,
        session_repo: ISessionRepository,
        oauth_repo: IOAuthConnectionRepository,
        jwt_service: AuthJWTService,
        github_provider: GithubOauthProvider,
    ) -> GitHubOAuthLoginInteractor:
        return GitHubOAuthLoginInteractor(
            user_repository=user_repo,
            session_repository=session_repo,
            oauth_connection_repository=oauth_repo,
            jwt_service=jwt_service,
            github_provider=github_provider,
        )

    @provide(scope=Scope.REQUEST)
    def get_google_oauth_login_interactor(
        self,
        user_repo: IUserRepository,
        session_repo: ISessionRepository,
        oauth_repo: IOAuthConnectionRepository,
        jwt_service: AuthJWTService,
        google_provider: GoogleOAuthProvider,
    ) -> GoogleOAuthLoginInteractor:
        return GoogleOAuthLoginInteractor(
            user_repository=user_repo,
            session_repository=session_repo,
            oauth_connection_repository=oauth_repo,
            jwt_service=jwt_service,
            google_provider=google_provider,
        )

    @provide(scope=Scope.REQUEST)
    def get_github_token_interactor(
        self,
        oauth_repo: IOAuthConnectionRepository,
    ) -> GetGitHubTokenInteractor:
        return GetGitHubTokenInteractor(oauth_repo)

    @provide(scope=Scope.REQUEST)
    def get_logout_interactor(
        self,
        session_repo: ISessionRepository,
    ) -> LogoutInteractor:
        return LogoutInteractor(session_repo)

    @provide(scope=Scope.REQUEST)
    def get_user_interactor(
        self,
        jwt_service: AuthJWTService,
        user_repo: IUserRepository,
        session_repo: ISessionRepository,
    ) -> GetUserInteractor:
        return GetUserInteractor(
            jwt_service=jwt_service,
            user_repository=user_repo,
            session_repository=session_repo,
        )

    @provide(scope=Scope.REQUEST)
    def get_refresh_token_interactor(
        self,
        user_repo: IUserRepository,
        session_repo: ISessionRepository,
        jwt_service: AuthJWTService,
    ) -> RefreshTokenInteractor:
        return RefreshTokenInteractor(
            user_repository=user_repo,
            session_repository=session_repo,
            jwt_service=jwt_service,
        )
