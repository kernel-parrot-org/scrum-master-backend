from scrum_master.modules.jira.infrastructure.jira.api import JiraAPI
from .models import CreateIssueRequest, UpdateIssueRequest


class JiraService:
    def __init__(self, api: JiraAPI):
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

        return await self.api.create_issue(payload)

    async def update_issue(self, issue_key: str, dto: UpdateIssueRequest):
        fields = {}
        if dto.summary: fields["summary"] = dto.summary
        if dto.description: fields["description"] = dto.description
        if dto.assignee: fields["assignee"] = {"name": dto.assignee}
        return await self.api.update_issue(issue_key, fields)

    async def delete_issue(self, issue_key: str):
        return await self.api.delete_issue(issue_key)

