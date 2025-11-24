import logging
from dishka.integrations.fastapi import inject
from dishka import FromDishka
from fastapi import APIRouter

from .service import JiraService
from .models import CreateIssueRequest, UpdateIssueRequest

router = APIRouter(prefix="/api/v1/jira", tags=["Jira"])
logger = logging.getLogger(__name__)


@router.get("/users")
@inject
async def get_users(service: FromDishka[JiraService]):
    return await service.get_users()


@router.get("/boards")
@inject
async def get_boards(service: FromDishka[JiraService]):
    return await service.get_boards()


@router.get("/boards/{board_id}/issues")
@inject
async def get_board_issues(board_id: int, service: FromDishka[JiraService]):
    return await service.get_board_issues(board_id)


@router.post("/issues")
@inject
async def create_issue(dto: CreateIssueRequest, service: FromDishka[JiraService]):
    return await service.create_issue(dto)


@router.put("/issues/{issue_key}")
@inject
async def update_issue(issue_key: str, dto: UpdateIssueRequest, service: FromDishka[JiraService]):
    return await service.update_issue(issue_key, dto)


@router.delete("/issues/{issue_key}")
@inject
async def delete_issue(issue_key: str, service: FromDishka[JiraService]):
    return await service.delete_issue(issue_key)

