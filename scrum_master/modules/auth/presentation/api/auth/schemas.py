from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from scrum_master.modules.auth.domain.entities import UserRole


class UserBase(BaseModel):
    email: str
    username: str | None = None

class UserResponse(UserBase):
    id: UUID
    role: UserRole
    avatar_url: str | None = None
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True
    )

class OAuthUserInfo(BaseModel):
    oauth_id: str
    email: str
    username: str | None
    avatar_url: str | None = None


class GitHubTokenResponse(BaseModel):
    github_token: str
