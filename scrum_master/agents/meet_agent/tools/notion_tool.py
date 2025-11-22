import logging

from core.config import settings
from services.notion_service import NotionService

logger = logging.getLogger(__name__)


async def export_to_notion(meeting_data: dict) -> dict:
    try:
        logger.info('[TOOL] Exporting to Notion...')

        notion_service = NotionService(
            token=settings.notion.token,
            page_id=settings.notion.page_id,
        )

        await notion_service.create_meeting_page(meeting_data)

        logger.info('[TOOL] Meeting page created')

        await notion_service.close()

        logger.info('[TOOL] Notion export completed, tasks created')

        return {
            'status': 'success',
        }

    except Exception as e:
        logger.info(f'[TOOL] Notion export error: {e!s}')
        return {
            'status': 'error',
            'error_message': f'Failed to export to Notion: {e!s}',
            'stage': 'export_to_notion',
        }
