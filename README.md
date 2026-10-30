# Zeus Smart Security — Raspberry Pi 3 Model B

Local Wi-Fi smart motion detection and intruder alert dashboard.

## Current platform

Designed for modern Raspberry Pi OS / Debian Trixie with Python 3.13 and the **Picamera2** camera stack.

This version does **not** use the old `picamera` package.

## Features

- Flask web dashboard and REST API
- Picamera2 live camera capture
- MJPEG live stream at `/video`
- OpenCV frame-difference motion detection
- GPIO17 (physical pin 11) LED alarm output
- Arm/disarm control from the dashboard
- SQLite event history
- Automatic motion snapshots in `captures/`
- Local Wi-Fi/LAN access only
- Buzzer intentionally disabled until its electrical rating and driver circuit are confirmed

## Install on Raspberry Pi OS / Debian Trixie

From the project directory:

```bash
sudo apt-get update
sudo apt-get install -y python3-flask python3-opencv python3-numpy python3-picamera2 python3-rpi.gpio python3-smbus i2c-tools
```

Optional Python-only dependency:

```bash
python3 -m pip install --break-system-packages -r requirements.txt
```

The apt packages are preferred for OpenCV, NumPy, Picamera2, GPIO and system libraries on Raspberry Pi OS.

## Run

```bash
cd /home/it/Desktop/Zeus
python3 app.py
```

Find the Pi IP:

```bash
hostname -I
```

From a phone/laptop connected to the same Wi-Fi, open:

```text
http://PI_IP_ADDRESS:5000
```

For example, if `hostname -I` prints `10.142.173.214`, use:

```text
http://10.142.173.214:5000
```

## Verify dependencies

```bash
python3 -c "import flask, cv2, numpy; print('Flask:', flask.__version__); print('OpenCV:', cv2.__version__); print('NumPy:', numpy.__version__)"
python3 -c "from picamera2 import Picamera2; print('Picamera2 OK')"
python3 -c "import RPi.GPIO; print('GPIO OK')"
```

## API

- `GET /api/health`
- `GET /api/status`
- `POST /api/arm` with JSON `{"armed": true}` or `{"armed": false}`
- `GET /api/events`
- `GET /video` — MJPEG camera stream
- `GET /captures/<filename>` — saved motion image

## Wiring assumptions

- LED anode/long leg -> 220–330 ohm resistor -> BCM GPIO17 (physical pin 11)
- LED cathode/short leg -> GND (for example physical pin 6)
- LCD wiring remains as previously configured
- Do not connect the unknown 2-pin buzzer directly to a GPIO pin. Confirm its voltage/current rating and use a suitable transistor/driver first.

## Notes

- Keep port 5000 on a trusted local network; do not expose it directly to the internet.
- Picamera2 requires the current Raspberry Pi camera stack. The old `python3-picamera` package is intentionally not used.
- Motion detection is a simple frame-difference prototype and can react to major lighting changes.
