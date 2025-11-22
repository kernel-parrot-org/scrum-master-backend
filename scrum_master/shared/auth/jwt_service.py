from datetime import UTC, datetime, timedelta

import jwt
from pydantic import SecretStr

from scrum_master.shared.exceptions.auth import UnauthorizedException


class JWTService:
    def __init__(
        self,
        secret_key: SecretStr,
        algorithm: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
    ):
        self._secret_key = secret_key.get_secret_value()
        self._algorithm = algorithm
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(self, user_id: int) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=self._access_token_expire_minutes)
        payload = {'user_id': user_id, 'exp': expire, 'type': 'access'}
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: int) -> str:
        expire = datetime.now(UTC) + timedelta(days=self._refresh_token_expire_days)
        payload = {'user_id': user_id, 'exp': expire, 'type': 'refresh'}
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> dict[str, int | str]:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            return payload
        except jwt.ExpiredSignatureError as e:
            raise UnauthorizedException('Token expired') from e
        except jwt.InvalidTokenError as e:
            raise UnauthorizedException('Invalid token') from e

    def verify_access_token(self, token: str) -> int:
        payload = self.decode_token(token)
        if payload.get('type') != 'access':
            raise UnauthorizedException('Invalid token type')
        return payload['user_id']

    def verify_refresh_token(self, token: str) -> int:
        payload = self.decode_token(token)
        if payload.get('type') != 'refresh':
            raise UnauthorizedException('Invalid token type')
        return payload['user_id']
