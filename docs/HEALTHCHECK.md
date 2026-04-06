# Docker Health Check

The RFID Monitor includes a built-in health check mechanism for Docker container monitoring.

## How It Works

### Health Status File
The main application (`rfid-monitor.py`) writes the current Unix timestamp to a health file every loop iteration (~100ms). This file serves as a heartbeat indicator that the application is alive and processing.

**Default location:** `/tmp/rfid-monitor-health`

### Health Check Script
The health check script (`healthcheck.py`) is run periodically by Docker to verify the application is healthy:

1. Reads the timestamp from the health file
2. Compares it against the current time
3. Returns exit code 0 (healthy) if timestamp is recent (< 30 seconds)
4. Returns exit code 1 (unhealthy) if:
   - Health file doesn't exist
   - Timestamp is stale (> 30 seconds old)
   - File content is invalid
   - Any other error occurs

### Docker Configuration
The Dockerfile includes a HEALTHCHECK instruction with these settings:

- **Interval:** 30 seconds between checks
- **Timeout:** 5 seconds max for check to complete
- **Retries:** 3 consecutive failures before marking unhealthy
- **Start period:** None (checks begin immediately)

This means the container will be marked unhealthy after ~90 seconds of the application being frozen or crashed.

## Viewing Health Status

### Check container health status
```bash
docker ps
# Look for "(healthy)" or "(unhealthy)" in STATUS column
```

### View detailed health check output
```bash
docker inspect --format='{{json .State.Health}}' jukebox | jq
```

### View health check logs
```bash
docker inspect jukebox | jq '.[0].State.Health.Log'
```

### Watch health status in real-time
```bash
watch -n 5 'docker inspect --format="{{.State.Health.Status}}" jukebox'
```

## Configuration

### Custom Health File Location
You can override the health file location using the `HEALTH_FILE_PATH` environment variable:

```yaml
# docker-compose.yml
environment:
  - HEALTH_FILE_PATH=/custom/path/to/health-file
```

This is useful if you want to:
- Use a persistent volume for debugging
- Avoid `/tmp` for some reason
- Integrate with custom monitoring scripts

**Note:** Both `rfid-monitor.py` and `healthcheck.py` use the same environment variable, so they will stay in sync.

## Integration with Orchestration

### Docker Compose
Health checks work automatically with Docker Compose. Unhealthy containers will be visible in `docker-compose ps`:

```bash
docker-compose ps
# NAME      STATUS
# jukebox   Up 5 minutes (healthy)
```

### Docker Swarm / Kubernetes
Orchestration platforms can use health checks to:
- Automatically restart unhealthy containers
- Route traffic away from unhealthy instances
- Alert on persistent health failures

Example Docker Swarm service config:
```yaml
deploy:
  restart_policy:
    condition: on-failure
    max_attempts: 3
```

### Watchtower / Autoheal
Compatible with container health monitoring tools like:
- [Autoheal](https://github.com/willfarrell/docker-autoheal) - Auto-restart unhealthy containers
- [Watchtower](https://github.com/containrrr/watchtower) - Monitor health during updates

## Troubleshooting

### Container marked unhealthy

**Check application logs:**
```bash
docker logs jukebox
```

**Verify main loop is running:**
```bash
# Check if health file is being updated
docker exec jukebox cat /tmp/rfid-monitor-health
sleep 1
docker exec jukebox cat /tmp/rfid-monitor-health
# Timestamps should be different
```

**Run health check manually:**
```bash
docker exec jukebox python /app/src/healthcheck.py
echo $?  # Should be 0 if healthy
```

### False positives (healthy when it shouldn't be)

If the container shows as healthy but isn't working:
- Health check only verifies the main loop is running
- Doesn't verify RFID hardware connectivity
- Doesn't verify webhook endpoint availability
- Doesn't verify network connectivity

Consider also monitoring:
- Application logs for errors
- Uptime Kuma heartbeat status
- Home Assistant webhook success rate

### Health file permissions

If health checks fail with permission errors:
```bash
# Check file permissions
docker exec jukebox ls -la /tmp/rfid-monitor-health

# Verify process can write to health file location
docker exec jukebox touch /tmp/test && docker exec jukebox rm /tmp/test
```

## Disabling Health Checks

To disable health checks (not recommended):

### Option 1: Override in docker-compose.yml
```yaml
services:
  jukebox:
    # ... existing config ...
    healthcheck:
      disable: true
```

### Option 2: Build custom Dockerfile
Remove or comment out the HEALTHCHECK instruction.

## Best Practices

1. **Monitor health check status** - Set up alerts for unhealthy containers
2. **Combine with Uptime Kuma** - Use both Docker health checks (local) and Uptime Kuma (remote)
3. **Review unhealthy logs** - Investigate patterns in health check failures
4. **Set restart policies** - Configure automatic restart on health failures
5. **Test health checks** - Verify they detect actual failures (e.g., kill main process)
