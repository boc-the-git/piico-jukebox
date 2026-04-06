# Configuration Guide

The RFID Monitor uses environment variables for configuration with automatic validation on startup.

## Required Variables

### `WEBHOOK_URL` (required)
Base URL for Home Assistant webhook. Tag ID will be appended to this URL.

**Validation:**
- Must be a valid HTTP or HTTPS URL
- Application exits immediately if not set or invalid

**Examples:**
```bash
# Good
WEBHOOK_URL=http://homeassistant.local:8123/api/webhook/nfc-tag-scanned-
WEBHOOK_URL=https://ha.example.com/api/webhook/rfid-

# Bad - will fail validation
WEBHOOK_URL=not-a-url
WEBHOOK_URL=ftp://wrong-scheme.com/webhook
WEBHOOK_URL=  # (empty/not set)
```

## Optional Variables

### `UPTIME_KUMA_PUSH_URL` (optional)
URL for Uptime Kuma push monitor to send periodic heartbeats.

**Validation:**
- Must be a valid HTTP or HTTPS URL if provided
- Heartbeat monitoring is disabled if not set

**Examples:**
```bash
# Good
UPTIME_KUMA_PUSH_URL=https://uptime.example.com/api/push/abc123

# Bad - will fail validation
UPTIME_KUMA_PUSH_URL=invalid-url
```

### `HEARTBEAT_INTERVAL` (optional)
Number of seconds between heartbeat checks.

**Validation:**
- Must be an integer between 10 and 3600 (10 seconds to 1 hour)
- Default: 60 seconds

**Examples:**
```bash
# Good
HEARTBEAT_INTERVAL=30
HEARTBEAT_INTERVAL=300

# Bad - will fail validation
HEARTBEAT_INTERVAL=5     # too low (minimum is 10)
HEARTBEAT_INTERVAL=5000  # too high (maximum is 3600)
HEARTBEAT_INTERVAL=abc   # not a number
```

### `HEALTH_FILE_PATH` (optional)
Custom path for Docker health check status file.

**Validation:**
- Validated as a Path type in main application
- Must be a valid file path string
- Default: `/tmp/rfid-monitor-health`

**Use cases:**
- Debugging health checks by using a persistent volume
- Custom monitoring scripts that read the health file
- Avoiding `/tmp` in restricted environments

**Examples:**
```bash
# Default behavior (not set)
# Uses /tmp/rfid-monitor-health

# Custom path
HEALTH_FILE_PATH=/app/data/health-status
HEALTH_FILE_PATH=/var/run/rfid-health
```

**Note:** The main application loads this via the Config validator. The health check script (`healthcheck.py`) reads it directly from the environment to remain lightweight.

## Configuration Methods

### Method 1: Environment Variables (Docker Compose)
```yaml
environment:
  - WEBHOOK_URL=http://homeassistant.local:8123/api/webhook/nfc-tag-scanned-
  - UPTIME_KUMA_PUSH_URL=https://uptime.example.com/api/push/abc123
  - HEARTBEAT_INTERVAL=60
  - HEALTH_FILE_PATH=/tmp/rfid-monitor-health
```

### Method 2: .env File (Development)
Create a `.env` file in the project root:
```bash
WEBHOOK_URL=http://homeassistant.local:8123/api/webhook/nfc-tag-scanned-
UPTIME_KUMA_PUSH_URL=https://uptime.example.com/api/push/abc123
HEARTBEAT_INTERVAL=60
HEALTH_FILE_PATH=/tmp/rfid-monitor-health
```

Use `.env.example` as a template.

### Method 3: Shell Export (Development)
```bash
export WEBHOOK_URL=http://homeassistant.local:8123/api/webhook/nfc-tag-scanned-
export UPTIME_KUMA_PUSH_URL=https://uptime.example.com/api/push/abc123
export HEARTBEAT_INTERVAL=60
export HEALTH_FILE_PATH=/tmp/rfid-monitor-health
python src/rfid-monitor.py
```

## Validation Errors

If configuration validation fails, the application will:
1. Print a detailed error message to stderr
2. Exit with code 1 (before initializing hardware)

**Example error output:**
```
Configuration validation failed: 1 validation error for Config
webhook_url
  Field required [type=missing, input_value={}, input_type=dict]
```

This fail-fast approach ensures problems are caught immediately rather than during operation.
