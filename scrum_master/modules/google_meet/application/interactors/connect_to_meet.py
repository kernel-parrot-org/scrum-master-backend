import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from scrum_master.modules.google_meet.application.dtos import (
    ConnectToMeetingRequest,
    MeetingResponse,
)
from scrum_master.modules.google_meet.application.interfaces import (
    IGoogleMeetAdapter,
    IMeetingRepository,
)
from scrum_master.modules.google_meet.domain.entities import MeetingStatus
from scrum_master.modules.google_meet.infrastructure.selenium.ui_methods import (
    GoogleMeetUIException,
)

logger = logging.getLogger(__name__)


class ConnectToMeetInteractor:
    def __init__(
        self,
        meeting_repository: IMeetingRepository,
        google_meet_adapter: IGoogleMeetAdapter,
    ):
        self.meeting_repository = meeting_repository
        self.google_meet_adapter = google_meet_adapter
        self.executor = ThreadPoolExecutor(max_workers=1)

    def _connect_sync(self, meet_url: str, bot_name: str | None) -> None:
        self.google_meet_adapter.initialize_driver()
        self.google_meet_adapter.connect_to_meeting(meet_url, bot_name)

    async def execute(self, request: ConnectToMeetingRequest) -> MeetingResponse:
        meeting = await self.meeting_repository.create(
            user_id=request.user_id,
            meet_url=request.meet_url,
            bot_name=request.bot_name,
        )

        try:
            await self.meeting_repository.update_status(
                meeting_id=meeting.id,
                status=MeetingStatus.CONNECTING,
            )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._connect_sync,
                request.meet_url,
                request.bot_name,
            )

            meeting = await self.meeting_repository.update_status(
                meeting_id=meeting.id,
                status=MeetingStatus.CONNECTED,
            )

            logger.info(f'Successfully connected to meeting {meeting.id}')

        except GoogleMeetUIException as e:
            logger.error(f'Failed to connect to meeting: {e}')
            meeting = await self.meeting_repository.update_status(
                meeting_id=meeting.id,
                status=MeetingStatus.FAILED,
                error_message=str(e),
            )
            self.google_meet_adapter.cleanup()

        except Exception as e:
            logger.error(f'Unexpected error: {e}')
            meeting = await self.meeting_repository.update_status(
                meeting_id=meeting.id,
                status=MeetingStatus.FAILED,
                error_message=f'Unexpected error: {str(e)}',
            )
            self.google_meet_adapter.cleanup()

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
