"""Utility functions for Google Meet bot."""
import logging
import os
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def clean_meeting_link(url: str) -> str:
    """Clean and validate Google Meet link."""
    # Remove any whitespace
    url = url.strip()

    # If it's a full URL, extract the meeting code
    if 'meet.google.com' in url:
        return url

    # If it's just a code, construct the full URL
    if len(url) == 12 and '-' in url:  # Format like: abc-defg-hij
        return f"https://meet.google.com/{url}"

    return url


def convert_timestamp_to_utc(timestamp_ms: int) -> datetime:
    """Convert JavaScript timestamp (milliseconds) to UTC datetime."""
    if timestamp_ms:
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    return None


def create_tar_archive(json_file: str, audio_file: str, output_base: str) -> str | None:
    """
    Create a tar archive containing the JSON transcript and audio file.

    Args:
        json_file: Path to the JSON transcript file
        audio_file: Path to the audio file
        output_base: Base path for the output tar file (without extension)

    Returns:
        Full path to the created tar file, or None if creation failed
    """
    tar_file_path = f"{output_base}.tar"

    try:
        with tarfile.open(tar_file_path, 'w') as tar:
            # Add JSON file if it exists
            if os.path.exists(json_file):
                tar.add(json_file, arcname=os.path.basename(json_file))

            # Add audio file if it exists
            if os.path.exists(audio_file):
                tar.add(audio_file, arcname=os.path.basename(audio_file))

        return tar_file_path if os.path.exists(tar_file_path) else None
    except Exception as e:
        logger.error(f"Error creating tar archive: {e}")
        return None


def audio_file_path(audio_file: str) -> str | None:
    """
    Get the full path to the audio file if it exists.

    Args:
        audio_file: Path to the audio file

    Returns:
        Full path to the audio file, or None if it doesn't exist
    """
    if os.path.exists(audio_file):
        return os.path.abspath(audio_file)
    return None


def save_screenshot(browser, filename_prefix: str = "error") -> str | None:
    """
    Helper function to save screenshot for debugging.

    Args:
        browser: Selenium WebDriver instance
        filename_prefix: Prefix for the screenshot filename

    Returns:
        Path to the saved screenshot, or None if save failed
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create out directory if it doesn't exist
        out_dir = Path("out")
        out_dir.mkdir(exist_ok=True)

        screenshot_path = out_dir / f"{filename_prefix}_{timestamp}.png"
        browser.save_screenshot(str(screenshot_path))
        return str(screenshot_path)
    except Exception:
        return None