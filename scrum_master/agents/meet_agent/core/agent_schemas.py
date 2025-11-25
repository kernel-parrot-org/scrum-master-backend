from typing import List, Optional

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    """Request to send a message to the agent."""
    message: str = Field(..., description="Message to send to the agent")
    session_id: Optional[str] = Field(None, description="Optional session ID for context")


class TranscribeAndCreateTasksRequest(BaseModel):
    """Request to transcribe audio and create tasks in Jira."""
    audio_uri: str = Field(..., description="GCS URI of the audio file (e.g., gs://bucket/file.wav)")
    project_key: str = Field(..., description="Jira project key")
    team_members: Optional[List[str]] = Field(
        None, 
        description="Optional list of team member names. If not provided, will use default team from DB."
    )


class TranscribeAndCreateTasksResponse(BaseModel):
    """Response from transcribe and create tasks endpoint."""
    status: str
    message: str
    meeting_id: Optional[str] = None
    jira_results: Optional[dict] = None
    meeting_data: Optional[dict] = Field(
        None, 
        description="Full meeting_data structure (also logged to console)"
    )


class AgentResponse(BaseModel):
    """Generic agent response."""
    status: str
    message: str
    data: Optional[dict] = None


class TeamMember(BaseModel):
    """Team member information."""
    name: str
    jira_username: str
    skills: List[str] = Field(default_factory=list)
    email: Optional[str] = None


class CreateTeamMemberRequest(BaseModel):
    """Request to create a team member."""
    name: str
    jira_username: str
    skills: List[str] = Field(default_factory=list, description="List of skills (e.g., ['backend', 'python', 'fastapi'])")
    email: Optional[str] = None
    project_key: str
