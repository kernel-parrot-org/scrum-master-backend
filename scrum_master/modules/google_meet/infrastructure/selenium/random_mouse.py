"""Random mouse movements."""
import logging
import random
import time

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By


def random_mouse_movements(browser, logger: logging.Logger, duration_seconds: int = 8) -> None:
    """Perform random mouse movements."""
    try:
        logger.info(f"Random mouse movements for {duration_seconds}s")

        window_size = browser.get_window_size()
        width = window_size['width']
        height = window_size['height']
        margin = 100

        actions = ActionChains(browser)
        end_time = time.time() + duration_seconds

        while time.time() < end_time:
            try:
                x_position = random.randint(margin, width - margin)
                y_position = random.randint(margin, height - margin)

                actions.reset_actions()
                body = browser.find_element(By.TAG_NAME, "body")
                actions.move_to_element(body).perform()

                time.sleep(random.uniform(0.1, 0.3))

                if random.random() < 0.1:
                    time.sleep(random.uniform(0.5, 1.0))

            except Exception as e:
                logger.warning(f"Movement error: {str(e)}")
                try:
                    actions.reset_actions()
                    body = browser.find_element(By.TAG_NAME, "body")
                    actions.move_to_element(body).perform()
                    time.sleep(0.5)
                except:
                    pass

        logger.info("Mouse movements completed")
    except Exception as e:
        logger.error(f"Error during mouse movements: {e}")