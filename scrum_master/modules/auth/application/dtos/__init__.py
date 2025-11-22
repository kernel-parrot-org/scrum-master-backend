from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from scrum_master.modules.auth.domain import UserRole


@dataclass(slots=True, frozen=True)
class OAuthCallbackDTO:
    code: str
    device_info: str | None
    ip_address: str | None


@dataclass(slots=True, frozen=True)
class LoginResultDTO:
    user_id: UUID
    username: str
    email: str
    avatar_url: str | None
    role: str
    access_token: str
    refresh_token: str
    expires_in: int


@dataclass(slots=True, frozen=True)
class RefreshTokenDTO:
    refresh_token: str


@dataclass(slots=True, frozen=True)
class LogoutDTO:
    session_id: str

@dataclass(slots=True, frozen=True)
class UserResponseOutputDTO:
    id: UUID
    email: str
    username: str
    role: UserRole
    created_at: datetime
    avatar_url: str | None = None
    last_login_at: datetime | None = None
    updated_at: datetime | None = None

