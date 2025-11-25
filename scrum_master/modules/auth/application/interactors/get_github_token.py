from uuid import UUID

from scrum_master.modules.auth.application.interfaces import \
    IOAuthConnectionRepository
from scrum_master.modules.auth.domain.entities import OAuthProvider


class GetGitHubTokenInteractor:
    def __init__(
        self,
        oauth_connection_repository: IOAuthConnectionRepository,
    ):
        self._oauth_repo = oauth_connection_repository

    async def __call__(self, user_id: UUID) -> str:
        oauth_connection = await self._oauth_repo.get_by_user_and_provider(
            user_id=user_id,
            provider=OAuthProvider.GITHUB,
        )

        if not oauth_connection:
            raise ValueError('GitHub OAuth connection not found for user')

        return str(oauth_connection.access_token)
