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
from providers.accuweather_provider import AccuWeatherProvider
from providers.yandexweather_provider import YandexWeatherProvider
from providers.gismeteo_provider import GismeteoProvider

SETTINGS_FILE = "settings.json"

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
scheduler = BackgroundScheduler()


def populate_page_data(filter_date:str = None, settings: SettingsManager = None):
    df = None
    series_by_source = defaultdict(list)
    
    settings = settings or SettingsManager().load_settings()
    city = settings.get("city", "")
    DATA_FILENAME = settings.get("weather_database_filename")

    if os.path.exists(DATA_FILENAME):
        df = pd.read_excel(DATA_FILENAME)
        if filter_date and "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df[df["Date"].dt.strftime("%Y-%m-%d").str.startswith(filter_date)]

        for _, row in df.iterrows():
            source = row.get("Source")
            temp = row.get("TemperatureNow")
            date = row.get("Date")

            if pd.notnull(source) and pd.notnull(temp) and pd.notnull(date):
                iso_time = pd.to_datetime(date).isoformat()
                series_by_source[source].append({
                    "x": iso_time,
                    "y": float(temp)
                })
        return {
            "table": df.sort_values(by='Date',ascending=False).to_html(index=False, classes="table table-striped table-bordered table-hover align-middle"),
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
    providers = [
        GismeteoProvider(),
        AccuWeatherProvider(),
        YandexWeatherProvider()
    ]
    settings = settings or SettingsManager().load_settings()
    city = settings.get("city","")
    DATA_FILENAME = settings.get("weather_database_filename")
    
    tracking_active = is_tracking_active(settings)
    if tracking_active:
        aggregator = WeatherAggregator(providers, DATA_FILENAME)
        df_new = aggregator.collect_data(city)
        aggregator.append_to_excel(df_new)


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

@app.get("/download")
async def download_file():
    settings = settings or SettingsManager().load_settings()
    DATA_FILENAME = settings.get("weather_database_filename")
    return FileResponse(DATA_FILENAME, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=DATA_FILENAME)

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    settings = SettingsManager().load_settings()
    return templates.TemplateResponse("settings.html", {"request": request, "settings": settings})

@app.post("/settings", response_class=HTMLResponse)
async def save_user_settings(request: Request, city: str = Form(...), interval: int = Form(...), tracking_start_at: str = Form(...), db_filename:str = Form(...), server_interval: int = Form(...)):
    if tracking_start_at:
        tracking_start_at = tracking_start_at.replace("T", " ")
    if db_filename:
        db_filename = "weather_report.xlsx"
        
    SettingsManager().save_settings({"city": city, "interval": interval, "tracking_start": tracking_start_at, "weather_database_filename":db_filename, "server_interval": server_interval})
    
    start_scheduler()
    
    return RedirectResponse(url="/", status_code=302)

start_scheduler()