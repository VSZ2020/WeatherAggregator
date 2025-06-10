import os, datetime
import pandas as pd
from providers.accuweather_provider import AccuWeatherProvider
from providers.yandexweather_provider import YandexWeatherProvider
from providers.gismeteo_provider import GismeteoProvider

class WeatherAggregator:
    def __init__(self, db_current_weather:str, db_forecast_weather:str):
        self.providers = [
            GismeteoProvider(),
            AccuWeatherProvider(),
            YandexWeatherProvider()
        ]
        self.db_current = db_current_weather
        self.db_forecast = db_forecast_weather

    def __append_to_report(self, df_new, report_filename):
        # Если файл существует, читаем старые данные
        if os.path.exists(report_filename):
            df_old = pd.read_excel(report_filename)
            df_combined = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_combined = df_new

        # Сохраняем объединённую таблицу
        df_combined.to_excel(report_filename, index=False)

    def append_to_current_report(self, df_new):
        self.__append_to_report(df_new, self.db_current)

    def append_to_forecast_report(self, df_new):
        self.__append_to_report(df_new, self.db_forecast)
    
    def collect_current_data(self, city: str):
        data = []
        print(f"[{datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")}] Запущен сбор фактических данных")
        for provider in self.providers:
            try:
                weather = provider.fetch(city)
                data.append(weather)
            except Exception as e:
                print(f"Ошибка у {provider.__class__.__name__}: {e}")
        return pd.DataFrame(data)

    def collect_forecast_data(self, city: str):
        data = []
        print(f"[{datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")}] Запущен сбор данных прогноза")
        for provider in self.providers:
            try:
                weather = provider.fetch_forecast(city)
                data.append(weather)
            except Exception as e:
                print(f"Ошибка у {provider.__class__.__name__}: {e}")
        return pd.DataFrame(data)