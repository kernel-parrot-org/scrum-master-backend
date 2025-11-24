
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='TELEGRAM_',
    )
    bot_token: SecretStr = SecretStr('')
    chat_id: str = '0'


class GoogleConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='GOOGLE_',
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
    )
    token: SecretStr = SecretStr('')
    database_id: str = ''
    page_id: str = ''


class Settings(BaseSettings):
    telegram: TelegramConfig = TelegramConfig()
    google: GoogleConfig = GoogleConfig()
    audio: AudioConfig = AudioConfig()
    notion: NotionConfig = NotionConfig()

    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=False,
    )


settings = Settings()
