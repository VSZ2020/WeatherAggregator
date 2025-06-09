import re, time, random
from bs4 import BeautifulSoup
from providers.weather_provider import WeatherProvider

class YandexWeatherProvider(WeatherProvider):
    def __init__(self):
        super().__init__()
        self.provider_name = "Яндекс.Погода"
        self.base_url = "https://yandex.ru"
        self.base_weather_url = f"{self.base_url}/pogoda/ru/"

    def _get_city_coords(self, city_name):
        url = f"{self.base_url}/weather/api/suggest?part={city_name}&type=weather"
        resp = self.session.get(url, timeout=10)
        data = resp.json()

        if not data:
            raise ValueError(f"[Yandex Weather] Город '{city_name}' не найден")

        uri = data[0].get("uri")
        lon = data[0]['coords'].get("lon")
        lat = data[0]['coords'].get("lat")

        if not lat or not lon:
            raise ValueError(f"[Yandex Weather] Не удалось получить координаты города '{city_name}'")

        print(f"[Yandex Weather] Город '{city_name}' ({(lat, lon)})")
        return (lat,lon)
    
    
    def fetch(self, city: str) -> dict:
        lat, lon = self._get_city_coords(city)
        cityCoordsSuffix = f"?lon={lon}&lat={lat}"
        
        current_url = f"{self.base_weather_url}" + cityCoordsSuffix
        forecast_url = f"{self.base_weather_url}/details/3-day-weather" + cityCoordsSuffix
        
        # Имитация "живого" клиента
        time.sleep(random.uniform(0.5, 1.5))

        current_resp = self.session.get(current_url, timeout=10)
        current_soup = BeautifulSoup(current_resp.text, "html.parser")
        
        cur_temp_elem = current_soup.find('span', class_=lambda x: x and x.startswith("AppFactTemperature_value"))
        temp_now = self._safe_int(cur_temp_elem.get_text(strip=True).replace("°", "").replace("+", "")) if cur_temp_elem and cur_temp_elem.get_text(strip=True).isdigit() else None
        if not cur_temp_elem:
            print("[Yandex Weather] Отсутствуют данные о текущей температуре")
        
        details_elems = current_soup.find_all('li', class_=lambda x: x and x.startswith("AppFact_details__item"))

        if len(details_elems) < 3:
            print("[Yandex Weather] Отсутствуют детальные данные о погоде")
        
        pressure_now = self._safe_int(details_elems[1].get_text(strip=True)) if len(details_elems) > 1 else None
        humidity_now = self._safe_int(details_elems[2].get_text(strip=True).replace("%","")) if len(details_elems) > 2 else None
        
        day_cards = current_soup.find_all('a', class_=lambda x: x and x.startswith("AppForecastDay_dayCard"))
        today_card = None
        for card in day_cards:
            title = card.find("h3")
            if title and "Сегодня" in title.get_text():
                today_card = card
                break
        
        uv_index = None    
        if not today_card:
            print("[Yandex Weather] Карточка с данными на сегодня не найдена.")
        else:
            elems = today_card.find_all("div", class_=lambda s: s and s.startswith("AppForecastDayDuration_item"))
            for elem in elems:
                caption = elem.find('div', class_=lambda s: s and s.startswith("AppForecastDayDuration_caption"))
                if caption and "УФ-индекс" in caption.get_text(strip=True):
                    value_block = elem.find('div', class_=lambda s: s and s.startswith("AppForecastDayDuration_value"))
                    if value_block:
                        uv_str = re.search(r'\d+', value_block.get_text(strip=True)).group()
                        uv_index = int(uv_str) if uv_str else None
                        break
        
        
        time.sleep(random.uniform(0.5, 1.5))
        
        # Tomorrow weather
        forecast_resp = self.session.get(forecast_url, timeout=10)
        forecast_soup = BeautifulSoup(forecast_resp.text, "html.parser")

        tomorrow_card = None
        day_cards = forecast_soup.find_all("div", class_=lambda x: x and x.startswith("AppForecastDay_dayCard"))
        for card in day_cards:
            title = card.find("h3")
            if title and "Завтра" in title.get_text():
                tomorrow_card = card
                break

        if not tomorrow_card:
            print("[Yandex Weather] Прогноз на завтра не найден.")
        else:
            temps = []
            winds = []
            precip = []

            temps_elems = tomorrow_card.find_all("div", style=lambda s: s and "temp" in s)
            wind_elems = tomorrow_card.find_all("div", style=lambda s: s and "wind" in s)
            precip_elems = tomorrow_card.find_all("div", style=lambda s: s and "text" in s)

            # Temperature
            for t in temps_elems:
                temp = t.get_text(strip=True).replace("°", "").replace("+", "")
                if temp.isdigit():
                    temps.append(self._safe_int(temp))
            # Wind
            for w in wind_elems:
                wnd = w.get_text(strip=True)
                if wnd.isdigit():
                    winds.append(self._safe_int(wnd))
            # Precipitation 
            for p in precip_elems:
                text = p.get_text(strip=True)
                if text:
                    precip.append(text)
            
            temp_max = max(temps)
            temp_min = min(temps)
            wind_max = max(winds)
            wind_min = min(winds)
  
            return self.make_dummy(self.provider_name, 
                                   city=city,
                                   temp=temp_now, 
                                   pres=pressure_now, 
                                   hum=humidity_now, 
                                   uv_index_now=uv_index, 
                                   max_temp_tomorrow=temp_max, 
                                   min_temp_tomorrow=temp_min, 
                                   max_wind_tomorrow=wind_max, 
                                   min_wind_tomorrow=wind_min, 
                                   precips="/ ".join(precip))