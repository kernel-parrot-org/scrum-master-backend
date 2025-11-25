import json
import logging
from typing import Any, Optional

from scrum_master.agents.meet_agent.core.config import settings
from scrum_master.modules.jira.infrastructure.jira.jira_client import JiraClient
from scrum_master.modules.jira.infrastructure.jira.jira_service import JiraService
from scrum_master.modules.jira.presentation.api.jira.schemas import (
    CreateIssueRequest,
    UpdateIssueRequest,
)

logger = logging.getLogger(__name__)


def _log_meeting_data(meeting_data: dict) -> None:
    """Log meeting_data structure to console for debugging."""
    logger.info("=" * 80)
    logger.info("MEETING DATA STRUCTURE:")
    logger.info("=" * 80)
    logger.info(json.dumps(meeting_data, indent=2, ensure_ascii=False))
    logger.info("=" * 80)


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


async def create_jira_epic(
    epic_name: str,
    summary: str,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    duedate: Optional[str] = None,
) -> dict:
    """
    Create a Jira epic.

    Args:
        epic_name: Epic name (short identifier).
        summary: Epic summary/title.
        description: Epic description (optional).
        priority: Priority level (optional).
        duedate: Due date in YYYY-MM-DD format (optional).
    """
    try:
        logger.info(f"[TOOL] Creating Jira epic: {epic_name}")
        service = _get_jira_service()

        request = CreateIssueRequest(
            project_key=settings.jira.project_key,
            summary=summary,
            description=description,
            issue_type="Epic",
            priority=priority,
            duedate=duedate,
            epic_name=epic_name,
        )

        result = await service.create_issue(request)
        logger.info(f"[TOOL] Jira epic created: {result}")
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"[TOOL] Failed to create Jira epic: {e}")
        return {"status": "error", "message": str(e)}


async def create_jira_subtask(
    parent_key: str,
    summary: str,
    description: Optional[str] = None,
    assignee: Optional[str] = None,
    priority: Optional[str] = None,
    duedate: Optional[str] = None,
) -> dict:
    """
    Create a Jira subtask under a parent issue.

    Args:
        parent_key: Parent issue key (e.g., "PROJ-123").
        summary: Subtask summary/title.
        description: Subtask description (optional).
        assignee: Assignee username (optional).
        priority: Priority level (optional).
        duedate: Due date in YYYY-MM-DD format (optional).
    """
    try:
        logger.info(f"[TOOL] Creating Jira subtask under {parent_key}: {summary}")
        service = _get_jira_service()

        request = CreateIssueRequest(
            project_key=settings.jira.project_key,
            summary=summary,
            description=description,
            assignee=assignee,
            issue_type="Sub-task",
            priority=priority,
            duedate=duedate,
            parent_key=parent_key,
        )

        result = await service.create_issue(request)
        logger.info(f"[TOOL] Jira subtask created: {result}")
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"[TOOL] Failed to create Jira subtask: {e}")
        return {"status": "error", "message": str(e)}


