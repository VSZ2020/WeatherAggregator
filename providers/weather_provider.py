import requests
import datetime as dt
from abc import ABC, abstractmethod

class WeatherProvider(ABC):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x86) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive"
        })
    
    def _safe_int(self, text):
        try:
            return int(text.replace("−", "-").replace("°", "").replace("+", "").replace("C",""))
        except:
            return None
    
    @abstractmethod
    def fetch(self, city: str) -> dict:
        pass
    
    @abstractmethod
    def fetch_forecast(self, city: str) -> dict:
        pass
    
    def make_dummy(self,
                   source_name: str,
                   timestamp: dt.datetime | None = None,
                   city:str = None, 
                   temp: int | None = None, 
                   pres: int | None = None, 
                   hum: int | None = None,
                   wind_speed: int = None,
                   wind_direction: str = None,
                   uv_index: int | None = None,
                   air_quality_index: str | None = None,
                   pm25: int = None,
                   pm10: int = None,
                   no2_gas: int = None,
                   so2_gas: int = None,
                   o3_gas: int = None,
                   co_gas: int = None,
                   precipitationTypes: str = None):
        return {
            'timestamp' : timestamp or dt.datetime.now(),
            'city' : city,
            'source': source_name,
            # Температура воздуха (Цельсий)
            'T0': temp,
            # Атм. давление (мм.рт.ст.)
            'P0': pres,
            # Относит. влажность (%)
            'H0': hum,
            # Скорость ветра (км/ч)
            'Ff': wind_speed,
            # Направление ветра
            'WD0': wind_direction,
            # УФ-индекс
            'UVI': uv_index,
            'conditions': precipitationTypes,
            
            # Индекс качества воздуха
            'AQI': air_quality_index,
            
            #  Основные загрязнители воздуха (мкг/м3)
            'PM2.5': pm25,
            'PM10': pm10,
            'NO2': no2_gas,
            'O3': o3_gas,
            'CO': co_gas,
            'SO2': so2_gas,
            # Конец списка загрязнителей
        }
    
    
    def make_forecast_dummy(self,
                   source_name: str,
                   timestamp: dt.datetime | None = None,
                   city:str = None, 
                   
                   temp_morn: int | None = None, 
                   temp_day: int | None = None, 
                   temp_even: int | None = None, 
                   temp_night: int | None = None,
                    
                   pres_morn: int | None = None, 
                   pres_day: int | None = None, 
                   pres_even: int | None = None, 
                   pres_night: int | None = None, 
                   
                   humid_morn: int | None = None, 
                   humid_day: int | None = None, 
                   humid_even: int | None = None, 
                   humid_night: int | None = None, 
                   
                   wind_speed_morn: int | None = None, 
                   wind_speed_day: int | None = None, 
                   wind_speed_even: int | None = None, 
                   wind_speed_night: int | None = None, 
                   
                   wind_dir_morn: str | None = None, 
                   wind_dir_day: str | None = None, 
                   wind_dir_even: str | None = None, 
                   wind_dir_night: str | None = None, 
                   
                   max_uv_index: int = None,
                   min_uv_index: int = None,
                   
                   precips_morn: str | None = None, 
                   precips_day: str | None = None, 
                   precips_even: str | None = None, 
                   precips_night: str | None = None,):
        return {
            'timestamp' : timestamp or dt.datetime.now(),
            'city' : city,
            'source': source_name,
            
            'TM1': temp_morn,
            'TD1': temp_day,
            'TE1': temp_even,
            'TN1': temp_night,
            
            'PM1': pres_morn,
            'PD1': pres_day,
            'PE1': pres_even,
            'PN1': pres_night,
            
            'HM1': humid_morn,
            'HD1': humid_day,
            'HE1': humid_even,
            'HN1': humid_night,
            
            'WSM1': wind_speed_morn,
            'WSD1': wind_speed_day,
            'WSE1': wind_speed_even,
            'WSN1': wind_speed_night,
            
            'WDM1': wind_dir_morn,
            'WDD1': wind_dir_day,
            'WDE1': wind_dir_even,
            'WDN1': wind_dir_night,
            
            'PrM1': precips_morn,
            'PrD1': precips_day,
            'PrE1': precips_even,
            'PrN1': precips_night,
            
            'MaxUVI1': max_uv_index,
            'MinUVI1': min_uv_index,
        }