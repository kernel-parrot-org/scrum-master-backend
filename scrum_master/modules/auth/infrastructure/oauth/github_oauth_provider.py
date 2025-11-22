import logging
from urllib.parse import urlencode

import httpx

from scrum_master.modules.auth.infrastructure.oauth.base_oauth_provider import BaseOAuthProvider
from scrum_master.modules.auth.presentation.api.auth.schemas import OAuthUserInfo

logger = logging.getLogger(__name__)

class GithubOauthProvider(BaseOAuthProvider):
    AUTHORIZATION_URL = 'https://github.com/login/oauth/authorize'
    TOKEN_URL = 'https://github.com/login/oauth/access_token'
    USERINFO_URL = 'https://api.github.com/user'

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = ['read:user', 'user:email', 'repo']

    async def get_authorization_url(self, state: str | None = None) -> str:
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scopes),
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
            }

            response = await client.post(
                self.TOKEN_URL,
                data=payload,
                headers={
                    'Accept': 'application/vnd.github+json',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            )

            if response.status_code != 200:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {'error': response.text}
                raise ValueError(f'GitHub OAuth error: {error_data}')


            data = response.json()
            logger.info(f'Github data: {data}')
            return data['access_token']

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USERINFO_URL,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/vnd.github+json',
                },
            )
            logger.info(access_token)
            response.raise_for_status()
            data = response.json()

            email = data.get('email')

            if not email:
                emails_response = await client.get(
                    'https://api.github.com/user/emails',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Accept': 'application/vnd.github+json',
                    },
                )
                emails_response.raise_for_status()
                emails = emails_response.json()

                for email_obj in emails:
                    if email_obj.get('primary') and email_obj.get('verified'):
                        email = email_obj['email']
                        break

                if not email:
                    for email_obj in emails:
                        if email_obj.get('verified'):
                            email = email_obj['email']
                            break

            if not email:
                raise Exception('No email found')

            return OAuthUserInfo(
                oauth_id=str(data['id']),
                email=email,
                username=data.get('login') or data.get('name'),
                avatar_url=data.get('avatar_url'),
            )


