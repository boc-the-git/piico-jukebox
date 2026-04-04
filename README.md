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

## Home Assistant Setup

### Option 1: Using the Blueprint (Recommended)

1. **Import the Blueprint**
   - Copy the contents of `home-assistant/rfid-jukebox-blueprint.yaml`
   - In Home Assistant, go to **Settings** → **Automations & Scenes** → **Blueprints**
   - Click **Import Blueprint** and paste the raw GitHub URL or manually add the blueprint file

2. **Create Automations from the Blueprint**
   - Click **Create Automation** on the RFID Jukebox Action blueprint
   - Configure:
     - **Full Webhook ID**: The complete webhook ID (e.g., `nfc-tag-scanned-AABBCCDD`)
     - **Actions**: What to do when this tag is scanned

3. **Repeat for each RFID tag** you want to configure

### Option 2: Manual Webhook Automation

Create an automation in Home Assistant manually:

```yaml
automation:
  - alias: "RFID Tag - Play Jazz Playlist"
    trigger:
      - platform: webhook
        webhook_id: "nfc-tag-scanned-AABBCCDD"
        local_only: false
    action:
      - service: media_player.play_media
        target:
          entity_id: media_player.living_room
        data:
          media_content_id: "spotify:playlist:37i9dQZF1DXbITWG1ZJKYt"
          media_content_type: "playlist"
```

### Example Use Cases

- **Music Control**: Play specific playlists, albums, or radio stations on media players
- **Scene Activation**: Trigger lighting scenes (e.g., "Movie Mode", "Party Lights")
- **Smart Home Control**: Turn on/off devices, adjust thermostats
- **Notifications**: Send alerts to phones or speakers
- **Multi-Action Sequences**: Dim lights, start music, and close blinds with one tag

## Running with Docker (Recommended)

Build the image:

```bash
docker build -t boc/jukebox-python:latest .
```

Create a `docker-compose.yml` file:

```yaml
services:
  jukebox:
    container_name: jukebox
    image: boc/jukebox-python:latest
    environment:
      - TZ=Australia/Melbourne
      - WEBHOOK_URL=http://<your ip/hostname>:8123/api/webhook/nfc-tag-scanned-
    devices:
      - "/dev/i2c-1:/dev/i2c-1:rwm"
    restart: unless-stopped
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