async def process_meeting_tasks_to_jira(meeting_data: dict) -> dict:
    """
    Process meeting_data and create Jira issues with proper decomposition.

    This function analyzes meeting_data structure and creates:
    - Epics for large technical specifications (project_complexity == "epic")
    - Tasks for individual work items
    - Subtasks for decomposed work items (task_type == "subtask")
    - Assigns tasks to team members
    
    Args:
        meeting_data: Structured meeting data containing tasks, participants, epic info, etc.
    """
    try:
        # ALWAYS log meeting_data to console for debugging
        _log_meeting_data(meeting_data)

        logger.info("[TOOL] Processing meeting tasks to Jira")
        service = _get_jira_service()

        tasks = meeting_data.get("tasks", [])
        project_complexity = meeting_data.get("project_complexity", "simple")
        created_issues = []
        epic_key = None

        # STEP 1: Create Epic if project is complex enough
        if project_complexity == "epic" and "epic" in meeting_data:
            epic_info = meeting_data["epic"]
            
            epic_summary = epic_info.get("title", "Project Epic")
            epic_description = epic_info.get("description", "")
            
            # Add meeting summary to epic description
            if "summary" in meeting_data:
                epic_description += f"\n\n**Meeting Summary:**\n{meeting_data['summary'].get('description', '')}"
                
                for topic in meeting_data.get("summary", {}).get("topics", []):
                    epic_description += f"\n\n**{topic.get('title', '')}**\n{topic.get('description', '')}"

            priority_map = {"high": "High", "medium": "Medium", "low": "Low"}
            
            epic_request = CreateIssueRequest(
                project_key=settings.jira.project_key,
                summary=epic_summary,
                description=epic_description,
                issue_type="Epic",
                epic_name=epic_summary[:50],  # Epic name has character limit
                priority=priority_map.get(epic_info.get("priority", "medium"), "Medium"),
                duedate=epic_info.get("deadline"),
            )

            epic_result = await service.create_issue(epic_request)
            epic_key = epic_result.get("key")
            created_issues.append({"type": "epic", "key": epic_key, "summary": epic_summary})
            logger.info(f"[TOOL] Created epic: {epic_key}")

        # STEP 2: Group tasks by parent-child relationship
        # Separate parent tasks from subtasks
        parent_tasks = [t for t in tasks if t.get("task_type") != "subtask"]
        subtasks = [t for t in tasks if t.get("task_type") == "subtask"]
        
        # Create mapping to store parent task keys
        task_title_to_key = {}

        # STEP 3: Create parent Tasks first
        for task in parent_tasks:
            task_description = _build_task_description(task)
            priority = _map_priority(task.get("priority", "medium"))

            request = CreateIssueRequest(
                project_key=settings.jira.project_key,
                summary=task.get("title", ""),
                description=task_description,
                assignee=None,
                issue_type="Task",
                priority=priority,
                duedate=task.get("deadline"),
            )

            result = await service.create_issue(request)
            task_key = result.get("key")
            task_title_to_key[task.get("title")] = task_key
            
            created_issues.append({
                "type": "task",
                "key": task_key,
                "summary": task.get("title"),
                "assignee": task.get("assignee")
            })
            logger.info(f"[TOOL] Created task: {task_key} - {task.get('title')}")

        # STEP 4: Create Subtasks with parent linkage
        for subtask in subtasks:
            parent_title = subtask.get("parent_task_title")
            parent_key = task_title_to_key.get(parent_title)
            
            if not parent_key:
                logger.warning(f"[TOOL] Parent task not found for subtask: {subtask.get('title')}. Creating as regular task instead.")
                # Create as regular task if parent not found
                task_description = _build_task_description(subtask)
                priority = _map_priority(subtask.get("priority", "medium"))
                
                request = CreateIssueRequest(
                    project_key=settings.jira.project_key,
                    summary=subtask.get("title", ""),
                    description=task_description,
                    assignee=None,
                    issue_type="Task",
                    priority=priority,
                    duedate=subtask.get("deadline"),
                )
                result = await service.create_issue(request)
                created_issues.append({
                    "type": "task_fallback",
                    "key": result.get("key"),
                    "summary": subtask.get("title")
                })
                continue

            # Create subtask with parent linkage
            task_description = _build_task_description(subtask)
            priority = _map_priority(subtask.get("priority", "medium"))
            
            request = CreateIssueRequest(
                project_key=settings.jira.project_key,
                summary=subtask.get("title", ""),
                description=task_description,
                assignee=None,
                issue_type="Sub-task",
                priority=priority,
                duedate=subtask.get("deadline"),
                parent_key=parent_key,
            )

            result = await service.create_issue(request)
            subtask_key = result.get("key")
            created_issues.append({
                "type": "subtask",
                "key": subtask_key,
                "summary": subtask.get("title"),
                "parent": parent_key,
                "assignee": subtask.get("assignee")
            })
            logger.info(f"[TOOL] Created subtask: {subtask_key} under {parent_key} - {subtask.get('title')}")

        # STEP 5: Return summary
        summary_msg = _create_summary_message(created_issues, epic_key)
        logger.info(f"[TOOL] {summary_msg}")
        
        return {
            "status": "success",
            "message": summary_msg,
            "data": {
                "epic_key": epic_key,
                "created_issues": created_issues,
                "total_count": len(created_issues)
            }
        }

    except Exception as e:
        logger.error(f"[TOOL] Failed to process meeting tasks to Jira: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


def _build_task_description(task: dict) -> str:
    """Build formatted task description from task data."""
    description = f"{task.get('description', '')}\\n\\n"
    
    if task.get('context'):
        description += f"**Context:** {task.get('context')}\\n"
    
    if task.get('priority_reason'):
        description += f"**Priority Reason:** {task.get('priority_reason')}\\n"
    
    if task.get('mentioned_by'):
        description += f"**Mentioned by:** {task.get('mentioned_by')}\\n"
    
    if task.get('skills_required'):
        skills = ", ".join(task.get('skills_required', []))
        description += f"**Skills Required:** {skills}\\n"
    
    return description


def _map_priority(priority_str: str) -> str:
    """Map priority string to Jira format."""
    priority_map = {
        "high": "High",
        "medium": "Medium",
        "low": "Low"
    }
    return priority_map.get(priority_str.lower(), "Medium")


def _create_summary_message(created_issues: list, epic_key: Optional[str]) -> str:
    """Create human-readable summary of created issues."""
    epics = [i for i in created_issues if i.get("type") == "epic"]
    tasks = [i for i in created_issues if i.get("type") == "task"]
    subtasks = [i for i in created_issues if i.get("type") == "subtask"]
    
    parts = []
    
    if epic_key:
        parts.append(f"1 Epic ({epic_key})")
    
    if tasks:
        parts.append(f"{len(tasks)} Tasks")
    
    if subtasks:
        parts.append(f"{len(subtasks)} Subtasks")
    
    summary = "Created " + ", ".join(parts) + " in Jira"
    return summary



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
