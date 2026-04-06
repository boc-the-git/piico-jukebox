# Error Recovery

The RFID Monitor includes robust error recovery mechanisms to handle transient failures and hardware issues without requiring manual intervention.

## Webhook Retry Logic

### Overview
Failed webhook calls are automatically retried with exponential backoff when appropriate, improving reliability in the face of temporary network issues or server problems.

### Configuration

**`WEBHOOK_MAX_RETRIES`** (default: 3)
- Maximum number of retry attempts after initial failure
- Range: 0-10
- Total attempts = initial + retries (e.g., 3 retries = 4 total attempts)

**`WEBHOOK_RETRY_DELAY`** (default: 1.0 seconds)
- Initial delay before first retry
- Range: 0.1-10.0 seconds
- Delay doubles with each retry (exponential backoff)

### Example Retry Sequence

With default settings (3 retries, 1.0s initial delay):
1. **Initial attempt** - fails
2. Wait 1 second
3. **Retry 1** - fails
4. Wait 2 seconds
5. **Retry 2** - fails
6. Wait 4 seconds
7. **Retry 3** - succeeds ✓

Total time before giving up: ~7 seconds

### Error Classification

The retry logic intelligently classifies errors as **transient** or **fatal**:

#### Transient Errors (will retry)
- **Network timeouts** - Server took too long to respond
- **Connection errors** - Network temporarily unreachable
- **5xx server errors** - Temporary server-side issues (500, 502, 503, 504)

#### Fatal Errors (will NOT retry)
- **4xx client errors** - Bad request, authentication failure, not found (400, 401, 403, 404)
- **Malformed URLs** - Configuration error
- **Other unexpected errors** - Unknown issues

This prevents wasting time retrying errors that won't succeed regardless of retry attempts.

### Logging

Each retry attempt is logged with detailed information:

```
# Transient error - will retry
2026-04-06 21:30:15 WARNING  Transient error (Timeout), retrying in 1.0s... (attempt 1/4)
2026-04-06 21:30:17 WARNING  Transient error (ConnectionError), retrying in 2.0s... (attempt 2/4)
2026-04-06 21:30:21 INFO     Webhook succeeded on attempt 3

# Fatal error - no retry
2026-04-06 21:30:15 ERROR    Webhook failed with client error 404: Not Found

# All retries exhausted
2026-04-06 21:30:25 ERROR    Webhook failed after 4 attempts: Connection timeout
```

### Tuning Recommendations

**Reliable network, fast server:**
```bash
WEBHOOK_MAX_RETRIES=1
WEBHOOK_RETRY_DELAY=0.5
```
- Quick retries for rare issues
- Minimal delay for legitimate failures

**Unreliable network:**
```bash
WEBHOOK_MAX_RETRIES=5
WEBHOOK_RETRY_DELAY=2.0
```
- More persistent retry attempts
- Longer delays to allow network recovery

**No retries (fail fast):**
```bash
WEBHOOK_MAX_RETRIES=0
```
- Useful for debugging or testing
- Failures are immediately visible

## RFID Hardware Recovery

### Overview
The application monitors RFID hardware health and automatically attempts recovery when failures are detected.

### Error Detection

The application tracks consecutive RFID errors:
- **Threshold:** 5 consecutive errors trigger recovery
- **Types of errors detected:**
  - `tagPresent()` exceptions
  - `readID()` failures
  - Hardware communication timeouts
  - I2C bus errors

### Recovery Process

When the error threshold is reached:

1. **Log warning** - "Too many consecutive RFID errors, attempting to reinitialize hardware..."
2. **Wait 2 seconds** - Allow hardware to settle
3. **Reinitialize hardware** - Create new `PiicoDev_RFID()` instance
4. **On success:**
   - Reset error counter
   - Resume normal operation
   - Log "RFID hardware initialized successfully"
5. **On failure:**
   - Log "RFID reinitialization failed"
   - Wait 10 seconds before next attempt
   - Continue retry loop

### Example Recovery Sequence

```
2026-04-06 21:30:15 ERROR    RFID hardware error (1/5): I2C communication error
2026-04-06 21:30:16 ERROR    RFID hardware error (2/5): I2C communication error
2026-04-06 21:30:17 ERROR    RFID hardware error (3/5): I2C communication error
2026-04-06 21:30:18 ERROR    RFID hardware error (4/5): I2C communication error
2026-04-06 21:30:19 ERROR    RFID hardware error (5/5): I2C communication error
2026-04-06 21:30:19 WARNING  Too many consecutive RFID errors, attempting to reinitialize hardware...
2026-04-06 21:30:21 INFO     RFID hardware initialized successfully
2026-04-06 21:30:21 INFO     Tag detected. Reading..
```

