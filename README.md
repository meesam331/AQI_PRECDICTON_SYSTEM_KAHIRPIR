# AQI Prediction System

A production-ready AQI prediction web app for Khairpur, Pakistan, built for the 10Pearls Internship.

**Author:** Meeesam Raza

**Live App:** [AQI Prediction System](web-production-c7cf8.up.railway.app)

This project was migrated from Streamlit to Flask. The Flask application serves the HTML dashboard, loads the trained model, handles validation, and renders predictions in one deployable service.

## Features

- Model-backed AQI predictions from PM2.5, PM10, CO, NO2, ozone, temperature, and humidity
- Three-day Open-Meteo outlook with a sample-data fallback
- Color-coded AQI health categories
- Responsive server-rendered interface
- Health endpoint at `/health` for deployment monitoring
- Friendly handling for missing model artifacts and invalid input

## Tech Stack

Python, Flask, Gunicorn, Pandas, NumPy, Scikit-learn, XGBoost, Joblib, and Open-Meteo.

## Project Structure

```text
aqi-prediction-10pearls/
├── app.py
├── aqi_pipeline.pkl
├── requirements.txt
├── Procfile
├── templates/index.html
├── static/style.css
├── notebooks/                 # Training notebooks are retained here when present
└── weather_data_khairpur.csv
```

The app prefers `model.pkl` and falls back to the existing `aqi_pipeline.pkl`. Keep either trained artifact in the project root. Notebook files are intentionally retained for reproducibility.

## Local Setup

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. The optional `PORT` environment variable controls the listening port.

## Deploy on Railway

1. Push this repository to GitHub and create a new Railway project from the repository.
2. Railway installs dependencies from `requirements.txt`.
3. The `Procfile` starts the service with `web: gunicorn app:app --bind 0.0.0.0:$PORT`.
4. Confirm the deployment with `https://your-domain/health`.

Railway supplies `PORT` automatically. No second API or Streamlit service is required.

## Model Inputs

The saved pipeline expects these named columns in order: `pm2_5`, `pm10`, `co`, `no2`, `ozone`, `temp`, and `humidity`.
