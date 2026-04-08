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
logger.info(f'Webhook retry: max {config.webhook_max_retries} attempts, {config.webhook_retry_delay}s initial delay')
if config.uptime_kuma_push_url:
    logger.info(f'Uptime Kuma heartbeat: ENABLED')
    logger.info(f'  Push URL: {config.uptime_kuma_push_url}')
    logger.info(f'  Heartbeat interval: {config.heartbeat_interval}s')
else:
    logger.info(f'Uptime Kuma heartbeat: DISABLED')
logger.info(f'RFID polling interval: 100ms')
logger.info(f'Tag read debounce: {TAG_DEBOUNCE_SECONDS}s per tag')
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


def sleep_with_health_updates(duration):
    """Sleep for duration seconds, updating health file every 100ms."""
    end = time() + duration
    while time() < end:
        sleep(min(0.1, end - time()))
        update_health_status()


def signal_handler(signum, frame):
    """Handle shutdown signals (SIGTERM, SIGINT) gracefully."""
    global shutdown_requested
    signal_name = signal.Signals(signum).name
    logger.info(f'Received {signal_name}, initiating graceful shutdown...')
    shutdown_requested = True


def is_transient_error(exception):
    """Determine if an error is transient and should be retried.

    Transient errors: Network timeouts, connection errors, temporary server issues.
    Fatal errors: Bad requests, authentication failures, not found errors.
    """
    if isinstance(exception, requests.exceptions.Timeout):
        return True
    if isinstance(exception, requests.exceptions.ConnectionError):
        return True
    if isinstance(exception, requests.exceptions.HTTPError):
        # Retry on 5xx server errors, not on 4xx client errors
        if hasattr(exception, 'response') and exception.response is not None:
            return 500 <= exception.response.status_code < 600
        return True
    return False


def send_webhook_with_retry(url, tag_id):
    """Send webhook with exponential backoff retry logic.

    Args:
        url: Full webhook URL to POST to
        tag_id: Tag ID for logging purposes

    Returns:
        True if successful, False otherwise
    """
    max_retries = config.webhook_max_retries
    retry_delay = config.webhook_retry_delay

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(str(url), timeout=10)

            if response.status_code == 200:
                if attempt > 0:
                    logger.info(f"Webhook succeeded on attempt {attempt + 1}")
                else:
                    logger.info("Webhook post was successful!")
                return True

            # Handle non-200 status codes
            if 400 <= response.status_code < 500:
                # Client error - don't retry
                logger.error(f"Webhook failed with client error {response.status_code}: {response.text}")
                return False

            # Server error - may retry
            if attempt < max_retries:
                logger.warning(f"Webhook failed with status {response.status_code}, retrying in {retry_delay}s...")
                sleep_with_health_updates(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Webhook failed after {max_retries + 1} attempts with status {response.status_code}")
                return False

        except requests.RequestException as e:
            if is_transient_error(e):
                if attempt < max_retries:
                    logger.warning(f"Transient error ({type(e).__name__}), retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries + 1})")
                    sleep_with_health_updates(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Webhook failed after {max_retries + 1} attempts: {e}")
                    return False
            else:
                # Fatal error - don't retry
                logger.error(f"Fatal webhook error: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook: {e}")
            return False


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

def init_rfid():
    """Initialize RFID hardware with error handling.

    Returns:
        PiicoDev_RFID object if successful, None otherwise
    """
    try:
        rfid = PiicoDev_RFID()
        logger.info('RFID hardware initialized successfully')
        return rfid
    except Exception as e:
        logger.error(f"Failed to initialize RFID hardware: {e}")
        return None


# Initialize RFID hardware
rfid = init_rfid()
if rfid is None:
    logger.error("Cannot start without RFID hardware. Exiting.")
    sys.exit(1)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

last_heartbeat = 0  # Track last heartbeat time
last_seen = {}  # Track last successful read time per tag ID
rfid_error_count = 0  # Track consecutive RFID errors
MAX_RFID_ERRORS = 5  # Max consecutive errors before attempting reconnection
TAG_DEBOUNCE_SECONDS = 8

logger.info('RFID Monitor running')

# Initial health status
update_health_status()

while not shutdown_requested:
    try:
        tag_present = rfid.tagPresent()
        rfid_error_count = 0  # Reset error count on successful operation
    except Exception as e:
        rfid_error_count += 1
        logger.error(f"RFID hardware error ({rfid_error_count}/{MAX_RFID_ERRORS}): {e}")

        if rfid_error_count >= MAX_RFID_ERRORS:
            logger.warning("Too many consecutive RFID errors, attempting to reinitialize hardware...")
            sleep_with_health_updates(2)
            rfid = init_rfid()
            if rfid is None:
                logger.error("RFID reinitialization failed. Waiting 10s before retry...")
                sleep_with_health_updates(10)
            else:
                rfid_error_count = 0
        else:
            sleep_with_health_updates(1)  # Brief delay before retry

        continue

    if tag_present:
        logger.info('Tag detected. Reading..')

        try:
            tag_id = rfid.readID()
        except Exception as e:
            logger.error(f"Failed to read tag: {e}")
            rfid_error_count += 1
            sleep_with_health_updates(1)
            continue

        if len(tag_id) == 0:
            logger.info('Card not read successfully. Ensure to hold it there for a moment to allow a successful read.')
            continue

        logger.debug(f'tag_id: {tag_id}')

        tag_id_clean = tag_id.replace(':', '')

        if not re.fullmatch(r'[0-9A-Fa-f]+', tag_id_clean):
            logger.warning(f'Invalid tag ID format: {tag_id}')
            continue

        if time() - last_seen.get(tag_id_clean, 0) < TAG_DEBOUNCE_SECONDS:
            continue

        url = f"{config.webhook_url}{tag_id_clean}"
        logger.info(f'url: {url}')

        # Send webhook with retry logic
        send_webhook_with_retry(url, tag_id_clean)
        last_seen[tag_id_clean] = time()

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
