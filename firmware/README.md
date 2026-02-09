# ESP32 + DHT11 firmware (MicroPython)

Reads temperature and humidity from a DHT11, sends JSON to the Local AI Gateway, and shows the result on a 0.96" SSD1306 OLED and the REPL.

## Prerequisites

- **MicroPython** firmware on your ESP32 (e.g. from [micropython.org](https://micropython.org/download/ESP32_GENERIC/)).
- **DHT11** (or DHT22) — built-in `dht` module.
- **0.96" SSD1306** OLED (128×64, I2C) — the [SSD1306 driver](https://docs.micropython.org/en/latest/esp8266/tutorial/ssd1306.html) is built into MicroPython on ESP32/ESP8266; display is optional (script runs without it if not connected).

## Wiring

| DHT11   | ESP32   |
|---------|---------|
| DATA    | GPIO 4  |
| VCC     | 3.3 V   |
| GND     | GND     |

| SSD1306 | ESP32   |
|---------|---------|
| SDA     | GPIO 21 |
| SCL     | GPIO 22 |
| VCC     | 3.3 V   |
| GND     | GND     |

Keep wires short to reduce noise.

## Configure

Edit the top of `main.py`:

- `WIFI_SSID` / `WIFI_PASS` — your Wi‑Fi
- `GATEWAY_URL` — e.g. `http://192.168.1.100:8000/describe` (IP of the machine running FastAPI)
- `DHT_PIN` — default 4
- `OLED_SDA_PIN` / `OLED_SCL_PIN` — I2C for SSD1306 (defaults 21, 22); `OLED_I2C_ADDR` usually 0x3C

See `config.example.py` for the list of variables.

## Deploy and run

1. Flash MicroPython to the ESP32 (e.g. with `esptool.py`).
2. Copy `main.py` to the device so it runs on boot. The SSD1306 driver is built-in; no extra files needed. Options:
   - **Thonny**: open `main.py`, then “Save as…” → “MicroPython device”.
   - **mpremote**: `mpremote cp main.py :main.py`
   - **ampy**: `ampy -p COM3 put main.py`
3. Reset the board or connect to the REPL; the script runs automatically and prints sensor values and the one-sentence description every 30 seconds.

To run once from the REPL instead of on boot:

```python
import main
main.main()
```

## Serial / REPL

Use 115200 baud. You’ll see Wi‑Fi connection, then periodic lines like:

The OLED shows the current temperature and humidity on the first line, and the AI-generated sentence wrapped on the following lines.

```
Temp: 23.4 °C  Humidity: 52.0 %
---
It's comfortably warm indoors with moderate humidity.
---
```
