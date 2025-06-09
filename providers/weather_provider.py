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
    
    def make_dummy(self,
                   source_name: str,
                   city:str = None, 
                   temp: int | None = None, 
                   pres: int | None = None, 
                   hum: int | None = None,
                   uv_index_now: int | None = None,
                   air_quality_now: str | None = None,
                   pm25: int = None,
                   pm10: int = None,
                   no2_gas: int = None,
                   so2_gas: int = None,
                   o3_gas: int = None,
                   co_gas: int = None, 
                   max_uv_tomorrow: int = None,
                   max_temp_tomorrow: int | None = None, 
                   min_temp_tomorrow: int | None = None, 
                   min_wind_tomorrow: int | None = None, 
                   max_wind_tomorrow: int | None = None,
                   precipitation_now: str = None,
                   precips: str | None  = None):
        return {
            'Date' : dt.datetime.now(),
            'City' : city,
            'Source': source_name,
            # Current data
            'TemperatureNow': temp,
            'PressureNow': pres,
            'HumidityNow': hum,
            'UvIndexNow': uv_index_now,
            'PrecipitationTypeNow': precipitation_now,
            # end of current data
            # Air quality and pollutants concentrations in ug/m3
            'AirQualityIndexNow': air_quality_now,
            'PM2.5': pm25,
            'PM10': pm10,
            'NO2': no2_gas,
            'O3': o3_gas,
            'CO': co_gas,
            'SO2': so2_gas,
            # end of pollutants
            'MaxUvIndexTomorrow': max_uv_tomorrow,
            'MaxTempTomorrow': max_temp_tomorrow,
            'MinTempTomorrow': min_temp_tomorrow,
            'MaxWindTomorrow': max_wind_tomorrow,
            'MinWindTomorrow': min_wind_tomorrow,
            'DayPrecipitationTypesTomorrow': precips
        }