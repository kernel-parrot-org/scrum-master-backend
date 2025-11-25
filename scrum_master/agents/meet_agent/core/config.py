from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from scrum_master.shared.config.base import JiraConfig

ENV_FILE = Path(__file__).parent.parent.parent.parent / '.env'


class TelegramConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='TELEGRAM_',
        env_file=ENV_FILE,
        env_file_encoding='utf-8',
        extra='ignore',
    )
    bot_token: SecretStr = SecretStr('')
    chat_id: str = '0'


class GoogleConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='GOOGLE_',
        env_file=ENV_FILE,
        env_file_encoding='utf-8',
        extra='ignore',
    )
    genai_use_vertexai: bool = False
    api_key: SecretStr = SecretStr('')
    application_credentials: str = ''
    gcs_bucket_name: str = ''
    project: str = ''
    location: str = 'us-central1'


class AudioConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='AUDIO_',
        env_file=ENV_FILE,
        env_file_encoding='utf-8',
        extra='ignore',
    )
    max_upload_size: int = 104857600
    upload_dir: str = 'data/uploads'
    allowed_extensions: set[str] = {
        '.mp3',
        '.wav',
        '.flac',
        '.ogg',
        '.webm',
        '.m4a',
        '.mp4',
    }


class NotionConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='NOTION_',
        env_file=ENV_FILE,
        env_file_encoding='utf-8',
        extra='ignore',
    )
    token: SecretStr = SecretStr('')
    database_id: str = ''
    page_id: str = ''


class MeetAgentConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    telegram: TelegramConfig = TelegramConfig()
    google: GoogleConfig = GoogleConfig()
    audio: AudioConfig = AudioConfig()
    notion: NotionConfig = NotionConfig()
    jira: JiraConfig = JiraConfig()


settings = MeetAgentConfig()
