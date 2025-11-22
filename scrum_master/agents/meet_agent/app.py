import logging
from pathlib import Path

import uvicorn
from api.routes import router as api_router
from core.config import Settings, settings
from core.ioc import AppProvider
from core.logging import configure_logging
from dishka import make_async_container
from dishka.integrations import fastapi as fastapi_integration
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from starlette.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
AGENT_DIR = BASE_DIR

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    configure_logging()
    container = make_async_container(AppProvider(), context={Settings: settings})
    app = get_fast_api_app(
        agents_dir=str(AGENT_DIR),
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

    app.include_router(api_router)


    return app


if __name__ == '__main__':
    uvicorn.run(create_app(), host='0.0.0.0', port=8000, log_level='info', reload=True)
