import logging
import os
import re
import sys
from time import sleep, time

import requests
from PiicoDev_RFID import PiicoDev_RFID

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('rfid-monitor')

WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
if not WEBHOOK_URL:
    logger.error("WEBHOOK_URL environment variable is not set")
    sys.exit(1)

# Uptime Kuma heartbeat monitoring (optional)
UPTIME_KUMA_PUSH_URL = os.environ.get('UPTIME_KUMA_PUSH_URL')

if UPTIME_KUMA_PUSH_URL:
    try:
        HEARTBEAT_INTERVAL = int(os.environ.get('HEARTBEAT_INTERVAL', '60'))
    except ValueError:
        logger.warning("Invalid HEARTBEAT_INTERVAL value, using default of 60 seconds")
        HEARTBEAT_INTERVAL = 60
else:
    HEARTBEAT_INTERVAL = 60  # Default value even when disabled

# Log configuration summary
logger.info('=' * 60)
logger.info('RFID Monitor Configuration')
logger.info('=' * 60)
logger.info(f'WEBHOOK_URL: {WEBHOOK_URL}')
if UPTIME_KUMA_PUSH_URL:
    logger.info(f'Uptime Kuma heartbeat: ENABLED')
    logger.info(f'  Push URL: {UPTIME_KUMA_PUSH_URL}')
    logger.info(f'  Heartbeat interval: {HEARTBEAT_INTERVAL}s')
else:
    logger.info(f'Uptime Kuma heartbeat: DISABLED')
logger.info(f'RFID polling interval: 100ms')
logger.info(f'Tag read debounce: 8s')
logger.info('=' * 60)

def send_heartbeat():
    """Send heartbeat to Uptime Kuma. Failures are logged but don't raise exceptions."""
    try:
        response = requests.post(UPTIME_KUMA_PUSH_URL, timeout=5)
        if response.status_code == 200:
            logger.debug("Heartbeat sent successfully")
        else:
            logger.warning(f"Heartbeat failed with status {response.status_code}")
            logger.warning(f"Response: {response.text}")
    except requests.RequestException as e:
        logger.warning(f"Heartbeat request failed: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error sending heartbeat: {e}")

rfid = PiicoDev_RFID()   # Initialise the RFID module

last_heartbeat = 0  # Track last heartbeat time

logger.info('RFID Monitor running')

while True:
    if rfid.tagPresent():    # if an RFID tag is present
        logger.info('Tag detected. Reading..')
        tag_id = rfid.readID()

        if len(tag_id) == 0:
            logger.info('Card not read successfully. Ensure to hold it there for a moment to allow a successful read.')
            continue

        logger.debug(f'tag_id: {tag_id}')

        tag_id_clean = tag_id.replace(':', '')

        if not re.fullmatch(r'[0-9A-Fa-f]+', tag_id_clean):
            logger.warning(f'Invalid tag ID format: {tag_id}')
            continue

        url = f"{WEBHOOK_URL}{tag_id_clean}"
        logger.info(f'url: {url}')

        try:
            response = requests.post(url, timeout=10)
        except requests.RequestException as e:
            logger.error(f"Webhook request failed: {e}")
            sleep(8)
            continue

        if response.status_code == 200:
            logger.info("Webhook post was successful!")
        else:
            logger.error(f"Webhook post failed with status code {response.status_code}")
            logger.error(f"Response text: {response.text}")

        sleep(8) # Sleep for 8s, so we don't spam messages when a card is held there

    sleep(0.1)

    # Send heartbeat to Uptime Kuma if configured
    if UPTIME_KUMA_PUSH_URL:
        current_time = time()
        if current_time - last_heartbeat >= HEARTBEAT_INTERVAL:
            send_heartbeat()
            last_heartbeat = current_time
