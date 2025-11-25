"""Test router and bot integration."""
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


async def test_connect():
    """Test bot connection."""
    from scrum_master.modules.google_meet.config import GoogleMeetConfig
    from scrum_master.modules.google_meet.infrastructure.selenium.meet_adapter import GoogleMeetAdapter
    from scrum_master.modules.google_meet.application.interactors.connect_to_meet import ConnectToMeetInteractor
    from scrum_master.modules.google_meet.application.dtos import ConnectToMeetingRequest

    logger.info("=== Testing Google Meet Connection ===")

    # Get test URL
    test_url = input("Enter Google Meet URL: ").strip()
    if not test_url:
        logger.error("No URL provided!")
        return

    # Setup
    config = GoogleMeetConfig()
    adapter = GoogleMeetAdapter(config)
    interactor = ConnectToMeetInteractor(google_meet_adapter=adapter)

    # Create request
    request = ConnectToMeetingRequest(
        meet_url=test_url,
        bot_name="Test Bot",
        min_record_time=60,
        max_waiting_time=300,
    )

    # Execute
    logger.info("Executing connection...")
    result = await interactor.execute(request)

    logger.info(f"Result: {result}")
    logger.info(f"Status: {result.status}")
    logger.info(f"Message: {result.message}")

    # Wait a bit to see if bot starts
    logger.info("Waiting 10 seconds to verify bot started...")
    await asyncio.sleep(10)

    logger.info("=== Test Complete ===")


if __name__ == "__main__":
    try:
        asyncio.run(test_connect())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
