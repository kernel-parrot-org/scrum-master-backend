import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).parent.parent.parent.parent / '.env'


class GoogleMeetConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='GOOGLE_MEET_',
        env_file=ENV_FILE,
        extra='ignore',
    )

    chromedriver_path: str = os.getenv('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
    chrome_bin: Optional[str] = os.getenv('CHROME_BIN')
    headless: bool = True
    enable_logging: bool = True
    bot_name: str = 'Scrum Bot'
    auto_join: bool = True

    # Bot-specific settings
    min_record_time: int = 3600  # 1 hour in seconds
    max_waiting_time: int = 1800  # 30 minutes in seconds

    # File upload settings
    enable_file_upload: bool = False
    presigned_url_combined: Optional[str] = None
    presigned_url_audio: Optional[str] = None


class GoogleMeetModuleConfig(BaseSettings):
    google_meet: GoogleMeetConfig = GoogleMeetConfig()
