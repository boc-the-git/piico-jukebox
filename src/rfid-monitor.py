import logging
import re
import signal
import sys
from time import sleep, time

import requests
from PiicoDev_RFID import PiicoDev_RFID

from config import load_config

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('rfid-monitor')

# Load and validate configuration
config = load_config()

# Log configuration summary
logger.info('=' * 60)
logger.info('RFID Monitor Configuration')
logger.info('=' * 60)
logger.info(f'WEBHOOK_URL: {config.webhook_url}')
if config.uptime_kuma_push_url:
    logger.info(f'Uptime Kuma heartbeat: ENABLED')
    logger.info(f'  Push URL: {config.uptime_kuma_push_url}')
    logger.info(f'  Heartbeat interval: {config.heartbeat_interval}s')
else:
    logger.info(f'Uptime Kuma heartbeat: DISABLED')
logger.info(f'RFID polling interval: 100ms')
logger.info(f'Tag read debounce: 8s')
logger.info('=' * 60)

# Shutdown flag for graceful termination
shutdown_requested = False

# Health check file for Docker
HEALTH_FILE = config.health_file_path


def update_health_status():
    """Write current timestamp to health file for Docker health checks."""
    try:
        HEALTH_FILE.write_text(str(int(time())))
    except Exception as e:
        logger.warning(f"Failed to update health status: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals (SIGTERM, SIGINT) gracefully."""
    global shutdown_requested
    signal_name = signal.Signals(signum).name
    logger.info(f'Received {signal_name}, initiating graceful shutdown...')
    shutdown_requested = True


def send_heartbeat():
    """Send heartbeat to Uptime Kuma. Failures are logged but don't raise exceptions."""
    if not config.uptime_kuma_push_url:
        return

    try:
        response = requests.get(str(config.uptime_kuma_push_url), timeout=5)
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

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

last_heartbeat = 0  # Track last heartbeat time

logger.info('RFID Monitor running')

# Initial health status
update_health_status()

while not shutdown_requested:
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

        url = f"{config.webhook_url}{tag_id_clean}"
        logger.info(f'url: {url}')

        try:
            response = requests.post(str(url), timeout=10)
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

    # Update health status for Docker health check
    update_health_status()

    # Send heartbeat to Uptime Kuma if configured
    if config.uptime_kuma_push_url:
        current_time = time()
        if current_time - last_heartbeat >= config.heartbeat_interval:
            send_heartbeat()
            last_heartbeat = current_time

# Cleanup on shutdown
logger.info('Shutting down RFID Monitor...')

# Send final heartbeat to signal shutdown
if config.uptime_kuma_push_url:
    logger.info('Sending final heartbeat...')
    send_heartbeat()

logger.info('Shutdown complete')
sys.exit(0)
