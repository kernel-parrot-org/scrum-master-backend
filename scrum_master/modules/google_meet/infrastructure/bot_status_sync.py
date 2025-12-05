"""Background task for syncing bot statuses from external service."""
import asyncio
import logging
from typing import Optional

import httpx

from scrum_master.modules.google_meet.infrastructure.bot_status_storage import (
    BotStatus,
    BotStatusStorage,
)

logger = logging.getLogger(__name__)


class BotStatusSyncTask:
    """Background task to sync bot statuses from external bot service."""

    def __init__(self, storage: BotStatusStorage, sync_interval: int = 3):
        """
        Initialize sync task.

        Args:
            storage: Bot status storage instance
            sync_interval: Interval in seconds between syncs (default: 3)
        """
        self.storage = storage
        self.sync_interval = sync_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the background sync task."""
        if self._task is None or self._task.done():
            self._running = True
            self._task = asyncio.create_task(self._sync_loop())
            logger.info('Bot status sync task started')

    async def stop(self):
        """Stop the background sync task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info('Bot status sync task stopped')

    async def _sync_loop(self):
        """Main sync loop."""
        while self._running:
            try:
                await asyncio.sleep(self.sync_interval)
                await self._sync_statuses()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f'Error in sync loop: {e}', exc_info=True)

    async def _sync_statuses(self):
        """Sync statuses from external service for active bots."""
        # Получаем все боты из storage
        async with self.storage._lock:
            bot_ids = list(self.storage._storage.keys())

        if not bot_ids:
            return

        # Обновляем статусы для ботов, которые еще не в финальном состоянии
        async with httpx.AsyncClient(timeout=10.0) as client:
            for bot_id in bot_ids:
                try:
                    bot_info = await self.storage.get(bot_id)
                    if not bot_info:
                        continue

                    # Пропускаем боты в финальных состояниях
                    if bot_info.status in [BotStatus.DONE, BotStatus.ERROR]:
                        continue

                    # Получаем статус из внешнего сервиса
                    # только для первых трех статусов
                    if bot_info.status in [
                        BotStatus.INITIALIZED,
                        BotStatus.CONNECTING,
                        BotStatus.CONNECTED,
                    ]:
                        response = await client.get(
                            f'http://host.docker.internal:8001/api/v1/bots/{bot_id}'
                        )
                        response.raise_for_status()
                        external_data = response.json()

                        # Маппим внешний статус на наш
                        external_status = external_data.get('status', '')
                        new_status = None

                        if external_status == 'initialized':
                            new_status = BotStatus.INITIALIZED
                        elif external_status == 'connecting':
                            new_status = BotStatus.CONNECTING
                        elif external_status == 'connected':
                            new_status = BotStatus.CONNECTED

                        # Обновляем статус если он изменился
                        if new_status and new_status != bot_info.status:
                            await self.storage.update_status(bot_id, new_status)
                            logger.info(
                                f'Synced bot {bot_id} status: '
                                f'{bot_info.status.value} -> {new_status.value}'
                            )

                except httpx.HTTPError as e:
                    logger.warning(f'Failed to sync status for bot {bot_id}: {e}')
                except Exception as e:
                    logger.error(
                        f'Unexpected error syncing bot {bot_id}: {e}',
                        exc_info=True
                    )


# Global instance
_sync_task: Optional[BotStatusSyncTask] = None


def get_bot_status_sync_task(storage: BotStatusStorage) -> BotStatusSyncTask:
    """Get global bot status sync task instance."""
    global _sync_task
    if _sync_task is None:
        _sync_task = BotStatusSyncTask(storage)
    return _sync_task
