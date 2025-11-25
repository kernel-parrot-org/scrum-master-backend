import logging
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

import httpx
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import (APIRouter, Cookie, Depends, HTTPException, Request,
                     Response, status)
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from scrum_master.modules.auth.application.dtos import (LogoutDTO,
                                                        OAuthCallbackDTO,
                                                        RefreshTokenDTO)
from scrum_master.modules.auth.application.interactors.get_user import \
    GetUserInteractor
from scrum_master.modules.auth.application.interactors.google_oauth_login import \
    GoogleOAuthLoginInteractor
from scrum_master.modules.auth.application.interactors.logout import \
    LogoutInteractor
from scrum_master.modules.auth.application.interactors.refresh_token import \
    RefreshTokenInteractor
from scrum_master.modules.auth.infrastructure.oauth.google_oauth_provider import \
    GoogleOAuthProvider
from scrum_master.modules.auth.infrastructure.security.jwt_service import \
    JWTService
from scrum_master.modules.auth.presentation.api.auth.schemas import \
    UserResponse
from scrum_master.shared.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/api/v1/auth',
    tags=['Auth']
)
security = HTTPBearer()


@router.get('/google', summary='Redirect to Google OAuth')
@inject
async def google_login(
    google_provider: FromDishka[GoogleOAuthProvider],
) -> dict:
    auth_url = await google_provider.get_authorization_url()
    return {'authorization_url': auth_url}


@router.get('/google/callback', summary='Google OAuth callback')
@inject
async def google_callback(
    code: str,
    request: Request,
    interactor: FromDishka[GoogleOAuthLoginInteractor],
) -> RedirectResponse:
    try:
        dto = OAuthCallbackDTO(
            code=code,
            device_info=request.headers.get('user-agent'),
            ip_address=request.client.host if request.client else None,
        )

        login_result = await interactor(dto)

        redirect_params = {
            'access_token': login_result.access_token,
            'expires_in': str(login_result.expires_in),
        }
        logger.info(f'Google OAuth callback redirect: {redirect_params}')
        settings = get_settings()
        redirect_url = f'{settings.frontend_url}/auth/callback?{urlencode(redirect_params)}'

        redirect_response = RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND,
        )

        redirect_response.set_cookie(
            key='refresh_token',
            value=login_result.refresh_token,
            max_age=30 * 24 * 60 * 60,
            httponly=True,
            secure=False,
            samesite='lax',
            path='/',
        )

        return redirect_response

    except httpx.HTTPStatusError as e:
        logger.error(
            'Google OAuth HTTP error',
            extra={'status_code': e.response.status_code}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='OAuth provider error',
        )
    except Exception as e:
        logger.error(f'Google OAuth failed, {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='OAuth authentication failed',
        )

@router.post('/logout', summary='Logout and clear session')
@inject
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    response: Response,
    jwt_service: FromDishka[JWTService],
    interactor: FromDishka[LogoutInteractor],
) -> dict:
    try:
        token = credentials.credentials
        payload = jwt_service.verify_access_token(token)

        dto = LogoutDTO(session_id=payload.session_id)
        await interactor(dto)

        response.delete_cookie(
            key='refresh_token',
            path='/',
        )

        return {'message': 'Successfully logged out'}
    except ValueError as e:
        logger.error(f'{e}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token',
        )


@router.post('/refresh', summary='Refresh access token using HttpOnly cookie')
@inject
async def refresh_token(
    refresh_token: Annotated[str | None, Cookie()] = None,
    interactor: FromDishka[RefreshTokenInteractor] = None,
) -> dict:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token not found in cookies',
        )

    try:
        dto = RefreshTokenDTO(refresh_token=refresh_token)
        login_result = await interactor(dto)

        return {
            'access_token': login_result.access_token,
            'token_type': 'Bearer',
            'expires_in': login_result.expires_in,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get('/me', summary='Get current user', response_model=UserResponse)
@inject
async def get_me(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    interactor: FromDishka[GetUserInteractor],
) -> UserResponse:
    try:
        response_interactor = await interactor(user_access_token=credentials.credentials)
        return UserResponse.model_validate(response_interactor)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid authentication credentials',
            headers={'WWW-Authenticate': 'Bearer'},
        )
