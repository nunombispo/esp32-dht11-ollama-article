"""
Local AI Gateway for ESP32 + DHT11 + Ollama.
Validates sensor data, builds a prompt, calls Ollama, returns a human-friendly description.
Optional: enrich with outside temperature via Open-Meteo (cached).
"""

from __future__ import annotations
import os
import time
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")
OPENMETEO_LAT = os.getenv("OPENMETEO_LAT", "52.09083")
OPENMETEO_LON = os.getenv("OPENMETEO_LON", "5.12222")
OUTSIDE_TEMP_CACHE_SECONDS = int(os.getenv("OUTSIDE_TEMP_CACHE_SECONDS", "300"))  # 5 min

# -----------------------------------------------------------------------------
# Pydantic models
# -----------------------------------------------------------------------------
class SensorReading(BaseModel):
    temperature_c: float = Field(..., ge=-40, le=85, description="Indoor temperature in °C")
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity %")
    outside_temp_c: float | None = Field(None, ge=-60, le=60, description="Outside temperature (optional, can be set by gateway)")
    outside_humidity: float | None = Field(None, ge=0, le=100, description="Outside humidity (optional, can be set by gateway)")

# -----------------------------------------------------------------------------
# Outside temperature enrichment (optional, cached)
# -----------------------------------------------------------------------------
_cached_outside: tuple[float, float, float] | None = None  # (temp_c, humidity, timestamp)

def _fetch_outside_temp_and_humidity() -> tuple[float, float] | None:
    """Fetch current outside temperature from Open-Meteo (no API key). Cache for 5–10 min."""
    global _cached_outside
    if not OPENMETEO_LAT or not OPENMETEO_LON:
        return None
    now = time.time()
    if _cached_outside is not None and (now - _cached_outside[2]) < OUTSIDE_TEMP_CACHE_SECONDS:
        return _cached_outside[0], _cached_outside[1]
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={OPENMETEO_LAT}&longitude={OPENMETEO_LON}"
        "&current=temperature_2m, humidity_2m"
    )
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(url)
            r.raise_for_status()
            data = r.json()
            temp = float(data["current"]["temperature_2m"])
            humidity = float(data["current"]["humidity_2m"])
            _cached_outside = (temp, humidity, now)
            return temp, humidity
    except Exception:
        if _cached_outside:
            return _cached_outside[0], _cached_outside[1]
        return None

# -----------------------------------------------------------------------------
# Prompt template
# -----------------------------------------------------------------------------
def build_prompt(reading: SensorReading) -> str:
    lines = [
        "You are a home weather assistant.",
        "",
        f"Inside temperature: {reading.temperature_c}°C",
        f"Humidity: {reading.humidity}%",
    ]
    if reading.outside_temp_c is not None:
        lines.append(f"Outside temperature: {reading.outside_temp_c}°C")
    lines.extend([
        "",
        "Write ONE friendly sentence describing the indoor conditions. The temperature is given in Celsius.",
        "" if reading.outside_temp_c is None else "Compare it with the outside temperature in Celsius.",
        "" if reading.outside_humidity is None else "Mention the outside conditions in comparison to the indoor conditions.",
        "Avoid emojis. Be concise. Sound human.",
    ])
    return "\n".join(lines)

# -----------------------------------------------------------------------------
# Ollama client
# -----------------------------------------------------------------------------
def call_ollama(prompt: str) -> str:
    """Call Ollama /api/generate and return the generated text. Raises on failure."""
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    with httpx.Client(timeout=60.0) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    response_text = (data.get("response") or "").strip()
    if not response_text:
        raise ValueError("Ollama returned empty response")
    return response_text

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Local AI Gateway",
    description="Validates DHT11 sensor data, calls Ollama for a human-friendly description.",
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/describe")
def describe(reading: SensorReading) -> dict[str, str]:
    """
    Accept sensor readings (temperature_c, humidity; optional outside_temp_c).
    Optionally enrich with outside temperature, then ask Ollama for one friendly sentence.
    Returns { "description": "..." }.
    """
    # Optional enrichment: if we didn't get outside_temp_c, try Open-Meteo
    if reading.outside_temp_c is None and reading.outside_humidity is None and (OPENMETEO_LAT and OPENMETEO_LON):
        outside = _fetch_outside_temp_and_humidity()
        if outside is not None:
            reading = SensorReading(
                temperature_c=reading.temperature_c,
                humidity=reading.humidity,
                outside_temp_c=round(outside[0], 1),
                outside_humidity=round(outside[1], 1),
            )
            print(f"Enriched with outside temperature: {outside[0]}°C and humidity: {outside[1]}%")

    prompt = build_prompt(reading)

    try:
        description_text = call_ollama(prompt)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama unavailable: {e!s}")

    return {"description": description_text}


# -----------------------------------------------------------------------------
# Main function
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)