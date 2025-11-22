from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pydantic import SecretStr

from scrum_master.modules.auth.domain.entities import TokenPair, User


class AccessTokenPayload:
    def __init__(self, sub: str, session_id: str, role: str, exp: int):
        self.sub = sub
        self.session_id = session_id
        self.role = role
        self.exp = exp


class RefreshTokenPayload:
    def __init__(self, sub: str, session_id: str, exp: int):
        self.sub = sub
        self.session_id = session_id
        self.exp = exp


class JWTService:
    def __init__(
        self,
        secret_key: SecretStr,
        algorithm: str = 'HS256',
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 30,
    ):
        self.secret_key = secret_key.get_secret_value()
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(self, user: User, session_id: UUID) -> str:
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            'sub': str(user.id),
            'session_id': str(session_id),
            'role': user.role,
            'exp': int(expire.timestamp()),
        }

        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

    def create_refresh_token(self, user_id: UUID, session_id: UUID) -> str:
        now = datetime.now(UTC)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            'sub': str(user_id),
            'session_id': str(session_id),
            'exp': int(expire.timestamp()),
        }

        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

    def create_token_pair(self, user: User, session_id: UUID) -> TokenPair:
        access_token = self.create_access_token(user, session_id)
        refresh_token = self.create_refresh_token(user.id, session_id)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60,
        )

    def verify_access_token(self, token: str) -> AccessTokenPayload:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return AccessTokenPayload(
                sub=payload['sub'],
                session_id=payload['session_id'],
                role=payload['role'],
                exp=payload['exp'],
            )
        except jwt.InvalidTokenError as e:
            raise ValueError(f'Invalid access token: {e!s}')

    def verify_refresh_token(self, token: str) -> RefreshTokenPayload:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return RefreshTokenPayload(
                sub=payload['sub'],
                session_id=payload['session_id'],
                exp=payload['exp'],
            )
        except jwt.InvalidTokenError as e:
            raise ValueError(f'Invalid refresh token: {e!s}')
