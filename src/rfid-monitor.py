from PiicoDev_RFID import PiicoDev_RFID
# from PiicoDev_Unified import sleep_ms
from time import sleep
import requests
import logging
import os
import sys

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
        id = rfid.readID()   # get the id

        if len(id) == 0:
            logger.info('Card not read successfully. Ensure to hold it there for a moment to allow a successful read.')
            continue

        logger.debug('id: '+id)

        id_without_colons = id.replace(':','')
        url = f"{WEBHOOK_URL}{id_without_colons}"
        logger.info('url: '+url)

        response = requests.post(url)

        # Check the status code of the response
        if response.status_code == 200:
            logger.info("Webhook post was successful!")
        else:
            # TODO: What does a failure actually look like? Break URL to test..
            logger.error(f"Webhook post failed with status code {response.status_code}")
            logger.error("Response text:", response.text)

        sleep(8) # Sleep for 8s, so we don't spam messages when a card is held there

    sleep(0.1)
