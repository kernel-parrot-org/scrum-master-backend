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

    def _connect_sync(
        self,
        meet_url: str,
        bot_name: str | None,
        min_record_time: int | None = None,
        max_waiting_time: int | None = None,
        presigned_url_combined: str | None = None,
        presigned_url_audio: str | None = None,
    ) -> None:
        self.google_meet_adapter.initialize_driver()
        self.google_meet_adapter.connect_to_meeting(
            meet_url=meet_url,
            bot_name=bot_name,
            min_record_time=min_record_time,
            max_waiting_time=max_waiting_time,
            presigned_url_combined=presigned_url_combined,
            presigned_url_audio=presigned_url_audio,
        )

    async def execute(self, request: ConnectToMeetingRequest) -> MeetingResponse:
        try:
            logger.info(f'Starting bot for meeting: {request.meet_url}')

            # Start bot in background thread (non-blocking)
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                self.executor,
                self._connect_sync,
                request.meet_url,
                request.bot_name,
                request.min_record_time,
                request.max_waiting_time,
                request.presigned_url_combined,
                request.presigned_url_audio,
            )

            # Return success immediately (bot runs in background)
            import uuid
            from datetime import datetime, timezone

            meeting_id = str(uuid.uuid4())
            logger.info(f'Bot started successfully for meeting: {meeting_id}')

            return MeetingResponse(
                id=meeting_id,
                user_id=request.user_id,
                meet_url=request.meet_url,
                status=MeetingStatus.CONNECTED,
                bot_name=request.bot_name or "Google Bot",
                error_message=None,
                connected_at=datetime.now(timezone.utc),
                disconnected_at=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f'Failed to start bot: {e}', exc_info=True)
            raise
