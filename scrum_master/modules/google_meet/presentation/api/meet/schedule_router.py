"""Schedule API for managing meeting schedules."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID, uuid4

import httpx
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scrum_master.modules.auth.domain.entities import (
    OAuthConnection,
    OAuthProvider,
    ScheduledMeeting,
    ScheduleType,
)
from scrum_master.modules.auth.infrastructure.security.jwt_service import JWTService
from scrum_master.modules.google_meet.infrastructure.calendar import GoogleCalendarService
from scrum_master.modules.google_meet.infrastructure.scheduler import MeetingScheduler
from scrum_master.modules.google_meet.presentation.api.meet.schemas import (
    CalendarEventResponse,
    CalendarEventsResponse,
    CreateCalendarEventRequest,
    CreateCalendarEventResponse,
    CreateScheduleRequest,
    ScheduleListResponse,
    ScheduleResponse,
    SyncCalendarRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1/schedules', tags=['Meeting Schedules'])
security = HTTPBearer()


def _build_calendar_link(event_id: str | None) -> str | None:
    """Build Google Calendar event link from event ID."""
    if not event_id:
        return None
    import base64
    from urllib.parse import quote
    # Google Calendar requires base64url-encoded event ID
    encoded_id = base64.urlsafe_b64encode(event_id.encode()).decode().rstrip('=')
    return f'https://calendar.google.com/calendar/event?eid={quote(encoded_id)}'


def _schedule_to_response(schedule: ScheduledMeeting) -> ScheduleResponse:
    """Convert ScheduledMeeting to response with calendar link."""
    return ScheduleResponse(
        id=schedule.id,
        meet_url=schedule.meet_url,
        bot_name=schedule.bot_name,
        schedule_type=schedule.schedule_type.value,
        scheduled_time=schedule.scheduled_time,
        days_of_week=schedule.days_of_week,
        is_active=schedule.is_active,
        next_trigger_at=schedule.next_trigger_at,
        created_at=schedule.created_at,
        calendar_event_id=schedule.calendar_event_id,
        calendar_link=_build_calendar_link(schedule.calendar_event_id),
    )


@router.post('', response_model=ScheduleResponse, summary='Create a new schedule')
@inject
async def create_schedule(
    request: CreateScheduleRequest,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
    db: FromDishka[AsyncSession],
    scheduler: FromDishka[MeetingScheduler],
    calendar_service: FromDishka[GoogleCalendarService],
) -> ScheduleResponse:
    """Create a new scheduled meeting."""
    try:
        payload = jwt_service.verify_access_token(credentials.credentials)
        user_id = UUID(payload.sub)
        
        # Calculate next trigger time
        next_trigger = _calculate_next_trigger(
            request.schedule_type,
            request.scheduled_time,
            request.days_of_week,
        )
        
        calendar_event_id = None
        
        # Create calendar event if requested
        if request.create_calendar_event and request.scheduled_time:
            try:
                # Get user's Google OAuth connection
                oauth_result = await db.execute(
                    select(OAuthConnection)
                    .where(
                        OAuthConnection.user_id == user_id,
                        OAuthConnection.provider == OAuthProvider.GOOGLE,
                    )
                )
                oauth = oauth_result.scalar_one_or_none()
                
                if oauth and oauth.refresh_token:
                    # Refresh token if needed
                    access_token = oauth.access_token
                    try:
                        token_data = await calendar_service.refresh_access_token(oauth.refresh_token)
                        access_token = token_data['access_token']
                        oauth.access_token = access_token
                        await db.commit()
                    except Exception as e:
                        logger.warning(f'Failed to refresh token: {e}')
                    
                    # Calculate end time (default +1 hour)
                    end_time = request.scheduled_time + timedelta(hours=1)
                    
                    # Create calendar event
                    try:
                        event = await calendar_service.create_event_with_meet(
                            access_token=access_token,
                            summary=f'{request.bot_name} - {request.meet_url}',
                            start_time=request.scheduled_time,
                            end_time=end_time,
                            description=f'Bot scheduled to join: {request.meet_url}',
                        )
                        calendar_event_id = event['id']
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 403:
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail='Calendar access denied. Please re-login with Google to grant calendar permissions.',
                            )
                        raise
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f'Failed to create calendar event: {e}')
        
        # Create schedule in DB
        schedule = ScheduledMeeting(
            id=uuid4(),
            user_id=user_id,
            meet_url=request.meet_url,
            bot_name=request.bot_name,
            schedule_type=ScheduleType(request.schedule_type.value),
            scheduled_time=request.scheduled_time,
            days_of_week=request.days_of_week,
            calendar_event_id=calendar_event_id,
            is_active=True,
            next_trigger_at=next_trigger,
        )
        
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        
        # Add to scheduler
        job_id = str(schedule.id)
        if request.schedule_type == 'once' and request.scheduled_time:
            scheduler.schedule_once(job_id, request.meet_url, request.bot_name, request.scheduled_time)
        elif request.schedule_type == 'daily' and request.scheduled_time:
            scheduler.schedule_daily(
                job_id, request.meet_url, request.bot_name,
                request.scheduled_time.hour, request.scheduled_time.minute,
            )
        elif request.schedule_type == 'weekly' and request.scheduled_time and request.days_of_week:
            scheduler.schedule_weekly(
                job_id, request.meet_url, request.bot_name,
                request.days_of_week,
                request.scheduled_time.hour, request.scheduled_time.minute,
            )
        
        logger.info(f'Created schedule {schedule.id} for user {user_id}')
        
        return _schedule_to_response(schedule)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f'Failed to create schedule: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('', response_model=ScheduleListResponse, summary='List all schedules')
@inject
async def list_schedules(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
    db: FromDishka[AsyncSession],
) -> ScheduleListResponse:
    """Get all schedules for the current user."""
    try:
        payload = jwt_service.verify_access_token(credentials.credentials)
        user_id = UUID(payload.sub)
        
        result = await db.execute(
            select(ScheduledMeeting)
            .where(ScheduledMeeting.user_id == user_id)
            .order_by(ScheduledMeeting.next_trigger_at)
        )
        schedules = result.scalars().all()
        
        return ScheduleListResponse(
            schedules=[_schedule_to_response(s) for s in schedules],
            total=len(schedules),
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.delete('/{schedule_id}', summary='Delete a schedule')
@inject
async def delete_schedule(
    schedule_id: UUID,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
    db: FromDishka[AsyncSession],
    scheduler: FromDishka[MeetingScheduler],
):
    """Delete a scheduled meeting."""
    try:
        payload = jwt_service.verify_access_token(credentials.credentials)
        user_id = UUID(payload.sub)
        
        result = await db.execute(
            select(ScheduledMeeting)
            .where(ScheduledMeeting.id == schedule_id, ScheduledMeeting.user_id == user_id)
        )
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Schedule not found')
        
        # Remove from scheduler
        scheduler.remove_schedule(str(schedule_id))
        
        # Delete from DB
        await db.delete(schedule)
        await db.commit()
        
        return {'message': 'Schedule deleted successfully'}
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.patch('/{schedule_id}/toggle', response_model=ScheduleResponse, summary='Toggle schedule active state')
@inject
async def toggle_schedule(
    schedule_id: UUID,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
    db: FromDishka[AsyncSession],
    scheduler: FromDishka[MeetingScheduler],
) -> ScheduleResponse:
    """Toggle a schedule between active and inactive."""
    try:
        payload = jwt_service.verify_access_token(credentials.credentials)
        user_id = UUID(payload.sub)
        
        result = await db.execute(
            select(ScheduledMeeting)
            .where(ScheduledMeeting.id == schedule_id, ScheduledMeeting.user_id == user_id)
        )
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Schedule not found')
        
        schedule.is_active = not schedule.is_active
        
        if schedule.is_active:
            # Re-add to scheduler
            _add_to_scheduler(scheduler, schedule)
        else:
            # Remove from scheduler
            scheduler.remove_schedule(str(schedule_id))
        
        await db.commit()
        await db.refresh(schedule)
        
        return _schedule_to_response(schedule)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get('/calendar/events', response_model=CalendarEventsResponse, summary='Get Google Calendar events with Meet links')
@inject
async def get_calendar_events(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
    db: FromDishka[AsyncSession],
    calendar_service: FromDishka[GoogleCalendarService],
    days_ahead: int = 7,
) -> CalendarEventsResponse:
    """Get upcoming Google Calendar events that have Google Meet links."""
    try:
        payload = jwt_service.verify_access_token(credentials.credentials)
        user_id = UUID(payload.sub)
        
        # Get user's Google OAuth connection
        result = await db.execute(
            select(OAuthConnection)
            .where(
                OAuthConnection.user_id == user_id,
                OAuthConnection.provider == OAuthProvider.GOOGLE,
            )
        )
        oauth = result.scalar_one_or_none()
        
        if not oauth:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='No Google account connected. Please login with Google first.',
            )
        
        # Refresh token if needed
        access_token = oauth.access_token
        if oauth.refresh_token:
            try:
                token_data = await calendar_service.refresh_access_token(oauth.refresh_token)
                access_token = token_data['access_token']
                oauth.access_token = access_token
                await db.commit()
            except Exception as e:
                logger.warning(f'Failed to refresh token: {e}')
        
        # Get calendar events
        try:
            events = await calendar_service.get_upcoming_events(
                access_token,
                time_max=datetime.now(timezone.utc) + timedelta(days=days_ahead),
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Calendar access denied. Please re-login with Google to grant calendar permissions.',
                )
            raise
        
        return CalendarEventsResponse(
            events=[CalendarEventResponse(**e) for e in events],
            total=len(events),
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to get calendar events: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post('/calendar/events', response_model=CreateCalendarEventResponse, summary='Create Google Calendar event with Meet link')
@inject
async def create_calendar_event(
    request: CreateCalendarEventRequest,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
    db: FromDishka[AsyncSession],
    calendar_service: FromDishka[GoogleCalendarService],
    scheduler: FromDishka[MeetingScheduler],
) -> CreateCalendarEventResponse:
    """Create a new Google Calendar event with automatic Meet link generation."""
    try:
        payload = jwt_service.verify_access_token(credentials.credentials)
        user_id = UUID(payload.sub)
        
        # Get user's Google OAuth connection
        result = await db.execute(
            select(OAuthConnection)
            .where(
                OAuthConnection.user_id == user_id,
                OAuthConnection.provider == OAuthProvider.GOOGLE,
            )
        )
        oauth = result.scalar_one_or_none()
        
        if not oauth:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='No Google account connected. Please login with Google first.',
            )
        
        # Refresh token if needed
        access_token = oauth.access_token
        if oauth.refresh_token:
            try:
                token_data = await calendar_service.refresh_access_token(oauth.refresh_token)
                access_token = token_data['access_token']
                oauth.access_token = access_token
                await db.commit()
            except Exception as e:
                logger.warning(f'Failed to refresh token: {e}')
        
        # Create calendar event with Meet link
        try:
            event = await calendar_service.create_event_with_meet(
                access_token=access_token,
                summary=request.summary,
                start_time=request.start_time,
                end_time=request.end_time,
                description=request.description,
                attendees=request.attendees,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Calendar access denied. Please re-login with Google to grant calendar permissions.',
                )
            raise
        
        schedule_id = None
        
        # Auto-schedule bot if requested
        if request.auto_schedule_bot and event.get('meet_link'):
            schedule = ScheduledMeeting(
                id=uuid4(),
                user_id=user_id,
                meet_url=event['meet_link'],
                bot_name=request.bot_name,
                schedule_type=ScheduleType.CALENDAR,
                scheduled_time=request.start_time,
                calendar_event_id=event['id'],
                is_active=True,
                next_trigger_at=request.start_time - timedelta(minutes=1),
            )
            
            db.add(schedule)
            await db.commit()
            await db.refresh(schedule)
            
            scheduler.schedule_once(
                str(schedule.id),
                event['meet_link'],
                request.bot_name,
                request.start_time,
            )
            
            schedule_id = schedule.id
            logger.info(f'Created schedule {schedule_id} for calendar event {event["id"]}')
        
        return CreateCalendarEventResponse(
            event_id=event['id'],
            summary=event['summary'],
            start=event['start'],
            end=event['end'],
            meet_link=event['meet_link'],
            html_link=event['html_link'],
            schedule_id=schedule_id,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f'Failed to create calendar event: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post('/calendar/sync', response_model=ScheduleListResponse, summary='Sync Google Calendar events as schedules')
@inject
async def sync_calendar(
    request: SyncCalendarRequest,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
    db: FromDishka[AsyncSession],
    calendar_service: FromDishka[GoogleCalendarService],
    scheduler: FromDishka[MeetingScheduler],
) -> ScheduleListResponse:
    """Sync Google Calendar events and create schedules for meetings with Meet links."""
    try:
        payload = jwt_service.verify_access_token(credentials.credentials)
        user_id = UUID(payload.sub)
        
        # Get user's Google OAuth connection
        result = await db.execute(
            select(OAuthConnection)
            .where(
                OAuthConnection.user_id == user_id,
                OAuthConnection.provider == OAuthProvider.GOOGLE,
            )
        )
        oauth = result.scalar_one_or_none()
        
        if not oauth:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='No Google account connected',
            )
        
        # Get calendar events
        try:
            events = await calendar_service.get_upcoming_events(
                oauth.access_token,
                time_max=datetime.now(timezone.utc) + timedelta(days=request.days_ahead),
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Calendar access denied. Please re-login with Google to grant calendar permissions.',
                )
            raise
        
        created_schedules = []
        
        if request.auto_schedule:
            for event in events:
                # Check if schedule already exists for this event
                existing = await db.execute(
                    select(ScheduledMeeting)
                    .where(
                        ScheduledMeeting.user_id == user_id,
                        ScheduledMeeting.calendar_event_id == event['id'],
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                
                # Parse start time
                try:
                    start_time = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                except:
                    continue
                
                # Create schedule
                schedule = ScheduledMeeting(
                    id=uuid4(),
                    user_id=user_id,
                    meet_url=event['meet_link'],
                    bot_name=f"Bot - {event['summary'][:20]}",
                    schedule_type=ScheduleType.CALENDAR,
                    scheduled_time=start_time,
                    calendar_event_id=event['id'],
                    is_active=True,
                    next_trigger_at=start_time - timedelta(minutes=1),
                )
                
                db.add(schedule)
                scheduler.schedule_once(str(schedule.id), event['meet_link'], schedule.bot_name, start_time)
                created_schedules.append(schedule)
            
            await db.commit()
        
        return ScheduleListResponse(
            schedules=[ScheduleResponse.model_validate(s) for s in created_schedules],
            total=len(created_schedules),
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f'Failed to sync calendar: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


def _calculate_next_trigger(
    schedule_type: str,
    scheduled_time: datetime | None,
    days_of_week: str | None,
) -> datetime | None:
    """Calculate the next trigger time for a schedule."""
    if not scheduled_time:
        return None
    
    now = datetime.now(timezone.utc)
    
    if schedule_type == 'once':
        return scheduled_time - timedelta(minutes=1)
    
    elif schedule_type == 'daily':
        # Next occurrence at the specified time
        next_time = now.replace(hour=scheduled_time.hour, minute=scheduled_time.minute, second=0, microsecond=0)
        if next_time <= now:
            next_time += timedelta(days=1)
        return next_time - timedelta(minutes=1)
    
    elif schedule_type == 'weekly' and days_of_week:
        days = [int(d) for d in days_of_week.split(',')]
        current_day = now.weekday()
        
        # Find next matching day
        for i in range(8):
            check_day = (current_day + i) % 7
            if check_day in days:
                next_time = now + timedelta(days=i)
                next_time = next_time.replace(hour=scheduled_time.hour, minute=scheduled_time.minute, second=0, microsecond=0)
                if next_time > now:
                    return next_time - timedelta(minutes=1)
    
    return None


def _add_to_scheduler(scheduler: MeetingScheduler, schedule: ScheduledMeeting):
    """Add a schedule to the scheduler."""
    job_id = str(schedule.id)
    
    if schedule.schedule_type == ScheduleType.ONCE and schedule.scheduled_time:
        scheduler.schedule_once(job_id, schedule.meet_url, schedule.bot_name, schedule.scheduled_time)
    elif schedule.schedule_type == ScheduleType.DAILY and schedule.scheduled_time:
        scheduler.schedule_daily(
            job_id, schedule.meet_url, schedule.bot_name,
            schedule.scheduled_time.hour, schedule.scheduled_time.minute,
        )
    elif schedule.schedule_type == ScheduleType.WEEKLY and schedule.scheduled_time and schedule.days_of_week:
        scheduler.schedule_weekly(
            job_id, schedule.meet_url, schedule.bot_name,
            schedule.days_of_week,
            schedule.scheduled_time.hour, schedule.scheduled_time.minute,
        )
    elif schedule.schedule_type == ScheduleType.CALENDAR and schedule.scheduled_time:
        scheduler.schedule_once(job_id, schedule.meet_url, schedule.bot_name, schedule.scheduled_time)

