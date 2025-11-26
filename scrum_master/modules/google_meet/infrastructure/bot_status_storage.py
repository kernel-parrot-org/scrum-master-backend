"""In-memory storage for bot statuses with thread-safe operations."""
import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class BotStatus(str, Enum):
    """Bot processing statuses."""
    STARTING = 'starting'
    RUNNING = 'running'
    TRANSCRIBING = 'transcribing'
    ANALYZING_MEETING = 'analyzing_meeting'
    CREATING_TASKS = 'creating_tasks'
    DONE = 'done'
    ERROR = 'error'


class BotStatusInfo:
    """Information about bot status."""

    def __init__(self, bot_id: str, status: BotStatus, user_id: str):
        self.bot_id = bot_id
        self.status = status
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.error_message: Optional[str] = None
        self.session_id: Optional[str] = None
        self.result_data: Optional[dict] = None

    def update_status(self, status: BotStatus, error_message: Optional[str] = None):
        """Update status and timestamp."""
        self.status = status
        self.updated_at = datetime.utcnow()
        if error_message:
            self.error_message = error_message

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            'bot_id': self.bot_id,
            'status': self.status.value,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'error_message': self.error_message,
            'session_id': self.session_id,
            'result_data': self.result_data,
        }


class BotStatusStorage:
    """Thread-safe in-memory storage for bot statuses."""

    def __init__(self):
        self._storage: dict[str, BotStatusInfo] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self):
        """Start background task to cleanup old entries."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_entries())
            logger.info('Bot status cleanup task started')

    async def stop_cleanup_task(self):
        """Stop cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info('Bot status cleanup task stopped')

    async def _cleanup_old_entries(self):
        """Remove entries older than 24 hours."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                cutoff_time = datetime.utcnow() - timedelta(hours=24)

                async with self._lock:
                    old_keys = [
                        bot_id for bot_id, info in self._storage.items()
                        if info.updated_at < cutoff_time
                    ]
                    for bot_id in old_keys:
                        del self._storage[bot_id]
                        logger.info(f'Cleaned up old bot status: {bot_id}')

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f'Error in cleanup task: {e}', exc_info=True)

    async def create(self, bot_id: str, user_id: str, status: BotStatus = BotStatus.STARTING) -> BotStatusInfo:
        """Create new bot status entry."""
        async with self._lock:
            info = BotStatusInfo(bot_id, status, user_id)
            self._storage[bot_id] = info
            logger.info(f'Created bot status: {bot_id} with status {status.value}')
            return info

    async def get(self, bot_id: str) -> Optional[BotStatusInfo]:
        """Get bot status by ID."""
        async with self._lock:
            return self._storage.get(bot_id)

    async def update_status(
        self,
        bot_id: str,
        status: BotStatus,
        error_message: Optional[str] = None,
        session_id: Optional[str] = None,
        result_data: Optional[dict] = None,
    ) -> Optional[BotStatusInfo]:
        """Update bot status."""
        async with self._lock:
            info = self._storage.get(bot_id)
            if info:
                info.update_status(status, error_message)
                if session_id:
                    info.session_id = session_id
                if result_data:
                    info.result_data = result_data
                logger.info(f'Updated bot {bot_id} status to {status.value}')
                return info
            return None

    async def delete(self, bot_id: str) -> bool:
        """Delete bot status."""
        async with self._lock:
            if bot_id in self._storage:
                del self._storage[bot_id]
                logger.info(f'Deleted bot status: {bot_id}')
                return True
            return False


# Global instance
_bot_status_storage: Optional[BotStatusStorage] = None


def get_bot_status_storage() -> BotStatusStorage:
    """Get global bot status storage instance."""
    global _bot_status_storage
    if _bot_status_storage is None:
        _bot_status_storage = BotStatusStorage()
    return _bot_status_storage