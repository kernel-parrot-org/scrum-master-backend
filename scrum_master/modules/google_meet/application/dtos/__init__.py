from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from scrum_master.modules.google_meet.domain.entities import MeetingStatus


@dataclass(slots=True)
class ConnectToMeetingRequest:
    user_id: UUID
    meet_url: str
    bot_name: str | None = None


@dataclass(slots=True)
class MeetingResponse:
    id: UUID
    user_id: UUID
    meet_url: str
    status: MeetingStatus
    bot_name: str | None
    error_message: str | None
    connected_at: datetime | None
    disconnected_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class DisconnectFromMeetingRequest:
    meeting_id: UUID
    user_id: UUID
