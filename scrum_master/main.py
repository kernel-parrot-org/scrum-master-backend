import logging
from pathlib import Path

import uvicorn
from dishka.integrations import fastapi as fastapi_integration
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from scrum_master.ioc import create_container
from scrum_master.modules.auth.presentation.api.auth.router import router as auth_router
from scrum_master.modules.jira.router import router as jira_router

BASE_DIR = Path(__file__).resolve().parent

logger = logging.getLogger(__name__)

container = create_container()

def create_app() -> FastAPI:
    app = FastAPI(
        title='Scrum Master API',
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
    app.include_router(jira_router)

    return app


if __name__ == '__main__':
    uvicorn.run(
        'scrum_master.main:create_app',
        factory=True,
        host='0.0.0.0',
        port=8000,
        log_level='info',
        reload=True
    )
