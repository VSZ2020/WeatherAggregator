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

    def fetch(self, city: str) -> dict:
        location_key = self.get_location_key(city)

        # Текущие условия
        current_url = f"{self.base_url}/web-api/three-day-redirect?key={location_key}"
        current_resp = self.session.get(current_url, timeout=10)
        current_soup = BeautifulSoup(current_resp.text, "html.parser")
        new_url_elem = current_soup.select_one("a.cur-con-weather-card")
        # Update with new URL of city
        current_url = self.base_url + new_url_elem['href']
        current_resp = self.session.get(current_url, timeout=10)
        current_soup = BeautifulSoup(current_resp.text, "html.parser")
        
        # Current temperature
        try:
            temp_elem = current_soup.select_one("div.temp div.display-temp")
            temp_str = temp_elem.get_text(strip=True)
            temp_now = self._safe_int(temp_str) if temp_str else None
        except:
            temp_now = None
            
        # Current precip
        try:
            precip_elem = current_soup.select_one('div.current-weather div.phrase')
            precips_now = precip_elem.get_text(strip=True) if precip_elem else None
        except:
            precips_now = None
            
        details_items =  current_soup.select('div.current-weather-details div.detail-item')
        uv_now = self._safe_int(details_items[2].select('div')[1].get_text(strip=True)[0])
        humidity_now = self._safe_int(details_items[5].select('div')[1].get_text(strip=True).replace(" %",""))
        pressure_now = self._safe_int(details_items[7].select('div')[1].get_text(strip=True).replace(" мбар","").replace("↔ ","")) // 1.333
        
        # Air quality data
        quality_url = current_url.replace("current-weather","air-quality-index")
        quality_resp = self.session.get(quality_url, timeout=10)
        quality_soup = BeautifulSoup(quality_resp.text, 'html.parser')
        
        try:
            # Air Quality Number
            aq_number_elem = quality_soup.select_one('div.aq-number')
            aq_number = self._safe_int(aq_number_elem.get_text(strip=True)) if aq_number_elem.get_text(strip=True).isdigit() else None
            
            # PM2.5
            pollutant_elems = quality_soup.find_all('div', class_='pollutant-index')
            pm25 = self._safe_int(pollutant_elems[0].get_text(strip=True))
            no2_gas = self._safe_int(pollutant_elems[2].get_text(strip=True))
            o3_gas = self._safe_int(pollutant_elems[4].get_text(strip=True))
            pm10 = self._safe_int(pollutant_elems[6].get_text(strip=True))
            co_gas = self._safe_int(pollutant_elems[8].get_text(strip=True))
            so2_gas = self._safe_int(pollutant_elems[10].get_text(strip=True))  
        except:
            aq_number = None
            pm25 = None
            pm10 = None
            no2_gas = None
            o3_gas = None
            co_gas = None
            so2_gas = None
        
        # Forecast data 
        forecast_url = current_url.replace("current-weather","weather-tomorrow")
        forecast_resp = self.session.get(forecast_url, timeout=10)
        forecast_soup = BeautifulSoup(forecast_resp.text, "html.parser")
        
        # Tomorrow temperatures
        try:
            temps_elems = forecast_soup.select("div.half-day-card-header__content div.weather div.temperature")
            temps_str = [re.search(r'\d+',elem.get_text(strip=True)).group() for elem in temps_elems]
            temps = [self._safe_int(temp_str) if temp_str and temp_str.isdigit() else None for temp_str in temps_str]
            max_temp, min_temp = temps
        except:
            max_temp = min_temp = None
        
        # Tomorrow UV
        try:
            elements = forecast_soup.find_all('p', class_='panel-item')
            if elements:
                for elem in elements:
                    if 'Макс. УФ-индекс' in elem.text:
                        uv_text = elem.find('span', class_='value').get_text()
                        uv_number = re.search(r'\d+', uv_text).group()
                        max_uv_tomorrow = uv_number
                        break
        except:
            max_uv_tomorrow = None
            
        # Tomorrow winds
        try:
            elements = forecast_soup.find_all('p', class_='panel-item')
            winds = []
            if elements:
                for elem in elements:
                    if 'Ветер' in elem.text:
                        wind_speed_text = elem.find('span', class_='value').get_text()
                        wind_speed_number = re.search(r'\d+', wind_speed_text).group()
                        winds.append(wind_speed_number)
            max_wind = max(winds)
            min_wind = min(winds)
        except:
            max_wind = min_wind = None

        try:         
            precip_elems = forecast_soup.select("div.half-day-card-content div.phrase")
            day_precip = precip_elems[0].get_text(strip=True)
            night_precip = precip_elems[1].get_text(strip=True)
        except:
            day_precip, night_precip = None
            
        
        # Составляем агрегированные данные
        return self.make_dummy(self.provider_name, 
                               city=city,
                               temp=temp_now, 
                               pres=pressure_now, 
                               hum=humidity_now, 
                               uv_index_now=uv_now,
                               precipitation_now= precips_now,
                               air_quality_now= aq_number,
                               pm25=pm25, pm10=pm10, no2_gas=no2_gas, o3_gas=o3_gas, co_gas=co_gas, so2_gas=so2_gas,
                               max_uv_tomorrow= max_uv_tomorrow,
                               max_temp_tomorrow=max_temp, 
                               min_temp_tomorrow=min_temp, 
                               max_wind_tomorrow=max_wind, 
                               min_wind_tomorrow=min_wind, 
                               precips=f"{day_precip} / {night_precip}")