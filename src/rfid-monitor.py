import logging
import os
import re
import sys
from time import sleep

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

rfid = PiicoDev_RFID()   # Initialise the RFID module

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
