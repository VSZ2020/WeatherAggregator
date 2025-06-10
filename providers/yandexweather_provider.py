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
            raise ValueError(f"[{self.provider_name}] Город '{city_name}' не найден")

        # uri = data[0].get("uri")
        lon = data[0]['coords'].get("lon")
        lat = data[0]['coords'].get("lat")

        if not lat or not lon:
            raise ValueError(f"[{self.provider_name}] Не удалось получить координаты города '{city_name}'")

        print(f"[{self.provider_name}] Найден город '{city_name}' с координатами (lat: {lat}, lon: {lon})")
        return (lat,lon)
    
    
    def fetch(self, city: str) -> dict:
        lat, lon = self._get_city_coords(city)
        cityCoordsSuffix = f"?lon={lon}&lat={lat}"
        
        current_url = f"{self.base_weather_url}" + cityCoordsSuffix
        
        # Имитация "живого" клиента
        time.sleep(random.uniform(0.5, 1.5))

        current_resp = self.session.get(current_url, timeout=10)
        current_soup = BeautifulSoup(current_resp.text, "html.parser")
       
        temp_now = None
        try:
            cur_temp_elem = current_soup.find('span', class_=lambda x: x and x.startswith("AppFactTemperature_value"))
            temp_now = self._safe_int(cur_temp_elem.get_text(strip=True).replace("°", "").replace("+", "")) if cur_temp_elem and cur_temp_elem.get_text(strip=True).isdigit() else None 
        except Exception as e:
            print(f"[{self.provider_name}] Отсутствуют данные о текущей температуре. Исключение: {e}") 
        
        pressure_now = humidity_now = None
        wind_speed = None
        wind_direction = None
        try:
            details_elems = current_soup.find_all('li', class_=lambda x: x and x.startswith("AppFact_details__item"))
            for elem in details_elems:
                if 'м/с' in elem.text:
                    wind_speed_str = re.search(r'\d+[,\d]*', elem.get_text(strip=True)).group()
                    wind_speed = float(wind_speed_str.replace(",",".")) if wind_speed_str else None # Скорость ветра в м/с
                    if wind_speed:
                        wind_speed = int(wind_speed * 3.6)  # Скорость ветра в км/ч            
                    wind_direction = re.search(r'[ВЗСЮ]+', elem.get_text(strip=True)).group()
            pressure_now = self._safe_int(details_elems[1].get_text(strip=True)) if len(details_elems) > 1 else None
            humidity_now = self._safe_int(details_elems[2].get_text(strip=True).replace("%","")) if len(details_elems) > 2 else None
        except Exception as e:
            print(f"[{self.provider_name}] Отсутствуют детальные данные о погоде (ветер, давление, влажность). Исключение: {e}")
        
        precipType = None
        try:
            precips_elem = current_soup.find('p', class_=lambda x: x and x.startswith('AppFact_warning'))
            if precips_elem:
                precipType = re.search(r'^(.*?)(?=, в ближайшие)', precips_elem.get_text(strip=True)).group(1)
        except Exception as e:
            print(f"[{self.provider_name}] Отсутствуют данные о погодных условиях. Исключение: {e}")
        
        day_cards = current_soup.find_all('a', class_=lambda x: x and x.startswith("AppForecastDay_dayCard"))
        today_card = None
        for card in day_cards:
            title = card.find("h3")
            if title and "Сегодня" in title.get_text():
                today_card = card
                break
        # УФ-индекс
        uv_index = None
        if not today_card:
            print(f"[{self.provider_name}] Карточка с данными на сегодня не найдена.")
        else:
            try:
                elems = today_card.find_all("div", class_=lambda s: s and s.startswith("AppForecastDayDuration_item"))
                for elem in elems:
                    caption = elem.find('div', class_=lambda s: s and s.startswith("AppForecastDayDuration_caption"))
                    if caption and "УФ-индекс" in caption.get_text(strip=True):
                        value_block = elem.find('div', class_=lambda s: s and s.startswith("AppForecastDayDuration_value"))
                        if value_block:
                            uv_str = re.search(r'\d+', value_block.get_text(strip=True)).group()
                            uv_index = int(uv_str) if uv_str else None
                            break
            except Exception as e:
                print(f"[{self.provider_name}] Карточка с данными на сегодня не найдена. Исключение: {e}")
        
        # Качество воздуха и загрязнители
        quality_url = f"{self.base_weather_url}/pollution" + cityCoordsSuffix
        current_resp = self.session.get(quality_url, timeout=10)
        current_soup = BeautifulSoup(current_resp.text, 'html.parser')
        
        aq_index = None
        try:
            aqi_elem = current_soup.find('div', class_=lambda x: x and x.startswith('AppPollutionWidgetMeter_value'))
            aq_index = self._safe_int(aqi_elem.get_text(strip=True))
        except Exception as e:
            print(f"[{self.provider_name}]. Не удалось получить данные о качестве воздуха. Исключение: {e}")
        
        pm25 = pm10 = no2 = so2 = co = o3 = None    
        try:
            pollutants_containers = current_soup.find_all('span', class_=lambda x: x and x.startswith('AppPollutionDetailsTitle_wrapper'))
            for container in pollutants_containers:
                span = container.find('span', class_=lambda x: x and x.startswith('AppPollutionDetailsTitle_subTitle__value'))
                if span:
                    if "NO2" in container.text:
                        no2 = self._safe_int(span.get_text(strip=True))
                        continue
                    if "PM10" in container.text:
                        pm10 = self._safe_int(span.get_text(strip=True))
                        continue    
                    if "SO2" in container.text:
                        so2 = self._safe_int(span.get_text(strip=True))
                        continue
                    if "O3" in container.text:
                        o3 = self._safe_int(span.get_text(strip=True))
                        continue 
                    if "PM2,5" in container.text:
                        pm25 = self._safe_int(span.get_text(strip=True))
                        continue
                    if "CO" in container.text:
                        co = self._safe_int(span.get_text(strip=True)) 
        except Exception as e:
            print(f"[{self.provider_name}]. Не удалось получить данные о качестве воздуха. Исключение: {e}")
        
        return self.make_dummy(self.provider_name,
                               city=city,
                               timestamp=None,
                                
                               temp=temp_now, 
                               pres=pressure_now, 
                               hum=humidity_now,
                               precipitationTypes=precipType, 
                               wind_speed=wind_speed,
                               wind_direction=wind_direction,
                                
                               air_quality_index=aq_index,
                               pm25=pm25,
                               pm10=pm10,
                               no2_gas=no2,
                               o3_gas=o3,
                               so2_gas=so2,
                               co_gas=co, 
                                
                               uv_index=uv_index)
            
        
    def fetch_forecast(self, city: str) -> dict:
        lat, lon = self._get_city_coords(city)
        cityCoordsSuffix = f"?lon={lon}&lat={lat}"
        
        forecast_url = f"{self.base_weather_url}/details/3-day-weather" + cityCoordsSuffix

        time.sleep(random.uniform(0.5, 1.5))
        
        # Прогноз на завтра
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
            print(f"[{self.provider_name}] Прогноз на завтра не найден.")
            return self.make_forecast_dummy(self.provider_name, city=city)
        
        temps = []
        humids=[]
        pressures=[]
        wind_speeds = []
        wind_dirs = []
        precips = []

        temps_elems = tomorrow_card.find_all("div", style=lambda s: s and "temp" in s)
        wind_speed_elems = tomorrow_card.find_all("div", style=lambda s: s and "wind" in s)
        wind_dir_elems = tomorrow_card.find_all("div", class_=lambda s: s and "AppForecastDayPart_direction__value" in s)
        precip_elems = tomorrow_card.find_all("div", style=lambda s: s and "text" in s)
        humid_elems = tomorrow_card.find_all("div", style=lambda s: s and "hum" in s)
        press_elems = tomorrow_card.find_all("div", style=lambda s: s and "press" in s)

        # Температура
        temp_morn = temp_day = temp_even = temp_night = None
        try:
            for t in temps_elems:
                temp = t.get_text(strip=True)
                if temp:
                    temps.append(self._safe_int(temp))
            temp_morn, temp_day, temp_even, temp_night = temps
        except Exception as e:
            print(f"[{self.provider_name}] Не удалось прочитать температуры на завтра. Исключение: {e}")
            
        # Скорость ветра
        wind_morn = wind_day = wind_even = wind_night = None
        try:
            for w in wind_speed_elems:
                wnd = w.get_text(strip=True)
                if wnd.isdigit():
                    wind_speeds.append(int(self._safe_int(wnd) * 3.6))
            wind_morn, wind_day, wind_even, wind_night = wind_speeds
        except Exception as e:
            print(f"[{self.provider_name}] Не удалось прочитать скорости ветра на завтра. Исключение: {e}")
            
        # Направления ветра
        wind_dir_morn = wind_dir_day = wind_dir_even = wind_dir_night = None
        try:
            for w in wind_dir_elems:
                wind_dirs.append(w.get_text(strip=True))
            wind_dir_morn, wind_dir_day, wind_dir_even, wind_dir_night = wind_dirs
        except Exception as e:
            print(f"[{self.provider_name}] Не удалось прочитать направления ветра на завтра. Исключение: {e}")
        
        # Влажность
        hum_morn = hum_day = hum_even = hum_night = None
        try:
            for h in humid_elems:
                humid_str = h.get_text(strip=True).replace("%","")
                if humid_str.isdigit():
                    humids.append(self._safe_int(humid_str))
            hum_morn, hum_day, hum_even, hum_night = humids
        except Exception as e:
            print(f"[{self.provider_name}] Не удалось прочитать значения влажности на завтра. Исключение: {e}")
        
        # Давление
        pres_morn = pres_day = pres_even = pres_night = None
        try:
            for p in press_elems:
                press_str = p.get_text(strip=True)
                if press_str.isdigit():
                    pressures.append(self._safe_int(press_str))
            pres_morn, pres_day, pres_even, pres_night = pressures
        except Exception as e:
            print(f"[{self.provider_name}] Не удалось прочитать значения давления на завтра. Исключение: {e}")
            
        # Условия погоды
        precip_morn = precip_day = precip_even = precip_night = None
        try: 
            for p in precip_elems:
                text = p.get_text(strip=True)
                if text:
                    precips.append(text)
            precip_morn, precip_day, precip_even, precip_night = precips
        except Exception as e:
            print(f"[{self.provider_name}] Не удалось прочитать значения условий погоды на завтра. Исключение: {e}")
        

        uv_index = None
        try:
            elems = tomorrow_card.find_all("div", class_=lambda s: s and s.startswith("AppForecastDayDuration_item"))
            for elem in elems:
                caption = elem.find('div', class_=lambda s: s and s.startswith("AppForecastDayDuration_caption"))
                if caption and "УФ-индекс" in caption.get_text(strip=True):
                    value_block = elem.find('div', class_=lambda s: s and s.startswith("AppForecastDayDuration_value"))
                    if value_block:
                        uv_str = re.search(r'\d+', value_block.get_text(strip=True)).group()
                        uv_index = int(uv_str) if uv_str else None
                        break
        except Exception as e:
            print(f"[{self.provider_name}] Карточка с данными на сегодня не найдена. Исключение: {e}")
        

        return self.make_forecast_dummy(self.provider_name, 
                                city=city,
                                timestamp=None,

                                temp_morn=temp_morn,
                                temp_day=temp_day,
                                temp_even=temp_even,
                                temp_night=temp_night,
                                
                                humid_morn=hum_morn,
                                humid_day=hum_day,
                                humid_even=hum_even,
                                humid_night=hum_night,
                                
                                pres_morn=pres_morn,
                                pres_day=pres_day,
                                pres_even=pres_even,
                                pres_night=pres_night,
                                
                                wind_speed_morn=wind_morn,
                                wind_speed_day=wind_day,
                                wind_speed_even=wind_even,
                                wind_speed_night=wind_night,
                                
                                wind_dir_morn=wind_dir_morn,
                                wind_dir_day=wind_dir_day,
                                wind_dir_even=wind_dir_even,
                                wind_dir_night=wind_dir_night,
                                
                                max_uv_index=uv_index,
                                
                                precips_morn=precip_morn,
                                precips_day=precip_day,
                                precips_even=precip_even,
                                precips_night=precip_night)