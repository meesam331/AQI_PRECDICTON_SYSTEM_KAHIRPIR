import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
# Flask now renders the former Streamlit dashboard and handles predictions directly.
from flask import Flask, jsonify, render_template, request

import python as data_fetcher

APP_DIR = Path(__file__).resolve().parent
MODEL_PATHS = [APP_DIR / "model.pkl", APP_DIR / "aqi_pipeline.pkl"]
FEATURE_COLUMNS = ["pm2_5", "pm10", "co", "no2", "ozone", "temp", "humidity"]
DEFAULTS = {"pm2_5": 35.0, "pm10": 55.0, "co": 280.0, "no2": 28.0, "ozone": 40.0, "temp": 30.0, "humidity": 45.0}
LABELS = {"pm2_5": "PM2.5 (ug/m3)", "pm10": "PM10 (ug/m3)", "co": "Carbon monoxide (ug/m3)", "no2": "Nitrogen dioxide (ug/m3)", "ozone": "Ozone (ug/m3)", "temp": "Temperature (C)", "humidity": "Humidity (%)"}

app = Flask(__name__)
model = None
model_path = None


def load_model():
    """Load the trained artifact once per worker, with a friendly missing-file error."""
    global model, model_path
    if model is not None:
        return model
    for candidate in MODEL_PATHS:
        if candidate.exists():
            model_path = candidate
            model = joblib.load(candidate)
            return model
    expected = ", ".join(path.name for path in MODEL_PATHS)
    raise FileNotFoundError(f"No trained model was found. Add {expected} to the project root.")


def aqi_category(aqi):
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for sensitive groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very unhealthy"
    return "Hazardous"


def category_class(category):
    if category == "Good":
        return "good"
    if category == "Moderate":
        return "moderate"
    return "unhealthy"


def aqi_message(category):
    messages = {"Good": "Air quality is satisfactory for most people.", "Moderate": "Air quality is acceptable; sensitive people should stay aware.", "Unhealthy for sensitive groups": "Sensitive groups may experience health effects.", "Unhealthy": "Everyone may begin to experience health effects.", "Very unhealthy": "Health alert: the risk of effects is increased.", "Hazardous": "Health warning of emergency conditions."}
    return messages[category]


def forecast_data():
    source = "live"
    try:
        air, weather = data_fetcher.fetch_forecast(days=3)
    except Exception:
        air, weather = data_fetcher.sample_forecast(days=3)
        source = "sample"
    length = min(len(air["hourly"]["time"]), len(weather["hourly"]["time"]))
    frame = pd.DataFrame({"date": pd.to_datetime(air["hourly"]["time"][:length]), "pm2_5": air["hourly"]["pm2_5"][:length], "pm10": air["hourly"]["pm10"][:length], "aqi": air["hourly"]["us_aqi"][:length], "co": air["hourly"]["carbon_monoxide"][:length], "no2": air["hourly"]["nitrogen_dioxide"][:length], "ozone": air["hourly"]["ozone"][:length], "temp": weather["hourly"]["temperature_2m"][:length], "humidity": weather["hourly"]["relative_humidity_2m"][:length]}).dropna(subset=FEATURE_COLUMNS + ["aqi"])
    daily = frame.assign(day=frame["date"].dt.date).groupby("day", as_index=False)[FEATURE_COLUMNS + ["aqi"]].mean()
    return daily.to_dict("records"), source


def page_context(**values):
    try:
        forecast, source = forecast_data()
        observed = round(float(forecast[0]["aqi"])) if forecast else None
    except Exception as exc:
        forecast, source, observed = [], "unavailable", None
        values.setdefault("forecast_error", f"Forecast unavailable: {exc}")
    if observed is not None:
        observed_category = aqi_category(observed)
        values.update(observed=observed, observed_category=observed_category, observed_class=category_class(observed_category), observed_message=aqi_message(observed_category), latest=forecast[0])
    values.update(forecast=forecast, source=source, feature_columns=FEATURE_COLUMNS, labels=LABELS, defaults=DEFAULTS, model_available=any(path.exists() for path in MODEL_PATHS))
    return values


@app.get("/")
def home():
    return render_template("index.html", **page_context())


@app.post("/predict")
def predict():
    values = {field: request.form.get(field, "").strip() for field in FEATURE_COLUMNS}
    errors = []
    try:
        numeric_values = [float(values[field]) for field in FEATURE_COLUMNS]
    except (TypeError, ValueError):
        numeric_values = []
        errors.append("Enter a valid number for every model input.")
    if numeric_values and (not np.isfinite(numeric_values).all() or any(value < 0 for value in numeric_values)):
        errors.append("All model inputs must be finite, non-negative values.")
    if errors:
        return render_template("index.html", **page_context(values=values, error=errors[0])), 400
    try:
        features = pd.DataFrame([numeric_values], columns=FEATURE_COLUMNS)
        prediction = float(load_model().predict(features)[0])
        aqi = round(float(np.clip(prediction, 0, 500)), 2)
        result_category = aqi_category(aqi)
    except FileNotFoundError as exc:
        return render_template("index.html", **page_context(values=values, error=str(exc))), 503
    except Exception:
        return render_template("index.html", **page_context(values=values, error="The model could not generate a prediction. Check the input values and try again.")), 500
    return render_template("index.html", **page_context(values=values, result=aqi, result_category=result_category, result_class=category_class(result_category), result_message=aqi_message(result_category)))


@app.get("/about")
def about():
    return render_template("index.html", **page_context(show_about=True))


@app.get("/health")
def health():
    try:
        load_model()
        return jsonify(status="healthy", model=model_path.name)
    except Exception as exc:
        return jsonify(status="unhealthy", error=str(exc)), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
