import logging
from typing import Annotated

import httpx
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from scrum_master.modules.auth.infrastructure.security.jwt_service import JWTService
from scrum_master.modules.google_meet.infrastructure.bot_status_storage import (
    BotStatus,
    get_bot_status_storage,
)
from scrum_master.modules.google_meet.presentation.api.meet.schemas import (
    BotStatusResponse,
    CreateTasksCallbackRequest,
    TriggerBotRequest,
    TriggerBotResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1/meet', tags=['Google Meet'])
security = HTTPBearer()



@router.post('/trigger', summary='Trigger bot to join Google Meet', response_model=TriggerBotResponse)
@inject
async def trigger_bot(
    request: TriggerBotRequest,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
) -> TriggerBotResponse:
    try:
        token = credentials.credentials
        payload = jwt_service.verify_access_token(token)
        user_id = payload.sub

        logger.info(f'User {user_id} triggering bot for meeting: {request.meet_url}')

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

            # Сохраняем статус бота в storage
            storage = get_bot_status_storage()
            await storage.create(bot_data['bot_id'], user_id, BotStatus.STARTING)

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


@router.get('/status/{bot_id}', summary='Get bot status for polling', response_model=BotStatusResponse)
@inject
async def get_bot_status(
    bot_id: str,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
) -> BotStatusResponse:
    """
    Эндпоинт для polling статуса бота.

    Фронтенд должен вызывать этот эндпоинт каждые 2-3 секунды для получения актуального статуса.

    Статусы:
    1. starting
    2. running - бот подключился к встрече
    3. transcribing - идет транскрипция аудио
    4. analyzing_meeting - анализ встречи
    5. creating_tasks - создание задач
    6. done - процесс завершен
    7. error - произошла ошибка
    """
    try:
        token = credentials.credentials
        payload = jwt_service.verify_access_token(token)
        user_id = payload.sub

        storage = get_bot_status_storage()
        bot_info = await storage.get(bot_id)

        if not bot_info:
            # Пробуем получить статус из внешнего сервиса
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(
                        f'http://host.docker.internal:8001/api/v1/bots/{bot_id}'
                    )
                    response.raise_for_status()
                    external_data = response.json()

                    # Маппим внешний статус на наш
                    external_status = external_data.get('status', '')
                    if external_status == 'starting':
                        internal_status = BotStatus.STARTING
                    elif external_status == 'running':
                        internal_status = BotStatus.RUNNING
                    else:
                        internal_status = BotStatus.STARTING

                    # Создаем запись в storage
                    bot_info = await storage.create(bot_id, user_id, internal_status)

                except httpx.HTTPError:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f'Bot {bot_id} not found'
                    )

        # Проверяем доступ пользователя к боту
        if bot_info.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Access denied to this bot'
            )

        return BotStatusResponse(**bot_info.to_dict())

    except ValueError as e:
        logger.error(f'Invalid token: {e}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid authentication credentials'
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Error getting bot status: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get bot status: {str(e)}'
        )


@router.post('/callback/update-status', summary='Callback to update bot status from external service')
async def update_bot_status_callback(request: CreateTasksCallbackRequest):
    """
    Callback эндпоинт для обновления статуса бота.

    Этот эндпоинт вызывается вашим внешним сервисом (http://host.docker.internal:8001)
    когда статус бота меняется или когда завершается обработка задач.
    """
    try:
        storage = get_bot_status_storage()

        # Обновляем статус на DONE с результатами
        await storage.update_status(
            request.bot_id,
            BotStatus.DONE,
            session_id=request.session_id,
            result_data=request.result_data
        )

        logger.info(f'Bot {request.bot_id} status updated to DONE via callback')

        return {'success': True, 'message': 'Status updated successfully'}

    except Exception as e:
        logger.error(f'Error updating bot status via callback: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to update status: {str(e)}'
        )
