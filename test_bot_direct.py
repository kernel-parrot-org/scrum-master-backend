"""Direct bot test - bypass all FastAPI/DI layers."""
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=== Testing Google Meet Bot ===")

    # Test URL - you'll need to replace this with actual meet URL
    test_url = input("Enter Google Meet URL: ").strip()

    if not test_url:
        logger.error("No URL provided!")
        sys.exit(1)

    try:
        from scrum_master.modules.google_meet.infrastructure.selenium.meet_bot import JoinGoogleMeet

        logger.info(f"Creating bot for URL: {test_url}")

        bot = JoinGoogleMeet(
            meetlink=test_url,
            bot_name="Test Bot",
            min_record_time=60,  # 1 minute for testing
            max_waiting_time=300,  # 5 minutes max wait
            logger=logger,
        )

        logger.info("Starting bot...")
        bot.run()

        logger.info("=== Bot completed successfully ===")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Bot failed: {e}", exc_info=True)
        sys.exit(1)
