"""Google Calendar Service for fetching meetings."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Service to interact with Google Calendar API."""
    
    CALENDAR_API_BASE = 'https://www.googleapis.com/calendar/v3'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
    
    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh the access token using refresh token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token',
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def get_upcoming_events(
        self,
        access_token: str,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 50,
    ) -> list[dict]:
        """Get upcoming calendar events with Google Meet links."""
        if time_min is None:
            time_min = datetime.now(timezone.utc)
        if time_max is None:
            time_max = time_min + timedelta(days=7)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.CALENDAR_API_BASE}/calendars/primary/events',
                headers={'Authorization': f'Bearer {access_token}'},
                params={
                    'timeMin': time_min.isoformat(),
                    'timeMax': time_max.isoformat(),
                    'maxResults': max_results,
                    'singleEvents': 'true',
                    'orderBy': 'startTime',
                },
            )
            response.raise_for_status()
            data = response.json()
            
            # Filter events with Google Meet links
            events_with_meet = []
            for event in data.get('items', []):
                meet_link = self._extract_meet_link(event)
                if meet_link:
                    events_with_meet.append({
                        'id': event['id'],
                        'summary': event.get('summary', 'No title'),
                        'start': event.get('start', {}).get('dateTime') or event.get('start', {}).get('date'),
                        'end': event.get('end', {}).get('dateTime') or event.get('end', {}).get('date'),
                        'meet_link': meet_link,
                        'organizer': event.get('organizer', {}).get('email'),
                        'attendees': [a.get('email') for a in event.get('attendees', [])],
                    })
            
            logger.info(f'Found {len(events_with_meet)} events with Google Meet links')
            return events_with_meet
    
    def _extract_meet_link(self, event: dict) -> Optional[str]:
        """Extract Google Meet link from event."""
        # Check conferenceData
        conf_data = event.get('conferenceData', {})
        for entry_point in conf_data.get('entryPoints', []):
            if entry_point.get('entryPointType') == 'video':
                uri = entry_point.get('uri', '')
                if 'meet.google.com' in uri:
                    return uri
        
        # Check hangoutLink (legacy)
        hangout_link = event.get('hangoutLink')
        if hangout_link and 'meet.google.com' in hangout_link:
            return hangout_link
        
        # Check description for meet links
        description = event.get('description', '')
        if 'meet.google.com/' in description:
            import re
            match = re.search(r'https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}', description)
            if match:
                return match.group(0)
        
        return None
    
    async def get_event_by_id(self, access_token: str, event_id: str) -> Optional[dict]:
        """Get a specific calendar event by ID."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f'{self.CALENDAR_API_BASE}/calendars/primary/events/{event_id}',
                    headers={'Authorization': f'Bearer {access_token}'},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f'Failed to get event {event_id}: {e}')
                return None
    
    async def create_event_with_meet(
        self,
        access_token: str,
        summary: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        description: str = '',
        attendees: Optional[list[str]] = None,
    ) -> dict:
        """Create a calendar event with automatic Google Meet link."""
        if end_time is None:
            end_time = start_time + timedelta(hours=1)
        
        event_body = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'conferenceData': {
                'createRequest': {
                    'requestId': f'meet-{start_time.timestamp()}',
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'},
                },
            },
        }
        
        if attendees:
            event_body['attendees'] = [{'email': email} for email in attendees]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.CALENDAR_API_BASE}/calendars/primary/events',
                headers={'Authorization': f'Bearer {access_token}'},
                params={'conferenceDataVersion': '1'},
                json=event_body,
            )
            response.raise_for_status()
            event = response.json()
            
            meet_link = self._extract_meet_link(event)
            logger.info(f'Created calendar event {event["id"]} with Meet link: {meet_link}')
            
            return {
                'id': event['id'],
                'summary': event.get('summary'),
                'start': event.get('start', {}).get('dateTime'),
                'end': event.get('end', {}).get('dateTime'),
                'meet_link': meet_link,
                'html_link': event.get('htmlLink'),
            }
    
    async def delete_event(self, access_token: str, event_id: str) -> bool:
        """Delete a calendar event."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    f'{self.CALENDAR_API_BASE}/calendars/primary/events/{event_id}',
                    headers={'Authorization': f'Bearer {access_token}'},
                )
                response.raise_for_status()
                logger.info(f'Deleted calendar event {event_id}')
                return True
            except httpx.HTTPStatusError as e:
                logger.error(f'Failed to delete event {event_id}: {e}')
                return False
    
    async def update_event(
        self,
        access_token: str,
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None,
    ) -> Optional[dict]:
        """Update an existing calendar event."""
        # First get current event
        current = await self.get_event_by_id(access_token, event_id)
        if not current:
            return None
        
        # Build update body
        update_body = {}
        if summary is not None:
            update_body['summary'] = summary
        if description is not None:
            update_body['description'] = description
        if start_time is not None:
            update_body['start'] = {'dateTime': start_time.isoformat(), 'timeZone': 'UTC'}
        if end_time is not None:
            update_body['end'] = {'dateTime': end_time.isoformat(), 'timeZone': 'UTC'}
        
        if not update_body:
            return current
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f'{self.CALENDAR_API_BASE}/calendars/primary/events/{event_id}',
                headers={'Authorization': f'Bearer {access_token}'},
                json=update_body,
            )
            response.raise_for_status()
            event = response.json()
            
            return {
                'id': event['id'],
                'summary': event.get('summary'),
                'start': event.get('start', {}).get('dateTime'),
                'end': event.get('end', {}).get('dateTime'),
                'meet_link': self._extract_meet_link(event),
                'html_link': event.get('htmlLink'),
            }

