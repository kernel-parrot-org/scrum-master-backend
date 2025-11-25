"""Google Meet Bot implementation - Robust version with aggressive navigation."""
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

from .random_mouse import random_mouse_movements
from .utils import audio_file_path, create_tar_archive, save_screenshot


class GoogleMeetUIException(Exception):
    pass


class JoinGoogleMeet:

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

        Path("out").mkdir(exist_ok=True)

    def setup_browser(self) -> None:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-application-cache')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--lang=en-US')
        options.add_argument('--accept-lang=en-US,en')
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--use-fake-device-for-media-stream")
        options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
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
            "intl.accept_languages": "en-US,en",
        })

        # Find Chrome binary
        chrome_paths = [
            os.environ.get('CHROME_BIN'),
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
        ]

        for chrome_path in chrome_paths:
            if chrome_path and os.path.exists(chrome_path):
                options.binary_location = chrome_path
                self.logger.info(f"Using Chrome binary: {chrome_path}")
                break

        driver_paths = [
            os.environ.get('CHROMEDRIVER_PATH'),
            "/usr/bin/chromedriver",
            "/usr/local/bin/chromedriver",
            "/usr/lib/chromium-browser/chromedriver",
            "/snap/bin/chromium.chromedriver",
        ]

        driver_path = None
        for path in driver_paths:
            if path and os.path.exists(path):
                driver_path = path
                self.logger.info(f"Using ChromeDriver: {path}")
                break

        try:
            self.logger.info("Setting up ChromeDriver...")

            if driver_path:
                service = Service(executable_path=driver_path, log_path='/dev/null')
            else:
                self.logger.warning("ChromeDriver not found, using system chromedriver")
                service = Service(log_path='/dev/null')

            self.browser = webdriver.Chrome(
                service=service,
                options=options
            )

            self.browser.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            })
            self.browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.info("Browser launched successfully")
        except Exception as e:
            self.logger.error(f"Failed to launch browser: {e}", exc_info=True)
            raise GoogleMeetUIException(f"Failed to launch browser: {e}")

    def navigate_to_meeting(self) -> None:
        # First visit Google Meet homepage to set cookies
        if not hasattr(self, '_visited_homepage'):
            self.logger.info("First visiting Google Meet homepage to set cookies...")
            try:
                self.browser.get("https://meet.google.com/")
                time.sleep(2)
                # Set some localStorage flags that real users would have
                self.browser.execute_script("""
                    localStorage.setItem('meet_visited', 'true');
                    localStorage.setItem('meet_prefs_set', 'true');
                """)
                self._visited_homepage = True
                self.logger.info("Homepage visited, cookies set.")
            except Exception as e:
                self.logger.warning(f"Failed to visit homepage: {e}")
        
        self.logger.info(f"Navigating to Google Meet link: {self.meetlink}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.browser.get(self.meetlink)
                # Wait for page to load
                WebDriverWait(self.browser, 15).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                
                current_url = self.browser.current_url
                self.logger.info(f"Current URL after navigation: {current_url}")
                self.logger.info(f"Page title: {self.browser.title}")
                
                # Check if we were redirected away from meet.google.com
                if "workspace.google.com" in current_url or "accounts.google.com" in current_url:
                    self.logger.warning(f"Redirected to {current_url}, attempt {attempt + 1}/{max_retries}")
                    
                    # Try to bypass redirect by stopping page load and forcing navigation
                    try:
                        self.browser.execute_script("window.stop();")
                        time.sleep(1)
                    except:
                        pass
                    
                    if attempt < max_retries - 1:
                        self.logger.info("Retrying navigation in 3 seconds...")
                        time.sleep(3)
                        # Try with referer header
                        try:
                            self.browser.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                                'headers': {
                                    'Referer': 'https://meet.google.com/',
                                    'Accept-Language': 'en-US,en;q=0.9'
                                }
                            })
                        except:
                            pass
                        continue
                    else:
                        self.logger.error("Failed to reach meeting page after all retries. Trying to force navigation...")
                        # Last attempt: try direct navigation with JavaScript
                        self.browser.execute_script(f"window.location.replace('{self.meetlink}');")
                        time.sleep(5)
                        current_url = self.browser.current_url
                        if "meet.google.com" not in current_url or "workspace.google.com" in current_url:
                            self.logger.error(f"Still redirected to: {current_url}")
                            screenshot_path = save_screenshot(self.browser, "redirect_error")
                            if screenshot_path:
                                self.logger.info(f"Redirect error screenshot saved to: {screenshot_path}")
                            raise GoogleMeetUIException(f"Cannot join meeting - redirected to {current_url}")
                
                # Check for meeting-specific error messages (English + Russian)
                try:
                    error_messages = [
                        "This meeting hasn't started",
                        "This meeting code doesn't exist",
                        "You can't join this video call",
                        "Invalid meeting code",
                        "Встреча ещё не началась",
                        "Такого кода встречи не существует",
                        "Вы не можете подключиться",
                        "Неверный код встречи"
                    ]
                    page_text = self.browser.find_element(By.TAG_NAME, "body").text
                    for error_msg in error_messages:
                        if error_msg.lower() in page_text.lower():
                            self.logger.error(f"Meeting error detected: {error_msg}")
                            screenshot_path = save_screenshot(self.browser, "meeting_error")
                            if screenshot_path:
                                self.logger.info(f"Meeting error screenshot saved to: {screenshot_path}")
                            raise GoogleMeetUIException(f"Meeting error: {error_msg}")
                except NoSuchElementException:
                    pass
                
                self.logger.info("Successfully navigated to the Google Meet link.")
                break
                
            except GoogleMeetUIException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to navigate to the meeting link: {e}")
                screenshot_path = save_screenshot(self.browser, "navigation_error")
                if screenshot_path:
                    self.logger.info(f"Navigation error screenshot saved to: {screenshot_path}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                else:
                    raise GoogleMeetUIException(f"Navigation failed after {max_retries} attempts: {e}")
        
        random_mouse_movements(self.browser, self.logger, duration_seconds=10)

        # Try to close modal dialogs
        try:
            modal_selectors = [
                '//button[@jsname="IbE0S"]',
                '//button[contains(@aria-label, "Got it")]',
                '//button[contains(., "Got it")]',
                '//button[contains(., "Dismiss")]'
            ]
            modal_closed = False
            for selector in modal_selectors:
                try:
                    modals = self.browser.find_elements(By.XPATH, selector)
                    if modals:
                        modals[0].click()
                        self.logger.info(f"Closed modal dialog using selector: {selector}")
                        modal_closed = True
                        break
                except:
                    continue
            if not modal_closed:
                self.logger.info("No modal dialog found to close.")
        except Exception as e:
            self.logger.warning(f"Modal handling issue (may not exist): {e}")

    def join_meeting(self) -> None:
        # Verify we're on the meeting page
        current_url = self.browser.current_url
        if "meet.google.com" not in current_url:
            self.logger.error(f"Not on meet.google.com page. Current URL: {current_url}")
            # Try to navigate back to the meeting
            self.logger.info("Attempting to navigate back to meeting...")
            self.browser.get(self.meetlink)
            time.sleep(5)
            current_url = self.browser.current_url
            if "meet.google.com" not in current_url:
                self.logger.error(f"Still not on meeting page: {current_url}")
                screenshot_path = save_screenshot(self.browser, "wrong_page")
                if screenshot_path:
                    self.logger.info(f"Wrong page screenshot saved to: {screenshot_path}")
        
        self.logger.info("Attempting to disable microphone and camera.")
        time.sleep(3)
        
        # Try multiple selectors for mic button (English + Russian)
        try:
            mic_selectors = [
                '//div[@aria-label="Turn off microphone"]',
                '//button[@aria-label="Turn off microphone"]',
                '//div[@aria-label="Отключить микрофон"]',
                '//button[@aria-label="Отключить микрофон"]',
                '//div[contains(@aria-label, "microphone") and contains(@aria-label, "off")]//ancestor::button',
                '//div[contains(@aria-label, "микрофон")]//ancestor::button',
                '//div[@data-is-muted="false"]//ancestor::button'
            ]
            mic_clicked = False
            for selector in mic_selectors:
                try:
                    mic_button = WebDriverWait(self.browser, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    mic_button.click()
                    self.logger.info("Microphone disabled successfully.")
                    mic_clicked = True
                    break
                except:
                    continue
            if not mic_clicked:
                self.logger.warning("Could not find microphone button, it may already be disabled.")
        except Exception as e:
            self.logger.warning(f"Mic disable issue (may already be off): {e}")

        # Try multiple selectors for camera button (English + Russian)
        try:
            camera_selectors = [
                '//div[@aria-label="Turn off camera"]',
                '//button[@aria-label="Turn off camera"]',
                '//div[@aria-label="Отключить камеру"]',
                '//button[@aria-label="Отключить камеру"]',
                '//div[contains(@aria-label, "camera") and contains(@aria-label, "off")]//ancestor::button',
                '//div[contains(@aria-label, "камер")]//ancestor::button',
            ]
            camera_clicked = False
            for selector in camera_selectors:
                try:
                    camera_button = WebDriverWait(self.browser, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    camera_button.click()
                    self.logger.info("Camera disabled successfully.")
                    camera_clicked = True
                    break
                except:
                    continue
            if not camera_clicked:
                self.logger.warning("Could not find camera button, it may already be disabled.")
        except Exception as e:
            self.logger.warning(f"Camera disable issue (may already be off): {e}")
        
        time.sleep(2)
        
        # Try to enter name (English + Russian)
        try:
            name_selectors = [
                "//input[@placeholder='Your name']",
                "//input[@placeholder='Ваше имя']",
                "//input[@type='text' and @aria-label]",
                "//input[contains(@placeholder, 'name')]",
                "//input[contains(@placeholder, 'имя')]"
            ]
            name_entered = False
            for selector in name_selectors:
                try:
                    name_input = WebDriverWait(self.browser, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    name_input.clear()
                    name_input.send_keys(self.bot_name)
                    self.logger.info(f"Entered the bot name: {self.bot_name}")
                    name_entered = True
                    break
                except:
                    continue
            if not name_entered:
                self.logger.warning("Could not find name input field, may not be required.")
        except Exception as e:
            self.logger.warning(f"Name input issue: {e}")
        
        time.sleep(1)
        
        # Try to click join button (English + Russian)
        try:
            join_selectors = [
                '//span[contains(text(), "Ask to join")]//parent::button',
                '//button[contains(., "Ask to join")]',
                '//span[contains(text(), "Join now")]//parent::button',
                '//button[contains(., "Join now")]',
                '//span[contains(text(), "Попросить")]//parent::button',
                '//button[contains(., "Попросить")]',
                '//span[contains(text(), "Присоединиться")]//parent::button',
                '//button[contains(., "Присоединиться")]',
            ]
            join_clicked = False
            for selector in join_selectors:
                try:
                    join_button = WebDriverWait(self.browser, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    join_button.click()
                    self.logger.info("Clicked the join button successfully.")
                    join_clicked = True
                    break
                except:
                    continue
            if not join_clicked:
                self.logger.error("Failed to find and click join button with any selector.")
                screenshot_path = save_screenshot(self.browser, "join_button_not_found")
                if screenshot_path:
                    self.logger.info(f"Screenshot saved to: {screenshot_path}")
                # Log page title and current URL for debugging
                self.logger.info(f"Current URL: {self.browser.current_url}")
                self.logger.info(f"Page title: {self.browser.title}")
        except Exception as e:
            self.logger.error(f"Join button click error: {e}")
            screenshot_path = save_screenshot(self.browser, "join_error")
            if screenshot_path:
                self.logger.info(f"Error screenshot saved to: {screenshot_path}")
        time.sleep(4)

    def check_admission(self) -> None:
        try:
            # Check if admitted to the meeting
            admitted = WebDriverWait(self.browser, 5).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "u6vdEc")]'))
            )
            if admitted and not self.recording_started:
                self.logger.info("Admitted to the meeting. Starting recording...")
                self.start_recording()
                self.recording_started = True
        except TimeoutException:
            pass

    def start_recording(self) -> None:
        self.logger.info("Starting meeting audio recording with FFmpeg...")
        output_audio_file = f'{self.output_file}.opus'
        
        if platform.system() == 'Darwin':
            command = [
                "ffmpeg",
                "-f", "avfoundation",
                "-i", ":0",
                "-acodec", "libopus",
                "-b:a", "128k",
                "-ac", "1",  
                "-ar", "48000",
                "-y",
                output_audio_file
            ]
        elif platform.system() == 'Linux':  
            command = [
                "ffmpeg",
                "-f", "pulse",
                "-i", "virtual-sink.monitor",
                "-af", "aresample=async=1000",
                "-acodec", "libopus",
                "-application", "audio",
                "-b:a", "256k",
                "-vbr", "on",
                "-frame_duration", "60",
                "-ac", "1",
                "-ar", "48000",
                "-y",
                output_audio_file
            ]
        else:
            self.logger.error("Unsupported operating system for recording.")
            return

        try:
            self.logger.info(f"Executing FFmpeg command: {' '.join(command)}")
            
            self.event_start_time = datetime.now(timezone.utc)
            self.recording_process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.recording_started = True
            self.recording_start_time = time.perf_counter() 
            self.logger.info(f"Recording started. Output will be saved to {output_audio_file}")
        except Exception as e:
            self.logger.error(f"Error starting FFmpeg: {e}")

    def stop_recording(self) -> None:
        if self.recording_started and self.recording_process:
            self.logger.info("Stopping audio recording...")
            self.recording_process.terminate()
            try:
                self.recording_process.wait(timeout=10)
                self.logger.info("Recording stopped.")
            except subprocess.TimeoutExpired:
                self.logger.warning("Recording process did not terminate in time. Forcibly killing it.")
                self.recording_process.kill()
                self.logger.info("Recording process killed.")
        else:
            self.logger.info("No recording was started, nothing to stop.")

    def end_session(self) -> None:
        if self.session_ended:
            self.logger.info("Session has already been ended. Skipping end_session method call.")
            return
        
        self.session_ended = True
        self.logger.info("Ending the session...")
        try:
            time.sleep(5)

            if self.browser:
                try:
                    self.browser.quit()
                    self.logger.info("Browser closed.")
                except Exception as e:
                    self.logger.error(f"Failed to close browser: {e}")
                
            self.stop_event.set()
            if self.recording_started:
                self.stop_recording()
                if self.presigned_url_audio:
                    self.upload_files()
            else:
                self.logger.info("No recording was started during this session.")
        except Exception as e:
            self.logger.error(f"Error during session cleanup: {e}", exc_info=True)
        finally:
            self.logger.info("Session ended successfully.")

    def upload_files(self) -> None:
        try:
            if self.presigned_url_audio:
                full_path = audio_file_path(f"{self.output_file}.opus")
                if full_path and os.path.exists(full_path):
                    self.logger.info(f"Attempting to upload the Audio file from path: {full_path}")
                    try:
                        self.logger.info(f"Uploading {f'{self.output_file}.opus'} to pre-signed URL...")
                        with open(full_path, 'rb') as file:
                            response = requests.put(self.presigned_url_audio, data=file, headers={'Content-Type': 'audio/opus'})
                            response.raise_for_status()
                        self.logger.info("Audio file uploaded successfully.")
                    except Exception as e:
                        self.logger.error(f"Error uploading the Audio file: {e}")
                else:
                    self.logger.error(f"Audio file does not exist at: {full_path}")
            else:
                self.logger.info("No pre-signed Audio URL provided or no Audio file to upload.")
        except Exception as e:
            self.logger.error(f"Error during file upload: {e}")

    def monitor_meeting(self) -> None:
        self.logger.info("Started monitoring the meeting.")
        start_time = time.perf_counter()

        while not self.stop_event.is_set():
            current_time = time.perf_counter()
            elapsed_time = current_time - start_time
            
            # Before being admitted, check if max_waiting_time has been exceeded
            if not self.recording_started:
                if elapsed_time > self.max_waiting_time:
                    self.logger.info(f"Maximum waiting time ({self.max_waiting_time} seconds) exceeded. Ending session.")
                    break
            else: 
                recording_elapsed_time = current_time - self.recording_start_time
                if recording_elapsed_time > self.min_record_time:
                    self.logger.info(f"Minimum recording time ({self.min_record_time} seconds) reached. Ending session.")
                    break

            try:
                self.check_admission()
            except WebDriverException:
                self.logger.error("Browser has been closed. Stopping monitoring.")
                break
            except Exception as e:
                self.logger.error(f"Error during monitoring: {e}")
            time.sleep(5)

    def run(self) -> None:
        try:
            self.logger.info("=== STARTING GOOGLE MEET BOT ===")
            self.setup_browser()
            self.navigate_to_meeting()
            self.join_meeting()
            self.monitor_meeting()
        except Exception as e:
            self.logger.error(f"An error occurred during the meeting session: {e}", exc_info=True)
            raise GoogleMeetUIException(f"Bot error: {e}")
        finally:
            self.logger.info("Finalizing the meeting session.")
            self.end_session()
        self.logger.info("=== BOT COMPLETED ===")