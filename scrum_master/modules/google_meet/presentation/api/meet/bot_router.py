import logging
from typing import Annotated

import httpx
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from scrum_master.modules.auth.infrastructure.security.jwt_service import JWTService
from scrum_master.modules.google_meet.presentation.api.meet.bot_schemas import (
    TriggerBotRequest,
    TriggerBotResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1/meet-bot', tags=['Meet Bot Integration'])
security = HTTPBearer()


@router.post('/trigger', summary='Trigger bot to join Google Meet', response_model=TriggerBotResponse)
@inject
async def trigger_bot(
    request: TriggerBotRequest,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
) -> TriggerBotResponse:
    """
    Trigger the Tamir bot to join a Google Meet meeting.
    Requires authentication.
    """
    try:
        # Verify authentication
        token = credentials.credentials
        payload = jwt_service.verify_access_token(token)
        user_id = payload.sub  # AccessTokenPayload has 'sub' attribute, not dict
        
        logger.info(f'User {user_id} triggering bot for meeting: {request.meet_url}')
        
        # Call google-meet-bot API
        async with httpx.AsyncClient(timeout=30.0) as client:
            bot_request = {
                'meetlink': request.meet_url,
                'bot_name': request.bot_name,
                'min_record_time': 120,
                'max_waiting_time': 1800,
            }
            
            response = await client.post(
                'http://host.docker.internal:8001/api/v1/bots/start',
                json=bot_request
            )
            response.raise_for_status()
            bot_data = response.json()
            
            logger.info(f'Bot started successfully: {bot_data.get("bot_id")}')
            
            return TriggerBotResponse(
                bot_id=bot_data['bot_id'],
                status=bot_data['status'],
                message=f'Bot {bot_data["bot_id"]} started successfully for meeting'
            )
            
    except httpx.HTTPStatusError as e:
        logger.error(f'Failed to start bot: {e.response.text}')
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Failed to start bot: {e.response.text}'
        )
    except httpx.RequestError as e:
        logger.error(f'Failed to connect to bot service: {e}')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Bot service is unavailable'
        )
    except ValueError as e:
        logger.error(f'Invalid token: {e}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid authentication credentials'
        )
    except Exception as e:
        logger.error(f'Error triggering bot: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to trigger bot: {str(e)}'
        )
