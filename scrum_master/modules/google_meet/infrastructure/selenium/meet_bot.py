"""Google Meet Bot implementation - Clean version."""
import json
import logging
import os
import platform
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

import requests
from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException,
                                        TimeoutException, WebDriverException)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from .random_mouse import random_mouse_movements
from .utils import audio_file_path, create_tar_archive, save_screenshot


class GoogleMeetUIException(Exception):
    """Exception raised for Google Meet UI errors."""
    pass


class JoinGoogleMeet:
    """Google Meet bot for joining meetings and recording audio."""

    def __init__(
        self,
        meetlink: str,
        start_time_utc: datetime | None = None,
        end_time_utc: datetime | None = None,
        min_record_time: int = 3600,
        bot_name: str = "Google Bot",
        presigned_url_combined: str | None = None,
        presigned_url_audio: str | None = None,
        max_waiting_time: int = 1800,
        logger: logging.Logger | None = None,
    ):
        """Initialize Google Meet bot."""
        self.meetlink = meetlink
        self.start_time_utc = start_time_utc
        self.end_time_utc = end_time_utc
        self.min_record_time = min_record_time
        self.bot_name = bot_name
        self.browser = None
        self.recording_started = False
        self.recording_start_time = None
        self.stop_event = Event()
        self.recording_process = None
        self.presigned_url_combined = presigned_url_combined
        self.presigned_url_audio = presigned_url_audio
        self.id = str(uuid.uuid4())
        self.output_file = f"out/{self.id}"
        self.event_start_time = None
        self.need_retry = False
        self.thread_start_time = None
        self.max_waiting_time = max_waiting_time
        self.session_ended = False
        self.logger = logger or logging.getLogger(__name__)

        # Create output directory
        Path("out").mkdir(exist_ok=True)

    def setup_browser(self) -> None:
        """Setup Chrome browser."""
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--start-maximized')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-infobars')
        options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36')
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-application-cache")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--use-fake-device-for-media-stream")
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument(f"user-data-dir=/tmp/CueMeet{self.id}")

        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 0,
            "profile.default_content_setting_values.geolocation": 0,
            "profile.default_content_setting_values.notifications": 0,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
        })

        try:
            self.logger.info("Installing ChromeDriver...")
            self.browser = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            self.browser.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
            })
            self.browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.info("Browser launched successfully")
        except Exception as e:
            self.logger.error(f"Failed to launch browser: {e}", exc_info=True)
            raise GoogleMeetUIException(f"Failed to launch browser: {e}")

    def navigate_to_meeting(self) -> None:
        """Navigate to Google Meet."""
        if not hasattr(self, '_visited_homepage'):
            self.logger.info("Visiting Google Meet homepage...")
            try:
                self.browser.get("https://meet.google.com/")
                time.sleep(2)
                self.browser.execute_script("""
                    localStorage.setItem('meet_visited', 'true');
                    localStorage.setItem('meet_prefs_set', 'true');
                """)
                self._visited_homepage = True
            except Exception as e:
                self.logger.warning(f"Failed to visit homepage: {e}")

        self.logger.info(f"Navigating to: {self.meetlink}")

        for attempt in range(3):
            try:
                self.browser.get(self.meetlink)
                WebDriverWait(self.browser, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )

                current_url = self.browser.current_url
                self.logger.info(f"Current URL: {current_url}")

                if "workspace.google.com" in current_url or "accounts.google.com" in current_url:
                    self.logger.warning(f"Redirected to {current_url}")
                    if attempt < 2:
                        time.sleep(3)
                        continue

                self.logger.info("Navigation successful")
                break
            except Exception as e:
                self.logger.error(f"Navigation error: {e}")
                if attempt < 2:
                    time.sleep(3)
                    continue
                else:
                    raise GoogleMeetUIException(f"Navigation failed: {e}")

        random_mouse_movements(self.browser, self.logger, duration_seconds=5)

    def join_meeting(self) -> None:
        """Join the meeting."""
        self.logger.info("Joining meeting...")
        time.sleep(3)

        # Disable mic
        try:
            mic_selectors = [
                '//div[@aria-label="Turn off microphone"]',
                '//button[@aria-label="Turn off microphone"]',
            ]
            for selector in mic_selectors:
                try:
                    mic_button = WebDriverWait(self.browser, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    mic_button.click()
                    self.logger.info("Microphone disabled")
                    break
                except:
                    continue
        except Exception as e:
            self.logger.warning(f"Mic disable issue: {e}")

        # Disable camera
        try:
            camera_selectors = [
                '//div[@aria-label="Turn off camera"]',
                '//button[@aria-label="Turn off camera"]',
            ]
            for selector in camera_selectors:
                try:
                    camera_button = WebDriverWait(self.browser, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    camera_button.click()
                    self.logger.info("Camera disabled")
                    break
                except:
                    continue
        except Exception as e:
            self.logger.warning(f"Camera disable issue: {e}")

        time.sleep(2)

        # Enter name
        try:
            name_selectors = [
                "//input[@placeholder='Your name']",
                "//input[@type='text' and @aria-label]",
            ]
            for selector in name_selectors:
                try:
                    name_input = WebDriverWait(self.browser, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    name_input.clear()
                    name_input.send_keys(self.bot_name)
                    self.logger.info(f"Entered bot name: {self.bot_name}")
                    break
                except:
                    continue
        except Exception as e:
            self.logger.warning(f"Name input issue: {e}")

        time.sleep(1)

        # Click join button
        try:
            join_selectors = [
                '//span[contains(text(), "Ask to join")]//parent::button',
                '//button[contains(., "Ask to join")]',
                '//span[contains(text(), "Join now")]//parent::button',
                '//button[contains(., "Join now")]',
            ]
            for selector in join_selectors:
                try:
                    join_button = WebDriverWait(self.browser, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    join_button.click()
                    self.logger.info("Clicked join button")
                    break
                except:
                    continue
        except Exception as e:
            self.logger.error(f"Join button error: {e}")
            screenshot_path = save_screenshot(self.browser, "join_error")
            if screenshot_path:
                self.logger.info(f"Screenshot: {screenshot_path}")

        time.sleep(4)

    def check_admission(self) -> None:
        """Check if admitted."""
        try:
            admitted = WebDriverWait(self.browser, 5).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "u6vdEc")]'))
            )
            if admitted and not self.recording_started:
                self.logger.info("Admitted! Starting recording...")
                self.start_recording()
                self.recording_started = True
        except TimeoutException:
            pass

    def start_recording(self) -> None:
        """Start FFmpeg recording."""
        self.logger.info("Starting recording...")
        output_audio_file = f'{self.output_file}.opus'

        if platform.system() == 'Darwin':
            command = ["ffmpeg", "-f", "avfoundation", "-i", ":0", "-acodec", "libopus", "-b:a", "128k", "-ac", "1", "-ar", "48000", output_audio_file]
        elif platform.system() == 'Linux':
            command = ["ffmpeg", "-f", "pulse", "-i", "virtual-sink.monitor", "-acodec", "libopus", "-b:a", "256k", "-ac", "1", "-ar", "48000", output_audio_file]
        else:
            self.logger.error("Unsupported OS")
            return

        try:
            self.event_start_time = datetime.now(timezone.utc)
            self.recording_process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.recording_started = True
            self.recording_start_time = time.perf_counter()
            self.logger.info(f"Recording started: {output_audio_file}")
        except Exception as e:
            self.logger.error(f"Recording error: {e}")

    def stop_recording(self) -> None:
        """Stop recording."""
        if self.recording_started and self.recording_process:
            self.logger.info("Stopping recording...")
            self.recording_process.terminate()
            try:
                self.recording_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.recording_process.kill()
            self.logger.info("Recording stopped")

    def end_session(self) -> None:
        """End session."""
        if self.session_ended:
            return

        self.session_ended = True
        self.logger.info("Ending session...")

        try:
            time.sleep(5)

            if self.browser:
                try:
                    self.browser.quit()
                    self.logger.info("Browser closed")
                except:
                    pass

            self.stop_event.set()
            if self.recording_started:
                self.stop_recording()
                if self.presigned_url_audio:
                    self.upload_files()
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
        finally:
            self.logger.info("Session ended")

    def upload_files(self) -> None:
        """Upload files."""
        try:
            if self.presigned_url_audio:
                full_path = audio_file_path(f"{self.output_file}.opus")
                if full_path and os.path.exists(full_path):
                    with open(full_path, 'rb') as file:
                        response = requests.put(self.presigned_url_audio, data=file, headers={'Content-Type': 'audio/opus'})
                        response.raise_for_status()
                    self.logger.info("Audio uploaded")
        except Exception as e:
            self.logger.error(f"Upload error: {e}")

    def monitor_meeting(self) -> None:
        """Monitor meeting."""
        self.logger.info("Monitoring meeting...")
        start_time = time.perf_counter()

        while not self.stop_event.is_set():
            current_time = time.perf_counter()
            elapsed = current_time - start_time

            if not self.recording_started:
                if elapsed > self.max_waiting_time:
                    self.logger.info(f"Max waiting time ({self.max_waiting_time}s) exceeded")
                    break
            else:
                recording_elapsed = current_time - self.recording_start_time
                if recording_elapsed > self.min_record_time:
                    self.logger.info(f"Min recording time ({self.min_record_time}s) reached")
                    break

            try:
                self.check_admission()
            except WebDriverException:
                self.logger.error("Browser closed")
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")

            time.sleep(5)

    def run(self) -> None:
        """Main run method."""
        try:
            self.logger.info("=== STARTING GOOGLE MEET BOT ===")
            self.setup_browser()
            self.navigate_to_meeting()
            self.join_meeting()
            self.monitor_meeting()
        except Exception as e:
            self.logger.error(f"Bot error: {e}", exc_info=True)
            raise GoogleMeetUIException(f"Bot error: {e}")
        finally:
            self.logger.info("Finalizing...")
            self.end_session()

        self.logger.info("=== BOT COMPLETED ===")