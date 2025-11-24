import logging
import os
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

from scrum_master.modules.google_meet.config import GoogleMeetConfig
from scrum_master.modules.google_meet.infrastructure.selenium.ui_methods import (
    GoogleMeetUIMethods,
    GoogleMeetUIException,
)

logger = logging.getLogger(__name__)


class GoogleMeetAdapter:
    def __init__(self, config: GoogleMeetConfig):
        self.config = config
        self.driver: WebDriver | None = None
        self.ui_methods: GoogleMeetUIMethods | None = None

    def _create_chrome_options(self) -> ChromeOptions:
        options = ChromeOptions()

        chrome_bin = os.getenv('CHROME_BIN')
        if chrome_bin:
            options.binary_location = chrome_bin
            logger.info(f'Using Chrome binary at: {chrome_bin}')

        if self.config.headless:
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-gpu')

        options.add_argument('--use-fake-ui-for-media-stream')
        options.add_argument('--use-fake-device-for-media-stream')

        prefs = {
            'profile.default_content_setting_values.media_stream_mic': 1,
            'profile.default_content_setting_values.media_stream_camera': 1,
            'profile.default_content_setting_values.notifications': 2,
        }
        options.add_experimental_option('prefs', prefs)
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)

        return options

    def initialize_driver(self) -> None:
        if self.driver:
            logger.warning('Driver already initialized')
            return

        try:
            logger.info('Initializing Chrome driver')
            options = self._create_chrome_options()

            chromedriver_path = os.getenv('CHROMEDRIVER_PATH')
            if chromedriver_path and os.path.exists(chromedriver_path):
                logger.info(f'Using ChromeDriver at: {chromedriver_path}')
                service = ChromeService(chromedriver_path)
            else:
                chrome_type = ChromeType.CHROMIUM if os.getenv('CHROME_BIN') else ChromeType.GOOGLE
                logger.info(f'Installing ChromeDriver for {chrome_type}')
                service = ChromeService(
                    ChromeDriverManager(chrome_type=chrome_type).install()
                )

            self.driver = webdriver.Chrome(
                service=service,
                options=options,
            )

            self.driver.execute_cdp_cmd(
                'Page.addScriptToEvaluateOnNewDocument',
                {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    '''
                },
            )

            self.ui_methods = GoogleMeetUIMethods(self.driver)

            logger.info('Chrome driver initialized successfully')

        except Exception as e:
            logger.error(f'Failed to initialize driver: {e}')
            self.cleanup()
            raise GoogleMeetUIException(f'Failed to initialize driver: {str(e)}')

    def connect_to_meeting(self, meet_url: str, bot_name: str | None = None) -> None:
        if not self.driver or not self.ui_methods:
            raise GoogleMeetUIException('Driver not initialized')

        display_name = bot_name or self.config.bot_name

        try:
            logger.info(f'Connecting to meeting: {meet_url}')
            self.ui_methods.attempt_to_join_meeting(meet_url, display_name)
            logger.info('Successfully connected to meeting')

        except GoogleMeetUIException:
            raise
        except Exception as e:
            logger.error(f'Unexpected error connecting to meeting: {e}')
            raise GoogleMeetUIException(f'Failed to connect: {str(e)}')

    def disconnect_from_meeting(self) -> None:
        if not self.ui_methods:
            logger.warning('UI methods not initialized')
            return

        try:
            logger.info('Disconnecting from meeting')
            self.ui_methods.leave_meeting()
            logger.info('Successfully disconnected from meeting')

        except Exception as e:
            logger.error(f'Error disconnecting from meeting: {e}')

    def cleanup(self) -> None:
        if self.driver:
            try:
                logger.info('Cleaning up driver')
                self.driver.quit()
                logger.info('Driver cleaned up successfully')
            except Exception as e:
                logger.error(f'Error cleaning up driver: {e}')
            finally:
                self.driver = None
                self.ui_methods = None

    def __enter__(self) -> 'GoogleMeetAdapter':
        self.initialize_driver()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.cleanup()
