# PiicoDev Jukebox

RFID monitoring application for Raspberry Pi that polls a PiicoDev RFID reader and triggers Home Assistant webhooks when tags are scanned.

## Requirements

- Raspberry Pi with I2C enabled (`raspi-config` > Interface Options > I2C)
- [PiicoDev RFID Module](https://core-electronics.com.au/piicodev-rfid-module.html) connected via I2C
- Home Assistant instance with webhook automation configured

## Configuration

Set the `WEBHOOK_URL` environment variable to your Home Assistant webhook endpoint. The scanned tag ID will be appended to this URL.

Example: `WEBHOOK_URL=http://<your ip/hostname>:8123/api/webhook/nfc-tag-scanned-`

When a tag with ID `AABBCCDD` is scanned, a POST request is made to:
`http://<your ip/hostname>:8123/api/webhook/nfc-tag-scanned-AABBCCDD`

## Running with Docker (Recommended)

Build the image:

```bash
docker build -t boc/jukebox-python:latest .
```

Run with Docker Compose:

```bash
docker-compose up -d
```

The container requires I2C device passthrough (`/dev/i2c-1`).

## How It Works

1. Initializes the PiicoDev RFID hardware via I2C
2. Continuously polls for RFID tags (100ms intervals)
3. When a tag is detected, reads and validates the tag ID
4. POSTs to the configured Home Assistant webhook with the tag ID
5. Implements an 8-second debounce to prevent repeated triggers while a tag is held on the reader

## License

MIT
