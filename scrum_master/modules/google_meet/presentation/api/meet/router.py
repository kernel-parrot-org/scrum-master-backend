import logging
from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from scrum_master.modules.auth.infrastructure.security.jwt_service import JWTService
from scrum_master.modules.google_meet.application.dtos import (
    ConnectToMeetingRequest as ConnectRequest,
    DisconnectFromMeetingRequest as DisconnectRequest,
)
from scrum_master.modules.google_meet.application.interactors.connect_to_meet import (
    ConnectToMeetInteractor,
)
from scrum_master.modules.google_meet.application.interactors.disconnect_from_meet import (
    DisconnectFromMeetInteractor,
)
from scrum_master.modules.google_meet.application.interactors.get_meetings import (
    GetMeetingsInteractor,
)
from scrum_master.modules.google_meet.presentation.api.meet.schemas import (
    ConnectToMeetingRequest,
    DisconnectFromMeetingRequest,
    MeetingListResponse,
    MeetingResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1/meet', tags=['Google Meet'])
security = HTTPBearer()


@router.post('/connect', summary='Connect to Google Meet', response_model=MeetingResponse)
@inject
async def connect_to_meeting(
    request: ConnectToMeetingRequest,
    # credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
    interactor: FromDishka[ConnectToMeetInteractor],
) -> MeetingResponse:
    try:
        # token = credentials.credentials
        # payload = jwt_service.verify_access_token(token)

        dto = ConnectRequest(
            user_id="8de94579-b359-4ef9-af50-fefd435454fe",
            meet_url=request.meet_url,
            bot_name=request.bot_name,
            min_record_time=request.min_record_time,
            max_waiting_time=request.max_waiting_time,
            presigned_url_combined=request.presigned_url_combined,
            presigned_url_audio=request.presigned_url_audio,
        )

        result = await interactor.execute(dto)

        return MeetingResponse(
            id=result.id,
            user_id=result.user_id,
            meet_url=result.meet_url,
            status=result.status,
            bot_name=result.bot_name,
            error_message=result.error_message,
            connected_at=result.connected_at,
            disconnected_at=result.disconnected_at,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )

    except ValueError as e:
        logger.error(f'Invalid token: {e}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid authentication credentials',
        )
    except Exception as e:
        logger.error(f'Error connecting to meeting: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to connect to meeting: {str(e)}',
        )


@router.post(
    '/disconnect',
    summary='Disconnect from Google Meet',
    response_model=MeetingResponse,
)
@inject
async def disconnect_from_meeting(
    request: DisconnectFromMeetingRequest,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
    interactor: FromDishka[DisconnectFromMeetInteractor],
) -> MeetingResponse:
    try:
        token = credentials.credentials
        payload = jwt_service.verify_access_token(token)

        dto = DisconnectRequest(
            meeting_id=request.meeting_id,
            user_id="8de94579-b359-4ef9-af50-fefd435454fe",
        )

        result = await interactor.execute(dto)

        return MeetingResponse(
            id=result.id,
            user_id=result.user_id,
            meet_url=result.meet_url,
            status=result.status,
            bot_name=result.bot_name,
            error_message=result.error_message,
            connected_at=result.connected_at,
            disconnected_at=result.disconnected_at,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )

    except ValueError as e:
        logger.error(f'Error: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f'Error disconnecting from meeting: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to disconnect from meeting: {str(e)}',
        )


@router.get('/meetings', summary='Get user meetings', response_model=MeetingListResponse)
@inject
async def get_meetings(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
    interactor: FromDishka[GetMeetingsInteractor],
) -> MeetingListResponse:
    try:
        token = credentials.credentials
        payload = jwt_service.verify_access_token(token)

        meetings = await interactor.execute("8de94579-b359-4ef9-af50-fefd435454fe")

        return MeetingListResponse(
            meetings=[
                MeetingResponse(
                    id=m.id,
                    user_id=m.user_id,
                    meet_url=m.meet_url,
                    status=m.status,
                    bot_name=m.bot_name,
                    error_message=m.error_message,
                    connected_at=m.connected_at,
                    disconnected_at=m.disconnected_at,
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                )
                for m in meetings
            ],
            total=len(meetings),
        )

    except ValueError as e:
        logger.error(f'Invalid token: {e}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid authentication credentials',
        )
    except Exception as e:
        logger.error(f'Error getting meetings: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get meetings: {str(e)}',
        )
