"""
ESP32 + DHT11 → Local AI Gateway (FastAPI + Ollama)
MicroPython: reads temperature and humidity, sends JSON to the gateway,
shows result on 0.96" SSD1306 OLED and REPL.

Wiring:
  DHT11 DATA → GPIO4, VCC → 3.3V, GND → GND
  SSD1306 SDA → GPIO21, SCL → GPIO22, VCC → 3.3V, GND → GND
"""

import json
import time
from machine import I2C, Pin

import dht
import network
import urequests

try:
    import ssd1306
except ImportError:
    ssd1306 = None

# -----------------------------------------------------------------------------
# Configuration — set these for your network and gateway
# -----------------------------------------------------------------------------
WIFI_SSID = "H369ABF75E6"
WIFI_PASS = "C79FA965F262"
GATEWAY_URL = "http://192.168.1.100:8000/describe"
DHT_PIN = 15
# 0.96" SSD1306 I2C (128x64)
OLED_SDA_PIN = 21
OLED_SCL_PIN = 22
OLED_I2C_ADDR = 0x3C

SEND_INTERVAL_SEC = 30
HTTP_TIMEOUT_SEC = 15
HTTP_RETRIES = 2
# Display: chars per line (8px font), max lines
OLED_COLS = 21
OLED_LINES = 8


def http_post_json(url, data):
    """POST JSON to url, return (status_code, body). Uses urequests."""
    body = json.dumps(data)
    headers = {"Content-Type": "application/json"}
    try:
        r = urequests.post(url, data=body, headers=headers, timeout=HTTP_TIMEOUT_SEC)
        code = r.status_code
        text = r.text
        r.close()
        return code, text
    except OSError as e:
        return None, str(e)


def init_display():
    """Init 128x64 SSD1306 over I2C. Returns display or None if unavailable."""
    if ssd1306 is None:
        print("No screen")
        return None
    try:
        i2c = I2C(0, scl=Pin(OLED_SCL_PIN), sda=Pin(OLED_SDA_PIN), freq=400000)
        disp = ssd1306.SSD1306_I2C(128, 64, i2c, addr=OLED_I2C_ADDR)
        disp.fill(0)
        disp.text("Starting...", 0, 0)
        disp.show()
        return disp
    except OSError:
        return None


def wrap_text(text, cols):
    """Split text into lines of at most cols chars, break on spaces when possible."""
    lines = []
    for word in text.split():
        if not lines:
            lines.append(word)
            continue
        if len(lines[-1]) + 1 + len(word) <= cols:
            lines[-1] += " " + word
        else:
            lines.append(word)
    # Split any line still too long
    out = []
    for line in lines:
        while len(line) > cols:
            out.append(line[:cols])
            line = line[cols:].lstrip()
        if line:
            out.append(line)
    return out


def display_update(display, temp_c, humidity, description=None):
    """Update OLED: line 0 = title, line 1 = temp, line 2 = humidity, rest = description wrapped."""
    if display is None:
        return
    display.fill(0)
    
    # Line 0: Title
    display.text("DHT11 Sensor", 0, 0)
    
    # Line 1: Temperature
    temp_line = "Temp: {:.1f}C".format(temp_c)
    display.text(temp_line, 0, 10)
    
    # Line 2: Humidity
    humid_line = "Humid: {:.0f}%".format(humidity)
    display.text(humid_line, 0, 20)
    
    # Line 3+: Description
    y = 30
    if description:
        for line in wrap_text(description, OLED_COLS)[:OLED_LINES - 3]:
            if y + 8 <= 64:
                display.text(line, 0, y)
                y += 10
    display.show()


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(0.5)
    return wlan


def read_dht(sensor):
    try:
        sensor.measure()
        t = sensor.temperature()
        h = sensor.humidity()
        if t is None or h is None:
            return None, None
        return round(t, 1), round(h, 1)
    except OSError:
        return None, None


def send_to_gateway(temp_c, humidity):
    """POST readings to gateway. Returns description string or None."""
    payload = {"temperature_c": temp_c, "humidity": humidity}
    for attempt in range(HTTP_RETRIES + 1):
        if attempt > 0:
            print("Retry...")
            time.sleep(0.5)
        code, body = http_post_json(GATEWAY_URL, payload)
        if code == 200:
            try:
                out = json.loads(body)
                desc = out.get("description", body)
                print("---")
                print(desc)
                print("---")
                return desc
            except ValueError:
                print(body)
                return None
        if code is not None:
            print("HTTP", code)
            print(body[:200] if body else "")
        else:
            print("Error:", body)
    print("Gateway unreachable after retries.")
    return None


def main():
    print("\nESP32 DHT11 → Local AI Gateway (MicroPython)")
    display = init_display()
    wlan = connect_wifi()
    print("IP:", wlan.ifconfig()[0])
    if display:
        display.fill(0)
        display.text(wlan.ifconfig()[0], 0, 0)
        display.show()

    sensor = dht.DHT11(Pin(DHT_PIN))
    last_send = 0
    last_temp_c = None
    last_humidity = None
    last_description = None

    while True:
        if not wlan.isconnected():
            connect_wifi()
            last_send = 0
            time.sleep(1)
            continue

        now = time.time()
        if now - last_send >= SEND_INTERVAL_SEC:
            temp_c, humidity = read_dht(sensor)
            if temp_c is not None:
                last_temp_c, last_humidity = temp_c, humidity
                print("Temp: {} °C  Humidity: {} %".format(temp_c, humidity))
                desc = send_to_gateway(temp_c, humidity)
                if desc is not None:
                    last_description = desc
                display_update(display, last_temp_c, last_humidity, last_description)
                last_send = now

        time.sleep(0.5)


if __name__ == "__main__":
    main()

