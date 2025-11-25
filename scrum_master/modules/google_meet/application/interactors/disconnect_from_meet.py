import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from scrum_master.modules.google_meet.application.dtos import (
    DisconnectFromMeetingRequest, MeetingResponse)
from scrum_master.modules.google_meet.application.interfaces import (
    IGoogleMeetAdapter, IMeetingRepository)
from scrum_master.modules.google_meet.domain.entities import MeetingStatus

logger = logging.getLogger(__name__)


class DisconnectFromMeetInteractor:
    def __init__(
        self,
        meeting_repository: IMeetingRepository,
        google_meet_adapter: IGoogleMeetAdapter,
    ):
        self.meeting_repository = meeting_repository
        self.google_meet_adapter = google_meet_adapter
        self.executor = ThreadPoolExecutor(max_workers=1)

    def _disconnect_sync(self) -> None:
        self.google_meet_adapter.disconnect_from_meeting()
        self.google_meet_adapter.cleanup()

    async def execute(self, request: DisconnectFromMeetingRequest) -> MeetingResponse:
        meeting = await self.meeting_repository.get_by_id(request.meeting_id)

        if not meeting:
            raise ValueError(f'Meeting {request.meeting_id} not found')

        if meeting.user_id != request.user_id:
            raise ValueError('User does not have permission to disconnect from this meeting')

        if meeting.status != MeetingStatus.CONNECTED:
            raise ValueError(f'Meeting is not connected (status: {meeting.status})')

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self._disconnect_sync)

            meeting = await self.meeting_repository.update_status(
                meeting_id=meeting.id,
                status=MeetingStatus.DISCONNECTED,
            )

            logger.info(f'Successfully disconnected from meeting {meeting.id}')

        except Exception as e:
            logger.error(f'Error disconnecting from meeting: {e}')
            meeting = await self.meeting_repository.update_status(
                meeting_id=meeting.id,
                status=MeetingStatus.FAILED,
                error_message=f'Error disconnecting: {str(e)}',
            )

        return MeetingResponse(
            id=meeting.id,
            user_id=meeting.user_id,
            meet_url=meeting.meet_url,
            status=meeting.status,
            bot_name=meeting.bot_name,
            error_message=meeting.error_message,
            connected_at=meeting.connected_at,
            disconnected_at=meeting.disconnected_at,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
        )