### Why This Helps

RFID hardware can fail for various reasons:
- **Loose connections** - Cable slightly disconnected
- **I2C bus glitches** - Temporary electrical interference
- **Power fluctuations** - Brief voltage drops
- **Hardware resets** - Device watchdog triggers

Automatic recovery means:
- No manual container restarts needed
- Reduced downtime during transient issues
- Better reliability in production

### Preventing Rapid Failure Loops

To avoid hammering the hardware with rapid reinit attempts:
- **1 second delay** between normal retry attempts
- **10 second delay** when reinitialization fails
- **Error counter reset** on successful operations

This prevents CPU thrashing and allows hardware time to recover.

## Startup Validation

### RFID Initialization

On startup, the application:
1. Attempts to initialize RFID hardware
2. Logs success or failure
3. **Exits with code 1** if initialization fails

This prevents running without functional hardware and makes failures immediately visible.

```
2026-04-06 21:30:15 ERROR    Failed to initialize RFID hardware: [Errno 2] No such file or directory: '/dev/i2c-1'
2026-04-06 21:30:15 ERROR    Cannot start without RFID hardware. Exiting.
```

## Health Check Integration

The health check mechanism complements error recovery:
- **Detects frozen main loop** - Even if error handlers fail
- **Docker can restart container** - Ultimate recovery for persistent failures
- **See:** `docs/HEALTHCHECK.md`

## Best Practices

### Monitoring

Watch for patterns in logs:
- **Frequent retries** - May indicate network or server issues
- **RFID reinit cycles** - Check hardware connections
- **Persistent failures** - Investigate root cause

### Configuration

Start with defaults and adjust based on observed behavior:
1. Monitor application for a week
2. Check logs for retry patterns
3. Tune settings based on success rates
4. Re-monitor to verify improvements

### Alerting

Set up alerts for:
- **Multiple webhook retry failures** - Server may be down
- **RFID reinitialization events** - Hardware issues
- **Docker unhealthy status** - Complete failure requiring attention

## Limitations

### What Error Recovery Does NOT Handle

- **Configuration errors** - Invalid webhook URL, bad settings
- **Permanent hardware failure** - Broken RFID reader
- **Home Assistant down** - Extended server outage
- **Network completely offline** - No internet connectivity

These require manual intervention or infrastructure fixes.

### Expected Behavior During Failures

**Temporary network glitch (5 seconds):**
- ✅ Handled by webhook retry logic
- No manual action needed

**RFID cable comes loose:**
- ✅ Handled by RFID reinitialization
- No manual action needed (if cable reconnects itself)

**Home Assistant server restart (2 minutes):**
- ⚠️ Partially handled
- Webhooks fail during restart
- Resume automatically once server is back
- Scans during downtime are lost (by design - no queueing)

**Raspberry Pi loses power:**
- ❌ Not handled
- Container restart via Docker/systemd handles this
- Application starts fresh on power return

## Troubleshooting

### Webhook retries not working

Check configuration:
```bash
docker logs jukebox | grep "Webhook retry"
# Should show: Webhook retry: max 3 attempts, 1.0s initial delay
```

Verify environment variable:
```bash
docker exec jukebox env | grep WEBHOOK
```

### RFID keeps failing

Check hardware:
```bash
# On Raspberry Pi host
ls -l /dev/i2c-1
# Should show: crw-rw---- 1 root i2c 89, 1 ...

# Test I2C devices
i2cdetect -y 1
# Should show RFID device address
```

Check container device access:
```bash
docker exec jukebox ls -l /dev/i2c-1
# Should show device is accessible
```

### Too many retries causing delays

Reduce retry attempts:
```yaml
environment:
  - WEBHOOK_MAX_RETRIES=1
  - WEBHOOK_RETRY_DELAY=0.5
```

### Logs show constant errors

Check if issue is transient or persistent:
```bash
# Last hour of logs
docker logs --since 1h jukebox | grep ERROR

# Count error types
docker logs jukebox | grep ERROR | sort | uniq -c | sort -rn
```
