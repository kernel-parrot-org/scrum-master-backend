import logging

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, status

from scrum_master.modules.google_meet.application.dtos import \
    ConnectToMeetingRequest as ConnectRequest
from scrum_master.modules.google_meet.application.interactors.connect_to_meet import \
    ConnectToMeetInteractor
from scrum_master.modules.google_meet.presentation.api.meet.schemas import (
    ConnectToMeetingRequest, MeetingResponse)

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1/meet', tags=['Google Meet'])


@router.post('/connect', summary='Connect to Google Meet', response_model=MeetingResponse)
@inject
async def connect_to_meeting(
    request: ConnectToMeetingRequest,
    interactor: FromDishka[ConnectToMeetInteractor],
) -> MeetingResponse:
    try:
        logger.info(f'Connecting to meeting: {request.meet_url}')

        dto = ConnectRequest(
            meet_url=request.meet_url,
            bot_name=request.bot_name,
            min_record_time=request.min_record_time,
            max_waiting_time=request.max_waiting_time,
            presigned_url_combined=request.presigned_url_combined,
            presigned_url_audio=request.presigned_url_audio,
        )

        result = await interactor.execute(dto)
        return result

    except Exception as e:
        logger.error(f'Error connecting to meeting: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to connect to meeting: {str(e)}',
        )
