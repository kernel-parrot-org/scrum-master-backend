import logging
from urllib.parse import urlencode

import httpx

from scrum_master.modules.auth.infrastructure.oauth.base_oauth_provider import \
    BaseOAuthProvider
from scrum_master.modules.auth.presentation.api.auth.schemas import \
    OAuthUserInfo

logger = logging.getLogger(__name__)


class GoogleOAuthProvider(BaseOAuthProvider):
    AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'
    USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = [
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.events',
            'openid',
        ]

    async def get_authorization_url(self, state: str | None = None) -> str:
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'access_type': 'offline',
            'prompt': 'consent',
        }
        if state:
            params['state'] = state
        return f'{self.AUTHORIZATION_URL}?{urlencode(params)}'

    async def exchange_code(self, code: str) -> str:
        async with httpx.AsyncClient() as client:
            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code',
            }

            response = await client.post(
                self.TOKEN_URL,
                data=payload,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            )

            if response.status_code != 200:
                error_data = (
                    response.json()
                    if response.headers.get('content-type', '').startswith('application/json')
                    else {'error': response.text}
                )
                raise ValueError(f'Google OAuth error: {error_data}')

            data = response.json()
            # Return both access and refresh token
            return {
                'access_token': data['access_token'],
                'refresh_token': data.get('refresh_token'),
                'expires_in': data.get('expires_in', 3600),
            }

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USERINFO_URL,
                headers={
                    'Authorization': f'Bearer {access_token}',
                },
            )
            response.raise_for_status()
            data = response.json()

            email = data.get('email')
            if not email:
                raise Exception('No email found in Google OAuth response')

            username = data.get('name') or email.split('@')[0]

            return OAuthUserInfo(
                oauth_id=str(data['id']),
                email=email,
                username=username,
                avatar_url=data.get('picture'),
            )