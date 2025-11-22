import json
from datetime import UTC, datetime
from uuid import UUID

from redis.asyncio import Redis

from scrum_master.modules.auth.application.interfaces import ISessionRepository
from scrum_master.modules.auth.domain.entities import SessionData


class RedisSessionRepository(ISessionRepository):
    def __init__(self, redis_client: Redis):
        self._redis = redis_client
        self._prefix = 'session'
        self._user_sessions_prefix = 'user_sessions'

    def _get_session_key(self, session_id: UUID) -> str:
        return f'{self._prefix}:{session_id!s}'

    def _get_user_sessions_key(self, user_id: UUID) -> str:
        return f'{self._user_sessions_prefix}:{user_id!s}'

    def _serialize_session(self, session: SessionData) -> str:
        return json.dumps({
            'id': str(session.id),
            'user_id': str(session.user_id),
            'device_info': session.device_info,
            'ip_address': session.ip_address,
            'created_at': session.created_at.isoformat(),
            'last_activity': session.last_activity.isoformat(),
            'expires_at': session.expires_at.isoformat(),
        })

    def _deserialize_session(self, data: str) -> SessionData:
        obj = json.loads(data)
        return SessionData(
            id=UUID(obj['id']),
            user_id=UUID(obj['user_id']),
            device_info=obj['device_info'],
            ip_address=obj['ip_address'],
            created_at=datetime.fromisoformat(obj['created_at']),
            last_activity=datetime.fromisoformat(obj['last_activity']),
            expires_at=datetime.fromisoformat(obj['expires_at']),
        )

    async def create(self, session: SessionData) -> SessionData:
        session_key = self._get_session_key(session.id)
        user_sessions_key = self._get_user_sessions_key(session.user_id)

        now = datetime.now(UTC)
        ttl = int((session.expires_at - now).total_seconds())
        if ttl <= 0:
            raise ValueError('Session expiration time must be in the future')

        await self._redis.setex(
            session_key,
            ttl,
            self._serialize_session(session)
        )

        await self._redis.sadd(user_sessions_key, str(session.id))
        await self._redis.expire(user_sessions_key, ttl + 3600)

        return session

    async def get_by_id(self, session_id: UUID) -> SessionData | None:
        data = await self._redis.get(self._get_session_key(session_id))
        if not data:
            return None

        return self._deserialize_session(data)

    async def get_by_user_id(self, user_id: UUID) -> list[SessionData]:
        user_sessions_key = self._get_user_sessions_key(user_id)
        session_ids = await self._redis.smembers(user_sessions_key)

        if not session_ids:
            return []

        sessions = []
        for session_id_str in session_ids:
            try:
                session = await self.get_by_id(UUID(session_id_str))
                if session:
                    sessions.append(session)
                else:
                    await self._redis.srem(user_sessions_key, session_id_str)
            except (ValueError, KeyError):
                await self._redis.srem(user_sessions_key, session_id_str)

        return sessions

    async def update(self, session: SessionData) -> SessionData:
        existing_session = await self.get_by_id(session.id)
        if not existing_session:
            raise ValueError(f'Session {session.id} not found')

        session_key = self._get_session_key(session.id)
        now = datetime.now(UTC)
        ttl = int((session.expires_at - now).total_seconds())

        if ttl <= 0:
            raise ValueError('Session has expired')

        await self._redis.setex(
            session_key,
            ttl,
            self._serialize_session(session)
        )

        return session

    async def delete(self, session_id: UUID) -> None:
        session = await self.get_by_id(session_id)

        await self._redis.delete(self._get_session_key(session_id))

        if session:
            await self._redis.srem(
                self._get_user_sessions_key(session.user_id),
                str(session_id)
            )

    async def delete_by_user_id(self, user_id: UUID) -> None:
        user_sessions_key = self._get_user_sessions_key(user_id)
        session_ids = await self._redis.smembers(user_sessions_key)

        if session_ids:
            session_keys = [self._get_session_key(UUID(sid)) for sid in session_ids]
            await self._redis.delete(*session_keys)

            await self._redis.delete(user_sessions_key)

    async def delete_expired(self) -> int:
        deleted_count = 0

        cursor = 0
        pattern = f'{self._user_sessions_prefix}:*'

        while True:
            cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)

            for user_sessions_key in keys:
                session_ids = await self._redis.smembers(user_sessions_key)

                for session_id_str in session_ids:
                    try:
                        session_id = UUID(session_id_str)
                        if not await self._redis.exists(self._get_session_key(session_id)):
                            await self._redis.srem(user_sessions_key, session_id_str)
                            deleted_count += 1
                    except ValueError:
                        await self._redis.srem(user_sessions_key, session_id_str)
                        deleted_count += 1

            if cursor == 0:
                break

        return deleted_count
