from uuid import UUID

from scrum_master.modules.google_meet.application.dtos import MeetingResponse
from scrum_master.modules.google_meet.application.interfaces import \
    IMeetingRepository


class GetMeetingsInteractor:
    def __init__(self, meeting_repository: IMeetingRepository):
        self.meeting_repository = meeting_repository

    async def execute(self, user_id: UUID) -> list[MeetingResponse]:
        meetings = await self.meeting_repository.get_by_user_id(user_id)

        return [
            MeetingResponse(
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
            for meeting in meetings
        ]
