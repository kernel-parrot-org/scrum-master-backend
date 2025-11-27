from dataclasses import dataclass
from datetime import datetime
from enum import Enum as PyEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserRole(str, PyEnum):
    USER = 'user'
    ADMIN = 'admin'
    MODERATOR = 'moderator'


class OAuthProvider(str, PyEnum):
    GITHUB = 'github'
    GOOGLE = 'google'


class User(Base):
    __tablename__ = 'users'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), default=UserRole.USER, nullable=False)

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
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def update_last_login(self) -> None:
        self.last_login_at = datetime.now()


class OAuthConnection(Base):
    __tablename__ = 'oauth_connections'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    provider: Mapped[OAuthProvider] = mapped_column(
        SqlEnum(OAuthProvider),
        nullable=False,
    )
    provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    access_token: Mapped[str] = mapped_column(String(512), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    scopes: Mapped[str | None] = mapped_column(String(512), nullable=True)

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

    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'provider',
            'provider_user_id',
            name='uq_user_provider_account',
        ),
        Index('ix_oauth_user_provider', 'user_id', 'provider'),
    )


@dataclass(slots=True)
class SessionData:
    id: UUID
    user_id: UUID
    device_info: str | None
    ip_address: str | None
    created_at: datetime
    last_activity: datetime
    expires_at: datetime


@dataclass(slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = 'bearer'

    def __post_init__(self):
        if not self.access_token or not self.refresh_token:
            raise ValueError('Tokens cannot be empty')
        if self.expires_in <= 0:
            raise ValueError('expires_in must be positive')


class ScheduleType(str, PyEnum):
    ONCE = 'once'           # One-time scheduled meeting
    DAILY = 'daily'         # Every day at specific time
    WEEKLY = 'weekly'       # Specific days of week
    CALENDAR = 'calendar'   # Synced from Google Calendar


class ScheduledMeeting(Base):
    """Scheduled meetings that bot will auto-join"""
    __tablename__ = 'scheduled_meetings'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    
    # Meeting details
    meet_url: Mapped[str] = mapped_column(String(512), nullable=False)
    bot_name: Mapped[str] = mapped_column(String(255), default='Scrum Bot')
    
    # Schedule settings
    schedule_type: Mapped[ScheduleType] = mapped_column(
        SqlEnum(ScheduleType, values_callable=lambda x: [e.value for e in x]),
        default=ScheduleType.ONCE,
        nullable=False,
    )
    
    # For ONCE: specific datetime, For DAILY/WEEKLY: time of day
    scheduled_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # For WEEKLY: comma-separated days (0=Mon, 6=Sun), e.g. "0,2,4" for Mon,Wed,Fri
    days_of_week: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # For CALENDAR: Google Calendar event ID
    calendar_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_trigger_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
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

    __table_args__ = (
        Index('ix_scheduled_meetings_next_trigger', 'next_trigger_at', 'is_active'),
    )
