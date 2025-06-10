import re
from bs4 import BeautifulSoup
from providers.weather_provider import WeatherProvider

class AccuWeatherProvider(WeatherProvider):
    def __init__(self):
        super().__init__()
        self.provider_name = "AccuWeather"
        self.base_url = "https://www.accuweather.com"

    def get_location_key(self, city):
        url = f"{self.base_url}/web-api/autocomplete"
        params = {"query": city, "language": "ru"}
        resp = self.session.get(url, params=params)
        data = resp.json()
        if not data:
            raise ValueError(f"[AccuWeather] Город {city} не найден")
        return data[0]['key']

    def get_city_url(self, loc_key:str):
        url = f"{self.base_url}/web-api/three-day-redirect?key={loc_key}"
        current_resp = self.session.get(url, timeout=10)
        current_soup = BeautifulSoup(current_resp.text, "html.parser")
        return self.base_url + current_soup.select_one("a.cur-con-weather-card")['href']
        
    def fetch(self, city: str) -> dict:
        location_key = self.get_location_key(city)

        current_url = self.get_city_url(location_key)
        current_resp = self.session.get(current_url, timeout=10)
        current_soup = BeautifulSoup(current_resp.text, "html.parser")
        
        # Текущая температура
        try:
            temp_elem = current_soup.select_one("div.temp div.display-temp")
            temp_str = temp_elem.get_text(strip=True)
            temp_now = self._safe_int(temp_str) if temp_str else None
        except Exception as e:
            temp_now = None
            print(f"[{self.provider_name}] Ошибка чтения текущей температуры. Исключение: {e}")
            
        # Текущий тип погодных условий
        try:
            precip_elem = current_soup.select_one('div.current-weather div.phrase')
            precips_now = precip_elem.get_text(strip=True) if precip_elem else None
        except Exception as e:
            precips_now = None
            print(f"[{self.provider_name}] Ошибка чтения текущего типа погодных условий. Исключение: {e}")
        
        uv_now = 0
        humidity_now = None
        pressure_now = None
        wind_speed = None
        wind_direction = None
        try:    
            details_card =  current_soup.find('div', class_='current-weather-card')
            items = details_card.find_all('div', class_='detail-item')
            for item in items:
                if item:
                    if "Влажность" in item.text:
                        humid_str = re.search(r'\d+', item.text).group()
                        humidity_now = self._safe_int(humid_str)
                    if "Давление" in item.text:
                        pressure_str = re.search(r'\d{3,4}', item.text).group()
                        pressure_now = self._safe_int(pressure_str) // 1.333 if pressure_str else None
                    if "Макс. УФ-индекс" in item.text:
                        uv_str = re.search(r'\d+', item.text).group()
                        uv_now = self._safe_int(uv_str) if uv_str else 0
                    if "Ветер" in item.text:
                        wind_speed_str = re.search(r'(\d+) км/ч', item.text).group(1)
                        wind_speed = self._safe_int(wind_speed_str) if wind_speed_str else 0
                        wind_direction = re.search(r'([ЗВСЮ]{1,3}) \d+ км/ч', item.text).group(1)
        except Exception as e:
            print(f"[{self.provider_name}] Ошибка чтения текущих влажности, давления и УФ-индекса. Исключение: {e}")
        
        # Качество воздуха и загрязнители
        quality_url = current_url.replace("current-weather","air-quality-index")
        quality_resp = self.session.get(quality_url, timeout=10)
        quality_soup = BeautifulSoup(quality_resp.text, 'html.parser')
        
        aq_number = None
        pm25 = None
        pm10 = None
        no2_gas = None
        o3_gas = None
        co_gas = None
        so2_gas = None
        try:
            # Индекс качества воздуха
            aq_number_elem = quality_soup.select_one('div.aq-number')
            aq_number = self._safe_int(aq_number_elem.get_text(strip=True)) if aq_number_elem.get_text(strip=True).isdigit() else None
            
            # Загрязнители
            pollutant_elems = quality_soup.find_all('div', class_='pollutant-index')
            pm25 = self._safe_int(pollutant_elems[0].get_text(strip=True))
            no2_gas = self._safe_int(pollutant_elems[2].get_text(strip=True))
            o3_gas = self._safe_int(pollutant_elems[4].get_text(strip=True))
            pm10 = self._safe_int(pollutant_elems[6].get_text(strip=True))
            co_gas = self._safe_int(pollutant_elems[8].get_text(strip=True))
            so2_gas = self._safe_int(pollutant_elems[10].get_text(strip=True))  
        except Exception as e:
            print(f"[{self.provider_name}] Ошибка чтения качества и состава воздуха. Исключение: {e}")
        
        # Составляем агрегированные данные
        return self.make_dummy(self.provider_name, 
                               city=city,
                               timestamp=None,
                               
                               temp=temp_now, 
                               pres=pressure_now, 
                               hum=humidity_now, 
                               wind_speed=wind_speed,
                               wind_direction=wind_direction,
                               uv_index=uv_now,
                               precipitationTypes= precips_now,
                               air_quality_index= aq_number,
                               pm25=pm25, pm10=pm10, no2_gas=no2_gas, o3_gas=o3_gas, co_gas=co_gas, so2_gas=so2_gas,
                               )
        
    def fetch_forecast(self, city: str) -> dict:
        location_key = self.get_location_key(city)
        
        # Данные прогноза
        default_url = self.get_city_url(location_key) 
        forecast_url = default_url.replace("current-weather","weather-tomorrow")
        forecast_resp = self.session.get(forecast_url, timeout=10)
        forecast_soup = BeautifulSoup(forecast_resp.text, "html.parser")
        
        # Температура (дневная и ночная)
        try:
            temps_elems = forecast_soup.select("div.half-day-card-header__content div.weather div.temperature")
            temps_str = [re.search(r'\d+',elem.get_text(strip=True)).group() for elem in temps_elems]
            temps = [self._safe_int(temp_str) if temp_str and temp_str.isdigit() else None for temp_str in temps_str]
            max_temp, min_temp = temps
        except Exception as e:
            max_temp = min_temp = None
            print(f"[{self.provider_name}] Ошибка чтения максимальной и минимальной температуры воздуха на завтра. Исключение: {e}")
        
        # УФ-индекс
        max_uv_index = None
        try:
            elements = forecast_soup.find_all('p', class_='panel-item')
            if elements:
                for elem in elements:
                    if 'Макс. УФ-индекс' in elem.text:
                        uv_text = elem.find('span', class_='value').get_text()
                        uv_number = re.search(r'\d+', uv_text).group()
                        max_uv_index = self._safe_int(uv_number)
                        break
        except Exception as e:
            print(f"[{self.provider_name}] Ошибка чтения УФ-индекса на завтра. Исключение: {e}")
            
        # Скорость и направление ветра
        wind_speed_day = wind_speed_night = None
        wind_dir_day = wind_dir_night = None
        try:
            elements = forecast_soup.find_all('p', class_='panel-item')
            wind_speeds = []
            wind_dirs = []
            if elements:
                for elem in elements:
                    if 'Ветер' in elem.text:
                        wind_text = elem.find('span', class_='value').get_text()
                        wind_speed_number = int(re.search(r'\d+', wind_text).group())
                        wind_direction_str = re.search(r'[ВЗСЮ]{1,3}', wind_text).group()
                        wind_speeds.append(wind_speed_number)
                        wind_dirs.append(wind_direction_str)
            wind_speed_day = wind_speeds[0]
            wind_speed_night = wind_speeds[1]
            wind_dir_day = wind_dirs[0]
            wind_dir_night = wind_dirs[1]
        except Exception as e:
            print(f"[{self.provider_name}] Ошибка чтения скорости (км/ч) и направления ветра на завтра. Исключение: {e}")

        try:         
            precip_elems = forecast_soup.select("div.half-day-card-content div.phrase")
            day_precip = precip_elems[0].get_text(strip=True)
            night_precip = precip_elems[1].get_text(strip=True)
        except Exception as e:
            day_precip, night_precip = None
            print(f"[{self.provider_name}] Ошибка чтения типа погодных условий на завтра. Исключение: {e}")
            
        
        # Составляем агрегированные данные
        return self.make_forecast_dummy(self.provider_name, 
                               city=city,
                               timestamp=None,
                               
                               temp_day=max_temp,
                               temp_night=min_temp,
                               
                               wind_speed_day=wind_speed_day,
                               wind_speed_night=wind_speed_night,
                               wind_dir_day=wind_dir_day,
                               wind_dir_night=wind_dir_night,
                               
                               precips_day=day_precip,
                               precips_night=night_precip,
                               
                               max_uv_index=max_uv_index
                               )