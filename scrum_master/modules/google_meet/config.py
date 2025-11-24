from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).parent.parent.parent.parent / '.env'


class GoogleMeetConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='GOOGLE_MEET_',
        env_file=ENV_FILE,
        extra='ignore',
    )

    chromedriver_path: str = '/usr/local/bin/chromedriver'
    headless: bool = True
    enable_logging: bool = True
    bot_name: str = 'Scrum Bot'
    auto_join: bool = True


class GoogleMeetModuleConfig(BaseSettings):
    google_meet: GoogleMeetConfig = GoogleMeetConfig()
