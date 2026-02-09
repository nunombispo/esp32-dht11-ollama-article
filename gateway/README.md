# Local AI Gateway (FastAPI + Ollama)

Validates sensor data from the ESP32, builds a prompt, calls Ollama, and returns a human-friendly description. Optional outside temperature via Open-Meteo.

## Prerequisites

- Python 3.10+
- Ollama running (e.g. on Raspberry Pi) at `http://127.0.0.1:11434` or set `OLLAMA_BASE_URL`
- Model pulled: `ollama pull mistral` (or set `OLLAMA_MODEL`)

## Install and run

```bash
cd gateway
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be at `http://<this-machine-ip>:8000`. Use that URL as `GATEWAY_URL` on the ESP32.

## Endpoints

- `GET /health` — readiness check
- `POST /describe` — body: `{"temperature_c": 23.4, "humidity": 52}` → returns `{"description": "One friendly sentence..."}`

## Optional: outside temperature

Set env vars so the gateway can add outside temp to the prompt (cached 5 min):

```bash
export OPENMETEO_LAT=38.7
export OPENMETEO_LON=-9.1
```

If unset, only indoor data is used.
