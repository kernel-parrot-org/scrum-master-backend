import logging
from pathlib import Path

from modules.auth.infrastructure.logging import configure_logging
from pydantic import ConfigDict

from scrum_master.utils.pydantic_fix import matching_adk_pydantic

try:
    matching_adk_pydantic()
except Exception as e:
    logging.error(f"Failed to apply matching_adk_pydantic: {e}")

from mcp.shared.context import RequestContext

RequestContext.__pydantic_config__ = ConfigDict(arbitrary_types_allowed=True)

import uvicorn
from dishka.integrations import fastapi as fastapi_integration
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from starlette.middleware.cors import CORSMiddleware

from scrum_master.agents.meet_agent.api.routes import \
    router as meet_agent_router
from scrum_master.ioc import create_container
from scrum_master.modules.auth.presentation.api.auth.router import \
    router as auth_router
from scrum_master.modules.google_meet.infrastructure.bot_status_storage import (
    get_bot_status_storage,
)
from scrum_master.modules.google_meet.infrastructure.bot_status_sync import (
    get_bot_status_sync_task,
)
from scrum_master.modules.google_meet.presentation.api.meet.router import \
    router as meet_router
from scrum_master.modules.jira.presentation.api.jira.router import \
    router as jira_router

BASE_DIR = Path(__file__).resolve().parent

configure_logging()


def create_app() -> FastAPI:
    container = create_container()

    app = get_fast_api_app(
        agents_dir=str(BASE_DIR / 'agents'),
        web=True,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    fastapi_integration.setup_dishka(container, app)
    app.include_router(auth_router)

    app.include_router(meet_router)
    app.include_router(meet_agent_router)
    app.include_router(jira_router)

    # Startup event: запуск фоновых задач
    @app.on_event('startup')
    async def startup_event():
        # Запускаем cleanup task для bot storage
        storage = get_bot_status_storage()
        await storage.start_cleanup_task()

        # Запускаем sync task для обновления статусов
        sync_task = get_bot_status_sync_task(storage)
        await sync_task.start()

        logging.info('Background tasks started')

    # Shutdown event: остановка фоновых задач
    @app.on_event('shutdown')
    async def shutdown_event():
        storage = get_bot_status_storage()
        await storage.stop_cleanup_task()

        sync_task = get_bot_status_sync_task(storage)
        await sync_task.stop()

        logging.info('Background tasks stopped')

    return app

if __name__ == '__main__':
    uvicorn.run(
        create_app(),
        factory=True,
        host='0.0.0.0',
        port=8000,
        log_level='info',
        reload=True
    )
