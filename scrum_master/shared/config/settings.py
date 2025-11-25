from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from scrum_master.shared.config.base import (GCSConfig, JiraConfig, JWTConfig,
                                             PostgresConfig, RedisConfig)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    postgres: PostgresConfig = PostgresConfig()
    redis: RedisConfig = RedisConfig()
    jwt: JWTConfig = JWTConfig()
    jira: JiraConfig = JiraConfig()
    gcs: GCSConfig = GCSConfig()

    app_name: str = 'Scrum Master'
    environment: str = 'development'
    debug: bool = False
    log_level: str = 'INFO'
    frontend_url: str = 'http://localhost:3000'
    secret_key: SecretStr = SecretStr('')


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
