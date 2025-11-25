from typing import Optional

from pydantic import BaseModel


class JiraUser(BaseModel):
    name: str
    displayName: str
    emailAddress: Optional[str] = None


class CreateIssueFields(BaseModel):
    project: dict
    summary: str
    assignee: Optional[dict] = None
    issuetype: dict


class CreateIssuePayload(BaseModel):
    fields: CreateIssueFields


class CreateIssueRequest(BaseModel):
    project_key: str
    summary: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    issue_type: str = "Task"
    priority: Optional[str] = None
    duedate: Optional[str] = None
    parent_key: Optional[str] = None  # For subtasks - parent issue key
    epic_name: Optional[str] = None  # For epics - epic name

class UpdateIssueRequest(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    duedate: Optional[str] = None

