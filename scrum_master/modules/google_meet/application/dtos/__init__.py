from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from scrum_master.modules.google_meet.domain.entities import MeetingStatus


@dataclass(slots=True)
class ConnectToMeetingRequest:
    meet_url: str
    bot_name: str | None = None
    min_record_time: int | None = None
    max_waiting_time: int | None = None
    presigned_url_combined: str | None = None
    presigned_url_audio: str | None = None


@dataclass(slots=True)
class MeetingResponse:
    meet_url: str
    status: str
    bot_name: str
    message: str


@dataclass(slots=True)
class DisconnectFromMeetingRequest:
    meeting_id: UUID
    user_id: UUID
