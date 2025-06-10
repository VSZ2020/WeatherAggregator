import time, random, re
from bs4 import BeautifulSoup
from providers.weather_provider import WeatherProvider

class GismeteoProvider(WeatherProvider):
    def __init__(self):
        super().__init__()
        self.provider_name = "Gismeteo"
        self.base_url = "https://www.gismeteo.ru"

    def _get_city_url(self, city_name):
        url = f"{self.base_url}/mq/city/q/{city_name}"
        resp = self.session.get(url, timeout=10)
        data = resp.json()

        if not data:
            raise ValueError(f"Город '{city_name}' не найден")

        slug = data[0].get("slug")
        geo_id = data[0].get("id")

        if not slug or not geo_id:
            raise ValueError(f"[Gismeteo] Не удалось получить slug или id для города '{city_name}'")
        
        city_url = f"{self.base_url}/weather-{slug}-{geo_id}"
        print(f"[{self.provider_name}] Получен URL города {city_name}: {city_url}")
        return city_url
    
    
    def fetch(self, city: str) -> dict:
        city_url = self._get_city_url(city)
        
        # Имитация "живого" клиента
        time.sleep(random.uniform(0.5, 1.5))

        current_url = f"{city_url}/now"
        current_resp = self.session.get(current_url, timeout=10)
        current_soup = BeautifulSoup(current_resp.text, "html.parser")

        # Фактическая температура воздуха
        temp_now = None
        try:
            temp_tag = current_soup.select_one("div.now-weather temperature-value")
            temp_now = int(temp_tag['value']) if temp_tag and temp_tag.has_attr('value') else None
        except Exception as e:
            print(f"[{self.provider_name}] Не удалось прочитать текущее значение температуры. Исключение: {e}")

        # Текущее давление
        pressure_now = None
        try:
            pressure_tag = current_soup.select_one("pressure-value")
            pressure_now = int(pressure_tag['value']) if pressure_tag and pressure_tag.has_attr('value') else None
        except Exception as e:
            print(f"[{self.provider_name}] Не удалось прочитать текущее значение давления. Исключение: {e}")

        humidity_now = None
        try:
            for block in current_soup.select("div.now-info-item"):
                title = block.select_one(".item-title")
                if title and "влажность" in title.text.lower():
                    value = block.select_one(".item-value")
                    humidity_now = int(value.text.strip()) if value else None
                    break
        except Exception as e:
            print(f"[{self.provider_name}] Не удалось прочитать текущее значение влажности. Исключение: {e}")

        wind_now = None
        wind_dir = None
        try:
            for block in current_soup.select("div.now-info-item"):
                title = block.select_one(".item-title")
                if title and "ветер" in title.text.lower():
                    value = block.select_one("div.item-value speed-value")
                    dir = block.select_one("div.item-measure")
                    wind_now = int(int(value['value'])*3.6) if value else None
                    wind_dir = dir.get_text(strip=True) if dir else None
                    break
        except Exception as e:
            print(f"[{self.provider_name}] Не удалось прочитать текущее значение скорости и направления ветра. Исключение: {e}")
        
        # Фактические погодные условия
        precips_now = None
        try:
            precips_tag = current_soup.select_one("div.now-desc")
            precips_now = precips_tag.get_text(strip=True).lower() if precips_tag else None
        except Exception as e:
            print(f"[{self.provider_name}] Не удалось прочитать текущее значение погодных условий. Исключение: {e}")
        
        return self.make_dummy(self.provider_name,
                               city=city,
                               timestamp=None,
                                
                               temp=temp_now, 
                               pres=pressure_now, 
                               hum=humidity_now,
                               precipitationTypes=precips_now, 
                               wind_speed=wind_now,
                               wind_direction=wind_dir)
            
        
    def fetch_forecast(self, city: str) -> dict:
        city_url = self._get_city_url(city)
        time.sleep(random.uniform(0.3, 1.2))
        
        forecast_url = f"{city_url}/3-days"
        forecast_resp = self.session.get(forecast_url, timeout=10)
        forecast_soup = BeautifulSoup(forecast_resp.text, "html.parser")

        # Температура на завтра
        temp_morn = temp_day = temp_even = temp_night = None
        try:
            # Вторая колонка прогноза на завтра
            temp_items = forecast_soup.select(".widget-row-chart-temperature-air .value temperature-value")

            temps = []
            for temp_item in temp_items:
                temp = self._safe_int(temp_item['value'])
                temps.append(temp)
            day_chunks = [temps[i:i+4] for i in range(0,12,4)]
            temp_morn, temp_day, temp_even, temp_night = day_chunks[1]
        except Exception as e:
            print(f"[{self.provider_name}] Ошибка в текущей температуре. Исключение: {e}")

        # Тип осадков
        precip_morn = precip_day = precip_even = precip_night = None
        try:
            weather_icons = forecast_soup.select(".widget-row-icon .row-item")
            precipitation_per_day = [icon["data-tooltip"] for icon in weather_icons[:12]]
            precipitation_day_chunks = [precipitation_per_day[i:i+4] for i in range(0, 12, 4)]
            precip_morn, precip_day, precip_even, precip_night = precipitation_day_chunks[1]
        except Exception as e:
            print(f"[{self.provider_name}] Ошибка парсинга осадков. Исключение: {e}")

        # Скорость ветра на завтра
        wind_speed_morn = wind_speed_day = wind_speed_even = wind_speed_night = None
        try:
            wind_elements = forecast_soup.select(".widget-row-wind .row-item .wind-speed speed-value")
            wind_speeds = [int(int(el['value']) * 3.6) for el in wind_elements[:12]]
            wind_chunks = [wind_speeds[i:i+4] for i in range(0, 12, 4)]
            wind_speed_morn, wind_speed_day, wind_speed_even, wind_speed_night = wind_chunks[1]
        except Exception as e:
            print(f"[{self.provider_name}] Ошибка парсинга значений скорости ветра. Исключение: {e}")
            
        # Направление ветра на завтра
        wind_dir_morn = wind_dir_day = wind_dir_even = wind_dir_night = None
        try:
            wind_elements = forecast_soup.select(".widget-row-wind .row-item .wind-speed .wind-direction")
            wind_dirs = []
            for el in wind_elements[:12]:
                text = el.get_text(strip=True)
                if text and '—' in text.lower():
                    wind_dirs.append("штиль")
                    continue
                w = re.search(r'[ВЗСЮ—]{1,3}',text).group()
                wind_dirs.append(w)
            wind_chunks = [wind_dirs[i:i+4] for i in range(0, 12, 4)]
            wind_dir_morn, wind_dir_day, wind_dir_even, wind_dir_night = wind_chunks[1]
        except Exception as e:
            print(f"[{self.provider_name}] Ошибка парсинга значений направления ветра. Исключение: {e}")
        
        
        # Давление на завтра
        press_morn = press_day = press_even = press_night = None
        try:
            pressure_elements = forecast_soup.select(".widget-row-chart-pressure .values .value pressure-value")
            pressures = [int(el['value']) for el in pressure_elements[:12]]
            pressure_chunks = [pressures[i:i+4] for i in range(0, 12, 4)]
            press_morn, press_day, press_even, press_night = pressure_chunks[1]
        except Exception as e:
            print(f"[{self.provider_name}] Ошибка парсинга значений давления на завтра. Исключение: {e}")
            
        # Влажность на завтра
        humid_morn = humid_day = humid_even = humid_night = None
        try:
            humid_elements = forecast_soup.select(".widget-row-humidity .row-item")
            humidities = [int(el.get_text(strip=True)) for el in humid_elements[:12]]
            humid_chunks = [humidities[i:i+4] for i in range(0, 12, 4)]
            humid_morn, humid_day, humid_even, humid_night = humid_chunks[1]
        except Exception as e:
            print(f"[{self.provider_name}] Ошибка парсинга значений давления на завтра. Исключение: {e}")

        # УФ-индекс на завтра
        max_uv = min_uv = None
        try:
            uv_elements = forecast_soup.select(".widget-row-radiation .row-item")
            uvs = [int(el.get_text(strip=True)) for el in uv_elements[:12]]
            uv_chunks = [uvs[i:i+4] for i in range(0, 12, 4)]
            max_uv = max(uv_chunks[1])
            min_uv = min(uv_chunks[1])
        except Exception as e:
            print(f"[{self.provider_name}] Ошибка парсинга значений давления на завтра. Исключение: {e}")

        return self.make_forecast_dummy(self.provider_name, 
                                city=city,
                                timestamp=None,

                                temp_morn=temp_morn,
                                temp_day=temp_day,
                                temp_even=temp_even,
                                temp_night=temp_night,
                                
                                humid_morn=humid_morn,
                                humid_day=humid_day,
                                humid_even=humid_even,
                                humid_night=humid_night,
                                
                                pres_morn=press_morn,
                                pres_day=press_day,
                                pres_even=press_even,
                                pres_night=press_night,
                                
                                wind_speed_morn=wind_speed_morn,
                                wind_speed_day=wind_speed_day,
                                wind_speed_even=wind_speed_even,
                                wind_speed_night=wind_speed_night,
                                
                                wind_dir_morn=wind_dir_morn,
                                wind_dir_day=wind_dir_day,
                                wind_dir_even=wind_dir_even,
                                wind_dir_night=wind_dir_night,
                                
                                max_uv_index=max_uv,
                                min_uv_index=min_uv,
                                
                                precips_morn=precip_morn,
                                precips_day=precip_day,
                                precips_even=precip_even,
                                precips_night=precip_night)