import logging
from typing import Optional

from scrum_master.agents.meet_agent.core.config import settings
from scrum_master.modules.jira.infrastructure.jira.jira_client import JiraClient
from scrum_master.modules.jira.infrastructure.jira.jira_service import JiraService
from scrum_master.modules.jira.presentation.api.jira.schemas import (
    CreateIssueRequest,
    UpdateIssueRequest,
)

logger = logging.getLogger(__name__)


def _get_jira_service() -> JiraService:
    client = JiraClient(
        url=settings.jira.api_url,
        token=settings.jira.api_token.get_secret_value(),
    )
    return JiraService(client)


async def create_jira_issue(
    summary: str,
    description: Optional[str] = None,
    assignee: Optional[str] = None,
    priority: Optional[str] = None,
    duedate: Optional[str] = None,
    issue_type: str = "Task",
) -> dict:
    """
    Create a new issue in Jira.
    
    Args:
        summary: The title/summary of the issue.
        description: Detailed description of the issue.
        assignee: Username of the assignee (optional).
        priority: Priority of the issue (e.g., "High", "Medium", "Low") (optional).
        duedate: Due date in YYYY-MM-DD format (optional).
        issue_type: Type of issue (default: "Task").
    """
    try:
        logger.info(f"[TOOL] Creating Jira issue: {summary}")
        service = _get_jira_service()
        
        request = CreateIssueRequest(
            project_key=settings.jira.project_key,
            summary=summary,
            description=description,
            assignee=assignee,
            issue_type=issue_type,
            priority=priority,
            duedate=duedate,
        )
        
        result = await service.create_issue(request)
        logger.info(f"[TOOL] Jira issue created: {result}")
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"[TOOL] Failed to create Jira issue: {e}")
        return {"status": "error", "message": str(e)}


async def update_jira_issue(
    issue_key: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    assignee: Optional[str] = None,
    priority: Optional[str] = None,
    duedate: Optional[str] = None,
) -> dict:
    """
    Update an existing Jira issue.
    
    Args:
        issue_key: The key of the issue to update (e.g., "PROJ-123").
        summary: New summary (optional).
        description: New description (optional).
        assignee: New assignee username (optional).
        priority: New priority (optional).
        duedate: New due date (optional).
    """
    try:
        logger.info(f"[TOOL] Updating Jira issue: {issue_key}")
        service = _get_jira_service()
        
        request = UpdateIssueRequest(
            summary=summary,
            description=description,
            assignee=assignee,
            priority=priority,
            duedate=duedate,
        )
        
        result = await service.update_issue(issue_key, request)
        logger.info(f"[TOOL] Jira issue updated: {result}")
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"[TOOL] Failed to update Jira issue: {e}")
        return {"status": "error", "message": str(e)}


async def search_jira_issues(query: str) -> dict:
    """
    Search for Jira issues using JQL (Jira Query Language) or simple text.
    Currently uses the board issues endpoint as a proxy for search if JQL is not fully supported by the client yet,
    or we can extend the client to support search.
    
    For now, let's assume we want to find issues to update them.
    """
    # TODO: Implement proper search if needed. For now, the agent might need to know the issue key.
    # If the user asks to "update the task about X", the agent needs to find it first.
    # Let's add a simple search by text in summary if possible, or just list recent issues.
    pass
