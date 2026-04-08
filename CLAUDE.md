# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-based RFID monitoring application for Raspberry Pi that polls a PiicoDev RFID reader and triggers Home Assistant webhooks when tags are scanned.

## Commands

```bash
# Pull Docker image
docker pull ghcr.io/boc-the-git/piico-jukebox

# Run with Docker Compose (production)
docker-compose up -d

# Run directly (development)
python src/rfid-monitor.py

# Check container health status
docker ps  # Look for "(healthy)" or "(unhealthy)"
docker inspect --format='{{.State.Health.Status}}' jukebox

# View health check logs
docker inspect jukebox | jq '.[0].State.Health.Log'

# Run health check manually
docker exec jukebox python /app/src/healthcheck.py
```

No test or lint commands are currently configured.

## Architecture

Main application (`src/rfid-monitor.py`) with configuration module (`src/config.py`):
1. Validates configuration on startup using pydantic-settings
2. Initializes PiicoDev RFID hardware via I2C (`/dev/i2c-1`)
3. Registers signal handlers for graceful shutdown (SIGTERM, SIGINT)
4. Polls for RFID tags in main loop (100ms hardware polling)
5. Updates health status file every iteration for Docker health checks
6. On tag detection, POSTs to Home Assistant webhook with tag ID
7. Implements 8-second debounce between successful reads
8. On shutdown signal, exits loop cleanly and sends final heartbeat

Configuration validation:
- Required: `WEBHOOK_URL` - must be valid HTTP/HTTPS URL
- Optional: `UPTIME_KUMA_PUSH_URL` - must be valid HTTP/HTTPS URL if provided
- Optional: `HEARTBEAT_INTERVAL` - must be 10-3600 seconds (default: 60)
- Optional: `HEALTH_FILE_PATH` - path for health check file (default: `/tmp/rfid-monitor-health`)
- Optional: `WEBHOOK_MAX_RETRIES` - max retry attempts for webhooks (default: 3, range: 0-10)
- Optional: `WEBHOOK_RETRY_DELAY` - initial retry delay in seconds (default: 1.0, range: 0.1-10.0)
- Application exits immediately with clear error if validation fails

Optional Uptime Kuma heartbeat monitoring:
- Sends periodic GET requests to configured push monitor URL
- Time-based intervals (default 60s, configurable via HEARTBEAT_INTERVAL)
- Failures logged but don't disrupt RFID monitoring
- Enabled when UPTIME_KUMA_PUSH_URL environment variable is set

Graceful shutdown:
- Handles SIGTERM (Docker stop) and SIGINT (Ctrl+C) signals
- Exits main loop cleanly without interrupting active operations
- Sends final heartbeat to Uptime Kuma if configured
- Logs shutdown process for observability
- Exits with code 0 on successful shutdown

Docker health check (`src/healthcheck.py`):
- Main loop writes timestamp to health file every iteration
- Health check script verifies timestamp is recent (< 30 seconds old)
- Runs every 30 seconds with 3 retries before marking unhealthy
- Allows Docker/orchestration tools to detect and restart frozen containers
- Configurable health file path via `HEALTH_FILE_PATH` env var (default: `/tmp/rfid-monitor-health`)

Error recovery:
- **Webhook retry logic**: Exponential backoff retry for transient errors
  - Retries network timeouts, connection errors, and 5xx server errors
  - Does NOT retry 4xx client errors (bad request, auth failures, not found)
  - Configurable max retries and initial delay
  - Logs each retry attempt with timing information
- **RFID hardware recovery**: Detects and recovers from hardware failures
  - Tracks consecutive RFID errors (max: 5 before reinit)
  - Attempts hardware reinitialization on persistent failures
  - Waits 2s before reinit attempt, then 10s if reinit itself fails
  - Gracefully handles tag read failures without crashing
- **Error classification**: Separates transient vs fatal errors for appropriate handling

Deployed as a Docker container with I2C device passthrough to Raspberry Pi hardware.

## Dependencies

Managed with `uv` via `pyproject.toml`:
- `piicodev` - PiicoDev RFID hardware interface
- `requests` - HTTP client for webhook calls
- `pydantic` - Data validation and settings management
- `pydantic-settings` - Environment variable loading with validation

