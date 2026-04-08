FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.4 /uv /bin/uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache .

COPY src ./src

# Health check: verify application is running and responsive
# Runs every 30s, timeout 5s, 3 retries before marking unhealthy
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python /app/src/healthcheck.py || exit 1

CMD ["python", "-u", "/app/src/rfid-monitor.py"]
