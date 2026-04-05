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
```

No test or lint commands are currently configured.

## Architecture

Single-file application (`src/rfid-monitor.py`) that:
1. Initializes PiicoDev RFID hardware via I2C (`/dev/i2c-1`)
2. Polls for RFID tags in an infinite loop (100ms hardware polling)
3. On tag detection, POSTs to Home Assistant webhook with tag ID
4. Implements 8-second debounce between successful reads

Optional Uptime Kuma heartbeat monitoring:
- Sends periodic GET requests to configured push monitor URL
- Time-based intervals (default 60s, configurable via HEARTBEAT_INTERVAL)
- Failures logged but don't disrupt RFID monitoring
- Enabled when UPTIME_KUMA_PUSH_URL environment variable is set

Deployed as a Docker container with I2C device passthrough to Raspberry Pi hardware.

## Dependencies

Managed with `uv` via `pyproject.toml`:
- `piicodev` - PiicoDev RFID hardware interface
- `requests` - HTTP client for webhook calls

