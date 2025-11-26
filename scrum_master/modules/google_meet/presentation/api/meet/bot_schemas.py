from pydantic import BaseModel, Field


class TriggerBotRequest(BaseModel):
    meet_url: str = Field(..., description='Google Meet URL to join')
    bot_name: str = Field('Tamir Bot', description='Bot display name in the meeting')


class TriggerBotResponse(BaseModel):
    bot_id: str = Field(..., description='Bot ID from google-meet-bot service')
    status: str = Field(..., description='Bot status')
    message: str = Field(..., description='Status message')
