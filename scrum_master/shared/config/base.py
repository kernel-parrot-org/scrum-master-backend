from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class JiraConfig(BaseSettings):
    url: str
    user: str
    token: str
    project: str


class PostgresConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='POSTGRES_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    host: str = 'localhost'
    port: int = 5432
    user: str = 'postgres'
    password: SecretStr = SecretStr('postgres')
    database: str = 'scrum_master'

    @property
    def url(self) -> str:
        # Use 'postgres' as host when in Docker (detected by /.dockerenv)
        import os
        db_host = 'postgres' if os.path.exists('/.dockerenv') else self.host
        return f'postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}@{db_host}:{self.port}/{self.database}'


class JWTConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='JWT_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    secret_key: SecretStr = SecretStr('secret')
    algorithm: str = 'HS256'
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30


class JiraConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='JIRA_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    api_url: str = ''
    api_token: SecretStr = SecretStr('')
    email: str = ''
    project_key: str = ''


class GCSConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='GCS_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    bucket_name: str = ''
    credentials_path: str = ''
    project_id: str = ''

class RedisConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='REDIS_',
        env_file='.env',
        extra='ignore',
    )
    host: str = 'localhost'
    port: int = 6379
    password: str | None = None
    db: int = 0

    @property
    def url(self) -> str:
        if self.password:
            return f'redis://:{self.password}@{self.host}:{self.port}/{self.db}'
        return f'redis://{self.host}:{self.port}/{self.db}'
