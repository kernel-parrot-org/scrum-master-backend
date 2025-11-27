from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TriggerBotRequest(BaseModel):
    meet_url: str = Field(..., description='Google Meet URL to join')
    bot_name: str = Field('Tamir Bot', description='Bot display name in the meeting')


class TriggerBotResponse(BaseModel):
    bot_id: str = Field(..., description='Bot ID from google-meet-bot service')
    status: str = Field(..., description='Bot status')
    message: str = Field(..., description='Status message')


# Schedule schemas
class ScheduleType(str, Enum):
    ONCE = 'once'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    CALENDAR = 'calendar'


class CreateScheduleRequest(BaseModel):
    meet_url: str = Field(..., description='Google Meet URL')
    bot_name: str = Field('Scrum Bot', description='Bot name')
    schedule_type: ScheduleType = Field(..., description='Type of schedule')
    scheduled_time: Optional[datetime] = Field(None, description='For ONCE: exact datetime, For DAILY/WEEKLY: time of day (hour:minute used)')
    days_of_week: Optional[str] = Field(None, description='For WEEKLY: comma-separated days (0=Mon, 6=Sun), e.g. "0,2,4"')
    create_calendar_event: bool = Field(False, description='Create Google Calendar event for this schedule')


class ScheduleResponse(BaseModel):
    id: UUID
    meet_url: str
    bot_name: str
    schedule_type: ScheduleType
    scheduled_time: Optional[datetime]
    days_of_week: Optional[str]
    is_active: bool
    next_trigger_at: Optional[datetime]
    created_at: datetime
    calendar_event_id: Optional[str] = None
    calendar_link: Optional[str] = None

    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    schedules: list[ScheduleResponse]
    total: int


class CalendarEventResponse(BaseModel):
    id: str
    summary: str
    start: str
    end: str
    meet_link: str
    organizer: Optional[str]


class CalendarEventsResponse(BaseModel):
    events: list[CalendarEventResponse]
    total: int


class SyncCalendarRequest(BaseModel):
    """Request to sync Google Calendar events as schedules."""
    days_ahead: int = Field(7, description='How many days ahead to sync')
    auto_schedule: bool = Field(True, description='Automatically create schedules for events with Meet links')


# Calendar event creation schemas
class CreateCalendarEventRequest(BaseModel):
    """Create a new Google Calendar event with Meet link."""
    summary: str = Field(..., description='Event title')
    start_time: datetime = Field(..., description='Event start time (UTC)')
    end_time: Optional[datetime] = Field(None, description='Event end time (UTC), defaults to +1 hour')
    description: str = Field('', description='Event description')
    attendees: Optional[list[str]] = Field(None, description='List of attendee emails')
    auto_schedule_bot: bool = Field(True, description='Automatically schedule bot to join this meeting')
    bot_name: str = Field('Scrum Bot', description='Bot name if auto_schedule_bot is True')


class CreateCalendarEventResponse(BaseModel):
    """Response after creating calendar event."""
    event_id: str = Field(..., description='Google Calendar event ID')
    summary: str
    start: str
    end: str
    meet_link: str = Field(..., description='Generated Google Meet link')
    html_link: str = Field(..., description='Link to view event in Google Calendar')
    schedule_id: Optional[UUID] = Field(None, description='Created schedule ID if auto_schedule_bot=True')
