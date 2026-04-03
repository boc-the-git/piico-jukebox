FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt /tmp/
RUN pip install --no-compile --no-cache-dir --requirement /tmp/requirements.txt

COPY src ./src

CMD ["python", "-u", "/app/src/rfid-monitor.py"]
