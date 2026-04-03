FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache .

COPY src ./src

CMD ["python", "-u", "/app/src/rfid-monitor.py"]
