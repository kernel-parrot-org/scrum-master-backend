from uuid import UUID

from scrum_master.modules.auth.application.dtos import LogoutDTO
from scrum_master.modules.auth.application.interfaces import ISessionRepository


class LogoutInteractor:
    def __init__(
        self,
        session_repository: ISessionRepository,
    ):
        self._session_repo = session_repository

    async def __call__(self, dto: LogoutDTO) -> None:
        session = await self._session_repo.get_by_id(UUID(dto.session_id))
        if not session:
            return

        await self._session_repo.delete(UUID(dto.session_id))
