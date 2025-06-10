import os, json
import pandas as pd
import datetime
from settings import SettingsManager
from collections import defaultdict
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler

from weather_aggregator import WeatherAggregator


SETTINGS_FILE = "settings.json"

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
scheduler = BackgroundScheduler()

def prepare_table_view(df: pd.DataFrame):
    df = df.fillna('-')
    df = df.rename(columns={"timestamp": "Время запроса",
                       "source": "Источник",
                       "city": "Город",
                       "T0": "Темп. (C)",
                       "H0": "Влажн. (%)",
                       "P0": "Атм. давл. (мм.рт.ст.)",
                       "Ff": "Скор. ветра (км/ч)",
                       "WD0": "Напр. ветра",
                       "UVI": "УФ-индекс",
                       "AQI": "Инд. кач-ва возд.",
                       "conditions": "Условия"
                       })
    return df

def populate_page_data(filter_date:str = None, settings: SettingsManager = None):
    df = None
    series_by_source = defaultdict(list)
    
    settings = settings or SettingsManager().load_settings()
    city = settings.get("city", "")
    CURRENT_DB_FILENAME = settings.get("weather_current_database")

    if os.path.exists(CURRENT_DB_FILENAME):
        df = pd.read_excel(CURRENT_DB_FILENAME)
        if filter_date and "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df[df["timestamp"].dt.strftime("%Y-%m-%d").str.startswith(filter_date)]

        for _, row in df.iterrows():
            source = row.get("source")
            temp = row.get("T0")
            date = row.get("timestamp")

            if pd.notnull(source) and pd.notnull(temp) and pd.notnull(date):
                iso_time = pd.to_datetime(date).isoformat()
                series_by_source[source].append({
                    "x": iso_time,
                    "y": float(temp)
                })
        df = df.sort_values(by='timestamp',ascending=False)
        df = prepare_table_view(df)
        return {
            "table": df.to_html(index=False, classes="table table-striped table-bordered table-hover align-middle"),
            "series": dict(series_by_source),
            'default_city': city,
        }
    return {
        "table": "<p>Нет данных</p>",
        "series": dict(series_by_source),
        "default_city": city,
    }

def is_tracking_active(settings: SettingsManager = None):
    settings = settings or SettingsManager().load_settings()
    tracking_start = settings.get("tracking_start")
        
    if tracking_start:
        try:
            start_time = datetime.datetime.strptime(tracking_start, "%Y-%m-%d %H:%M")
            tracking_active = datetime.datetime.now() >= start_time
            return tracking_active
        except Exception as e:
            print("Ошибка парсинга tracking_start:", e)
    return False


def update_weather_data(settings: SettingsManager = None): 
    settings = settings or SettingsManager().load_settings()
    city = settings.get("city","")
    CURRENT_WEATHER_FILENAME = settings.get("weather_current_database")
    FORECAST_WEATHER_FILENAME = settings.get("weather_forecast_database")
    
    tracking_active = is_tracking_active(settings)
    if tracking_active:
        aggregator = WeatherAggregator(db_current_weather=CURRENT_WEATHER_FILENAME, db_forecast_weather=FORECAST_WEATHER_FILENAME)
        df_current_new = aggregator.collect_current_data(city)
        df_forecast_new = aggregator.collect_forecast_data(city)
        aggregator.append_to_current_report(df_current_new)
        aggregator.append_to_forecast_report(df_forecast_new)


def start_scheduler():
    settings = SettingsManager().load_settings()
    interval = settings.get("server_interval", 10)
    if scheduler.running:
        scheduler.remove_all_jobs()
    else:
        scheduler.start()
    scheduler.add_job(update_weather_data, 'interval', seconds=interval, id="weather_update", replace_existing=True)

@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request, filter_date: str = None):
    data_dict = populate_page_data(filter_date=filter_date)
    data_dict['request'] = request
    return templates.TemplateResponse("form.html", data_dict)

@app.get("/data", response_class=JSONResponse)
async def get_weather_table():
    data_dict = populate_page_data()
    return data_dict

@app.get("/tracking-status", response_class=JSONResponse)
async def get_weather_table():
    return {"tracking_status": is_tracking_active()}

@app.get("/download_current")
async def download_report_current():
    settings = SettingsManager().load_settings()
    DB_CURRENT = settings.get("weather_current_database")
    DB_FORECAST = settings.get("weather_forecast_database")
    return FileResponse(DB_CURRENT, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=DB_CURRENT)

@app.get("/download_forecast")
async def download_report_forecast():
    settings = SettingsManager().load_settings()
    DB_FORECAST = settings.get("weather_forecast_database")
    return FileResponse(DB_FORECAST, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=DB_FORECAST)

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    settings = SettingsManager().load_settings()
    return templates.TemplateResponse("settings.html", {"request": request, "settings": settings})

@app.post("/settings", response_class=HTMLResponse)
async def save_user_settings(request: Request, 
                             city: str = Form(...), 
                             interval: int = Form(...), 
                             tracking_start_at: str = Form(...), 
                             db_current_filename:str = Form(...), 
                             db_forecast_filename:str = Form(...), 
                             server_interval: int = Form(...)):
    if tracking_start_at:
        tracking_start_at = tracking_start_at.replace("T", " ")
    if not db_current_filename:
        db_current_filename = "weather_report_current.xlsx"
    if not db_forecast_filename:
        db_forecast_filename = "weather_report_forecast.xlsx"
        
    SettingsManager().save_settings(
        {
            "city": city, 
            "interval": interval, 
            "tracking_start": tracking_start_at, 
            "weather_current_database":db_current_filename, 
            "weather_forecast_database":db_forecast_filename, 
            "server_interval": server_interval
        })
    
    start_scheduler()
    
    return RedirectResponse(url="/", status_code=302)

start_scheduler()