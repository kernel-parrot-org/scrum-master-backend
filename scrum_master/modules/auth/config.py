from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).parent.parent.parent.parent / '.env'

class GoogleOAuthConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='GOOGLE_OAUTH_',
        env_file=ENV_FILE,
        extra='ignore',
    )

    client_id: str = ''
    client_secret: str = ''
    redirect_uri: str = ''


class AuthModuleConfig(BaseSettings):
    google: GoogleOAuthConfig = GoogleOAuthConfig()
