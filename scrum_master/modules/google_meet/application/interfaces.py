from abc import ABC, abstractmethod
from uuid import UUID

from scrum_master.modules.google_meet.domain.entities import Meeting, MeetingStatus


class IMeetingRepository(ABC):
    @abstractmethod
    async def create(
        self,
        user_id: UUID,
        meet_url: str,
        bot_name: str | None = None,
    ) -> Meeting:
        pass

    @abstractmethod
    async def get_by_id(self, meeting_id: UUID) -> Meeting | None:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> list[Meeting]:
        pass

    @abstractmethod
    async def update_status(
        self,
        meeting_id: UUID,
        status: MeetingStatus,
        error_message: str | None = None,
    ) -> Meeting | None:
        pass

    @abstractmethod
    async def delete(self, meeting_id: UUID) -> bool:
        pass


class IGoogleMeetAdapter(ABC):
    @abstractmethod
    def initialize_driver(self) -> None:
        pass

    @abstractmethod
    def connect_to_meeting(
        self,
        meet_url: str,
        bot_name: str | None = None,
        min_record_time: int | None = None,
        max_waiting_time: int | None = None,
        presigned_url_combined: str | None = None,
        presigned_url_audio: str | None = None,
    ) -> None:
        pass

    @abstractmethod
    def disconnect_from_meeting(self) -> None:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass
