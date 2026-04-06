#!/usr/bin/env python3
"""Health check script for Docker container monitoring."""

import os
import sys
from pathlib import Path
from time import time

# Health file location (must match rfid-monitor.py)
HEALTH_FILE = Path(os.environ.get('HEALTH_FILE_PATH', '/tmp/rfid-monitor-health'))

# Maximum age in seconds before considering unhealthy
MAX_AGE_SECONDS = 30


def check_health():
    """Check if the application is healthy by reading the health status file.

    Returns:
        0 if healthy, 1 if unhealthy.
    """
    try:
        # Check if health file exists
        if not HEALTH_FILE.exists():
            print(f"Health file not found: {HEALTH_FILE}", file=sys.stderr)
            return 1

        # Read timestamp from health file
        timestamp_str = HEALTH_FILE.read_text().strip()
        if not timestamp_str:
            print("Health file is empty", file=sys.stderr)
            return 1

        # Parse timestamp
        try:
            last_update = int(timestamp_str)
        except ValueError:
            print(f"Invalid timestamp in health file: {timestamp_str}", file=sys.stderr)
            return 1

        # Check if timestamp is recent
        current_time = int(time())
        age = current_time - last_update

        if age > MAX_AGE_SECONDS:
            print(f"Health check stale: last update {age}s ago (max: {MAX_AGE_SECONDS}s)", file=sys.stderr)
            return 1

        # Healthy
        print(f"Health check passed: last update {age}s ago")
        return 0

    except Exception as e:
        print(f"Health check error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(check_health())
