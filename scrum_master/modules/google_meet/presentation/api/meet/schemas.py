from typing import Optional

from pydantic import BaseModel, Field


class TriggerBotRequest(BaseModel):
    meet_url: str = Field(..., description='Google Meet URL to join')
    bot_name: str = Field('Tamir Bot', description='Bot display name in the meeting')


class TriggerBotResponse(BaseModel):
    bot_id: str = Field(..., description='Bot ID from google-meet-bot service')
    status: str = Field(..., description='Bot status')
    message: str = Field(..., description='Status message')


class BotStatusResponse(BaseModel):
    bot_id: str
    status: str
    user_id: str
    created_at: str
    updated_at: str
    error_message: Optional[str] = None
    session_id: Optional[str] = None
    result_data: Optional[dict] = None


class CreateTasksCallbackRequest(BaseModel):
    bot_id: str = Field(..., description='Bot ID to update status for')
    session_id: str = Field(..., description='Agent session ID')
    result_data: Optional[dict] = Field(None, description='Result data from agent')
