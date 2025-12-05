"""Google Meet adapter - Simplified."""
import logging
import threading
from typing import Any

from scrum_master.modules.google_meet.application.interfaces import \
    IGoogleMeetAdapter
from scrum_master.modules.google_meet.config import GoogleMeetConfig

from .meet_bot import GoogleMeetUIException, JoinGoogleMeet


class GoogleMeetAdapter(IGoogleMeetAdapter):
    """Adapter for Google Meet bot."""

    def __init__(self, config: GoogleMeetConfig):
        self.config = config
        self.bot: JoinGoogleMeet | None = None
        self.logger = logging.getLogger(__name__)
        self.bot_thread: threading.Thread | None = None

    def initialize_driver(self) -> None:
        """Initialize driver (no-op)."""
        pass

    def connect_to_meeting(
        self,
        meet_url: str,
        bot_name: str | None = None,
        min_record_time: int | None = None,
        max_waiting_time: int | None = None,
        presigned_url_combined: str | None = None,
        presigned_url_audio: str | None = None,
    ) -> None:
        """Connect to meeting in background thread."""
        try:
            bot_display_name = bot_name or self.config.bot_name
            record_time = min_record_time or 3600
            waiting_time = max_waiting_time or 1800

            self.logger.info(f"Starting bot for: {meet_url}")

            self.bot = JoinGoogleMeet(
                meetlink=meet_url,
                bot_name=bot_display_name,
                min_record_time=record_time,
                max_waiting_time=waiting_time,
                presigned_url_combined=presigned_url_combined,
                presigned_url_audio=presigned_url_audio,
                logger=self.logger,
            )

            # Run bot in background thread
            self.bot_thread = threading.Thread(target=self._run_bot, daemon=True)
            self.bot_thread.start()

            self.logger.info("Bot started in background")

        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}", exc_info=True)
            raise GoogleMeetUIException(f"Connection error: {e}")

    def _run_bot(self):
        """Run bot in background."""
        try:
            if self.bot:
                self.bot.run()
        except Exception as e:
            self.logger.error(f"Bot execution error: {e}", exc_info=True)

    def disconnect_from_meeting(self) -> None:
        """Disconnect from meeting."""
        if self.bot:
            try:
                self.logger.info("Disconnecting...")
                self.bot.end_session()
                if self.bot_thread and self.bot_thread.is_alive():
                    self.bot_thread.join(timeout=5)
                self.bot = None
            except Exception as e:
                self.logger.error(f"Disconnect error: {e}")

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.disconnect_from_meeting()