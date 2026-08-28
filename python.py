import csv
import datetime
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

# Khairpur, Sindh (corrected coordinates)
LOCATIONS = {"Khairpur": {"latitude": 27.5295, "longitude": 68.7592}}
AIR_QUALITY_URL = os.getenv("OPEN_METEO_AIR_URL", "https://air-quality-api.open-meteo.com/v1/air-quality")
WEATHER_URL = os.getenv("OPEN_METEO_WEATHER_URL", "https://archive-api.open-meteo.com/v1/archive")
FORECAST_WEATHER_URL = os.getenv("OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))

START_DATE = "2023-01-01"
FEATURE_COLUMNS = ["pm2_5", "pm10", "co", "no2", "ozone", "temp", "humidity"]


def _to_date(value):
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(value)


def _get_json(url, params, attempts=3):
    last_error = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"API request failed after {attempts} attempts: {last_error}")


def fetch_data(location="Khairpur", days=None, start_date=None, end_date=None):
    coords = LOCATIONS[location]
    today = datetime.date.today()

    if end_date is None:
        end_date = today
    else:
        end_date = _to_date(end_date)

    if days is not None:
        start_date = today - datetime.timedelta(days=days - 1)
    elif start_date is None:
        start_date = _to_date(START_DATE)
    else:
        start_date = _to_date(start_date)

    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")

    params = {
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "timezone": "auto",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }

    air = _get_json(AIR_QUALITY_URL, {**params, "hourly": "pm2_5,pm10,us_aqi,carbon_monoxide,nitrogen_dioxide,ozone"})
    weather = _get_json(WEATHER_URL, {**params, "hourly": "temperature_2m,relative_humidity_2m"})
    return air, weather


def fetch_forecast(location="Khairpur", days=3):
    if not 1 <= days <= 7:
        raise ValueError("Forecast days must be between 1 and 7")

    coords = LOCATIONS[location]
    params = {
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "timezone": "auto",
        "forecast_days": days,
    }
    air = _get_json(
        AIR_QUALITY_URL,
        {**params, "hourly": "pm2_5,pm10,us_aqi,carbon_monoxide,nitrogen_dioxide,ozone"},
    )
    weather = _get_json(
        FORECAST_WEATHER_URL,
        {**params, "hourly": "temperature_2m,relative_humidity_2m"},
    )
    return air, weather


def sample_forecast(days=3):
    """Fallback sample data when Open-Meteo is unavailable."""
    hours = min(24 * days, 72)
    start = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
    times = [(start + datetime.timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    air = {
        "hourly": {
            "time": times,
            "pm2_5": [35.0 + (i % 24) * 0.4 for i in range(hours)],
            "pm10": [55.0 + (i % 24) * 0.6 for i in range(hours)],
            "us_aqi": [90 + (i % 24) for i in range(hours)],
            "carbon_monoxide": [280.0 + (i % 12) for i in range(hours)],
            "nitrogen_dioxide": [28.0 + (i % 8) for i in range(hours)],
            "ozone": [40.0 + (i % 10) for i in range(hours)],
        }
    }
    weather = {
        "hourly": {
            "time": times,
            "temperature_2m": [28.0 + (i % 24) * 0.3 for i in range(hours)],
            "relative_humidity_2m": [45.0 + (i % 15) for i in range(hours)],
        }
    }
    return air, weather


def save_to_csv(air, weather, output_file="weather_data_khairpur.csv"):
    times = air["hourly"]["time"]
    rows = []
    for i in range(min(len(times), len(weather["hourly"]["time"]))):
        row = [
            times[i],
            air["hourly"]["pm2_5"][i],
            air["hourly"]["pm10"][i],
            air["hourly"]["us_aqi"][i],
            air["hourly"]["carbon_monoxide"][i],
            air["hourly"]["nitrogen_dioxide"][i],
            air["hourly"]["ozone"][i],
            weather["hourly"]["temperature_2m"][i],
            weather["hourly"]["relative_humidity_2m"][i],
        ]
        if None not in row:
            rows.append(row)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "pm2_5", "pm10", "aqi", "co", "no2", "ozone", "temp", "humidity"])
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows to {output_file}")
    return output_file


if __name__ == "__main__":
    air_data, weather_data = fetch_data()
    save_to_csv(air_data, weather_data)
