from scrum_master.modules.jira.infrastructure.jira.jira_client import JiraClient

from scrum_master.modules.jira.presentation.api.jira.schemas import (
    CreateIssueRequest,
    UpdateIssueRequest
)


class JiraService:
    def __init__(self, api: JiraClient):
        self.api = api

    async def get_users(self):
        return await self.api.get_users()

    async def get_boards(self):
        return await self.api.get_boards()

    async def get_board_issues(self, board_id: int):
        return await self.api.get_board_issues(board_id)

    async def create_issue(self, dto: CreateIssueRequest):
        payload = {
            "fields": {
                "project": {"key": dto.project_key},
                "summary": dto.summary,
                "issuetype": {"name": dto.issue_type},
            }
        }

        if dto.description:
            payload["fields"]["description"] = dto.description

        if dto.assignee:
            payload["fields"]["assignee"] = {"name": dto.assignee}

        if dto.priority:
            payload["fields"]["priority"] = {"name": dto.priority}

        # Commented out - not configured in Jira project
        # if dto.duedate:
        #     payload["fields"]["duedate"] = dto.duedate

        # Handle subtasks - add parent link
        if dto.parent_key:
            payload["fields"]["parent"] = {"key": dto.parent_key}

        # Handle epics - add epic name (REQUIRED for Epic type)
        if dto.epic_name and dto.issue_type == "Epic":
            payload["fields"]["customfield_10105"] = dto.epic_name

        return await self.api.create_issue(payload)

    async def update_issue(self, issue_key: str, dto: UpdateIssueRequest):
        fields = {}
        if dto.summary: fields["summary"] = dto.summary
        if dto.description: fields["description"] = dto.description
        if dto.assignee: fields["assignee"] = {"name": dto.assignee}
        if dto.priority: fields["priority"] = {"name": dto.priority}
        if dto.duedate: fields["duedate"] = dto.duedate
        return await self.api.update_issue(issue_key, fields)

    async def delete_issue(self, issue_key: str):
        return await self.api.delete_issue(issue_key)

