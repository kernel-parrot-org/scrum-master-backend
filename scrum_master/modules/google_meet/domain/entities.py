from dataclasses import dataclass
from datetime import datetime
from enum import Enum as PyEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from scrum_master.modules.auth.domain.entities import Base


class MeetingStatus(str, PyEnum):
    PENDING = 'pending'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'
    FAILED = 'failed'


class Meeting(Base):
    __tablename__ = 'meetings'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    meet_url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[MeetingStatus] = mapped_column(
        SqlEnum(MeetingStatus),
        default=MeetingStatus.PENDING,
        nullable=False,
    )

    bot_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    disconnected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=datetime.now(),
        nullable=False,
    )

    def update_status(self, status: MeetingStatus, error_message: str | None = None) -> None:
        self.status = status
        if error_message:
            self.error_message = error_message
        if status == MeetingStatus.CONNECTED:
            self.connected_at = datetime.now()
        elif status in (MeetingStatus.DISCONNECTED, MeetingStatus.FAILED):
            self.disconnected_at = datetime.now()


@dataclass(slots=True)
class MeetingSession:
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
