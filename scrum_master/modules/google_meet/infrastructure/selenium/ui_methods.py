import logging
import time
from typing import Any

from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)


class GoogleMeetUIException(Exception):
    pass


class GoogleMeetNotFoundException(GoogleMeetUIException):
    pass


class GoogleMeetJoinTimeoutException(GoogleMeetUIException):
    pass


class GoogleMeetUIMethods:
    def __init__(self, driver: WebDriver, wait_timeout: int = 60):
        self.driver = driver
        self.wait_timeout = wait_timeout
        self.wait = WebDriverWait(driver, wait_timeout)

    def find_element_by_selector(self, selector_type: Any, selector: str) -> Any:
        """Безопасный поиск элемента без исключений"""
        try:
            return self.driver.find_element(selector_type, selector)
        except NoSuchElementException:
            return None
        except Exception as e:
            logger.warning(f'Unknown error in find_element_by_selector: {type(e).__name__}')
            return None

    def click_element_forcefully(self, element: Any) -> None:
        """Клик через JavaScript для обхода блокировок"""
        try:
            self.driver.execute_script('arguments[0].click();', element)
        except Exception as e:
            logger.error(f'Failed to click element forcefully: {e}')
            raise

    def click_others_may_see_your_meeting_differently_button(self) -> None:
        """Закрывает модальное окно 'Got it'"""
        got_it_button = self.find_element_by_selector(
            By.XPATH, '//button[.//span[text()="Got it"]]'
        )
        if got_it_button:
            logger.info('Clicking "Got it" button to dismiss modal')
            try:
                self.click_element_forcefully(got_it_button)
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f'Could not click "Got it" button: {e}')

    def click_this_meeting_is_being_recorded_join_now_button(self) -> None:
        """Нажимает 'Join now' если встреча записывается"""
        recording_join_button = self.find_element_by_selector(
            By.XPATH, '//button[.//span[text()="Join now"]]'
        )
        if recording_join_button:
            logger.info('Clicking "Join now" for recording notification')
            try:
                recording_join_button.click()
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f'Could not click recording join button: {e}')

    def handle_blocking_elements(self) -> None:
        """Обрабатывает все блокирующие модальные окна"""
        self.click_others_may_see_your_meeting_differently_button()
        self.click_this_meeting_is_being_recorded_join_now_button()

    def navigate_to_meeting(self, meet_url: str) -> None:
        logger.info(f'Navigating to meeting: {meet_url}')
        try:
            self.driver.get(meet_url)
            time.sleep(2)
        except WebDriverException as e:
            logger.error(f'Failed to navigate to meeting: {e}')
            raise GoogleMeetUIException(f'Failed to navigate: {str(e)}')

    def disable_microphone_and_camera(self) -> None:
        logger.info('Disabling microphone and camera')

        time.sleep(2)

        mic_selectors = [
            'div[aria-label="Turn off microphone"]',
            'button[aria-label="Turn off microphone"]',
            'div[aria-label*="microphone"]',
        ]

        for selector in mic_selectors:
            try:
                mic_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                self._safe_click(mic_button)
                logger.info('Successfully disabled microphone')
                time.sleep(0.5)
                break
            except (NoSuchElementException, WebDriverException):
                continue
        else:
            logger.warning('Microphone button not found or already disabled')

        camera_selectors = [
            'div[aria-label="Turn off camera"]',
            'button[aria-label="Turn off camera"]',
            'div[aria-label*="camera"]',
        ]

        for selector in camera_selectors:
            try:
                camera_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                self._safe_click(camera_button)
                logger.info('Successfully disabled camera')
                time.sleep(0.5)
                break
            except (NoSuchElementException, WebDriverException):
                continue
        else:
            logger.warning('Camera button not found or already disabled')

    def enter_display_name(self, name: str) -> None:
        logger.info(f'Entering display name: {name}')

        name_selectors = [
            'input[type="text"][aria-label="Your name"]',
            'input[aria-label="Your name"]',
            'input[placeholder*="name" i]',
            'input[type="text"]',
        ]

        for attempt in range(5):
            for selector in name_selectors:
                try:
                    name_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if name_input.is_displayed() and name_input.is_enabled():
                        name_input.clear()
                        name_input.send_keys(name)
                        logger.info('Successfully entered display name')
                        time.sleep(0.5)
                        return
                except (NoSuchElementException, WebDriverException):
                    continue

            time.sleep(1)

        logger.warning('Could not enter display name - field not found or not interactable')

    def click_join_button(self) -> None:
        logger.info('Clicking join button')

        time.sleep(2)

        join_button_selectors = [
            '//button[.//span[text()="Join now"]]',
            '//button[.//span[text()="Ask to join"]]',
            '//button[.//span[text()="Join the call now"]]',
            '//span[text()="Join now"]',
            '//span[text()="Ask to join"]',
            '//button[contains(., "Join")]',
            '//button[@aria-label*="Join"]',
        ]

        for attempt in range(10):
            for selector in join_button_selectors:
                try:
                    button = self.driver.find_element(By.XPATH, selector)
                    if button.is_displayed() and button.is_enabled():
                        self._safe_click(button)
                        logger.info('Successfully clicked join button')
                        time.sleep(3)
                        return
                except (NoSuchElementException, WebDriverException) as e:
                    continue

            logger.info(f'Join button not found, attempt {attempt + 1}/10, waiting...')
            time.sleep(2)

        raise GoogleMeetJoinTimeoutException('Could not find join button after 10 attempts')

    def _safe_click(self, element: Any) -> None:
        try:
            element.click()
        except WebDriverException:
            try:
                self.driver.execute_script('arguments[0].click();', element)
            except WebDriverException as e:
                logger.error(f'Failed to click element: {e}')
                raise

    def wait_for_meeting_to_load(self) -> None:
        logger.info('Waiting for meeting to load')
        try:
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div[data-meeting-title]')
                )
            )
            logger.info('Meeting loaded successfully')
        except TimeoutException:
            logger.warning('Meeting title not found, continuing anyway')

    def check_if_meeting_exists(self) -> bool:
        try:
            error_indicators = [
                '//h1[contains(text(), "can\'t find")]',
                '//h1[contains(text(), "Video call ended")]',
                '//div[contains(text(), "invalid")]',
            ]

            for indicator in error_indicators:
                try:
                    self.driver.find_element(By.XPATH, indicator)
                    return False
                except NoSuchElementException:
                    continue

            return True
        except Exception as e:
            logger.error(f'Error checking if meeting exists: {e}')
            return False

    def attempt_to_join_meeting(self, meet_url: str, bot_name: str) -> None:
        try:
            self.navigate_to_meeting(meet_url)

            if not self.check_if_meeting_exists():
                raise GoogleMeetNotFoundException('Meeting not found or invalid')

            time.sleep(3)

            logger.info('Disabling media inputs...')
            self.disable_microphone_and_camera()

            time.sleep(1)

            logger.info('Entering display name...')
            self.enter_display_name(bot_name)

            time.sleep(1)

            logger.info('Clicking join button...')
            self.click_join_button()

            logger.info('Waiting for meeting to load...')
            self.wait_for_meeting_to_load()

            logger.info('Successfully joined the meeting')

        except GoogleMeetUIException:
            raise
        except Exception as e:
            logger.error(f'Unexpected error during join attempt: {e}')
            raise GoogleMeetUIException(f'Failed to join meeting: {str(e)}')

    def leave_meeting(self) -> None:
        logger.info('Leaving meeting')
        try:
            leave_button_selectors = [
                '//button[@aria-label="Leave call"]',
                '//button[contains(., "Leave")]',
                '//span[contains(text(), "Leave call")]',
            ]

            for selector in leave_button_selectors:
                try:
                    button = self.driver.find_element(By.XPATH, selector)
                    self._safe_click(button)
                    logger.info('Successfully left the meeting')
                    return
                except NoSuchElementException:
                    continue

            logger.warning('Leave button not found, closing driver')

        except Exception as e:
            logger.error(f'Error leaving meeting: {e}')
