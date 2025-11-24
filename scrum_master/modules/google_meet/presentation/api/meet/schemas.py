from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from scrum_master.modules.google_meet.domain.entities import MeetingStatus


class ConnectToMeetingRequest(BaseModel):
    meet_url: str = Field(..., description='Google Meet URL', min_length=1)
    bot_name: str | None = Field(None, description='Bot display name in the meeting')


class DisconnectFromMeetingRequest(BaseModel):
    meeting_id: UUID = Field(..., description='Meeting ID to disconnect from')


class MeetingResponse(BaseModel):
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

    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    meetings: list[MeetingResponse]
    total: int
