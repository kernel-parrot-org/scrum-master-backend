import logging
from pathlib import Path

from pydantic import ConfigDict
from scrum_master.utils.pydantic_fix import matching_adk_pydantic
try:
    matching_adk_pydantic()
except Exception as e:
    logging.error(f"Failed to apply monkeypatch: {e}")

from mcp.shared.context import RequestContext
RequestContext.__pydantic_config__ = ConfigDict(arbitrary_types_allowed=True)

import uvicorn
from dishka.integrations import fastapi as fastapi_integration
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from google.adk.cli.fast_api import get_fast_api_app

from scrum_master.ioc import create_container
from scrum_master.modules.auth.presentation.api.auth.router import router as auth_router
from scrum_master.modules.google_meet.presentation.api.meet.router import router as meet_router
from scrum_master.agents.meet_agent.api.routes import router as meet_agent_router
from google.adk.cli.fast_api import get_fast_api_app


BASE_DIR = Path(__file__).resolve().parent

logger = logging.getLogger(__name__)


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
