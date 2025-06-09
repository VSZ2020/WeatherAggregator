import time, random
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

        return f"{self.base_url}/weather-{slug}-{geo_id}"

    def fetch(self, city: str) -> dict:
        # city_url = self._get_city_url(city)
        city_url = self._get_city_url(city)
        print(f"[Gismeteo] URL города: {city_url}")

        # Имитация "живого" клиента
        time.sleep(random.uniform(0.5, 1.5))

        current_url = f"{city_url}/now"
        forecast_url = f"{city_url}/3-days"

        current_resp = self.session.get(current_url, timeout=10)
        current_soup = BeautifulSoup(current_resp.text, "html.parser")

        try:
            temp_tag = current_soup.select_one("div.now-weather temperature-value")
            temp_now = int(temp_tag['value']) if temp_tag and temp_tag.has_attr('value') else None
        except:
            temp_now = None

        try:
            pressure_tag = current_soup.select_one("pressure-value")
            pressure_now = int(pressure_tag['value']) if pressure_tag and pressure_tag.has_attr('value') else None
        except:
            pressure_now = None

        try:
            humidity_now = None
            for block in current_soup.select("div.now-info-item"):
                title = block.select_one(".item-title")
                if title and "влажность" in title.text.lower():
                    value = block.select_one(".item-value")
                    humidity_now = int(value.text.strip()) if value else None
                    break
        except:
            humidity_now = None

        time.sleep(random.uniform(0.3, 1.2))

        forecast_resp = self.session.get(forecast_url, timeout=10)
        forecast_soup = BeautifulSoup(forecast_resp.text, "html.parser")

        # 1. Температура на завтра
        temp_min = temp_max = None
        try:
            # Вторая колонка прогноза на завтра
            temp_items = forecast_soup.select(".widget-row-chart-temperature-air .value temperature-value")

            temps = []
            for temp_item in temp_items:
                temp = temp_item['value'].replace("−", "-").replace("+", "").strip()
                temps.append(int(temp))
            day_chunks = [temps[i:i+4] for i in range(0,12,4)]
            # min_max_per_day = [(min(day),max(day)) for day in day_chunks]
            # temps = [int(t.text.replace("−", "-").replace("+", "").strip()) for t in temp_items if t.text.strip()]
            temp_min = min(day_chunks[1])
            temp_max = max(day_chunks[1])
        except Exception as e:
            print(f"[Gismeteo] Ошибка в текущей температуре: {e}")

        # 2. Тип осадков (data-tooltip)
        try:
            weather_icons = forecast_soup.select(".widget-row-icon .row-item")
            precipitation_per_day = [icon["data-tooltip"] for icon in weather_icons[:12]]
            precipitation_day_chunks = [precipitation_per_day[i:i+4] for i in range(0, 12, 4)]
            precipitation_summary = " / ".join(precipitation_day_chunks[1])
        except Exception as e:
            precipitation_summary = "не удалось получить"
            print(f"[Gismeteo] Ошибка парсинга осадков: {e}")

        # 3. Ветер на завтра
        try:
            wind_elements = forecast_soup.select(".widget-row-wind .row-item .wind-speed speed-value")
            wind_speeds = [int(el['value']) for el in wind_elements[:12]]
            wind_chunks = [wind_speeds[i:i+4] for i in range(0, 12, 4)]
            wind_max = max(wind_chunks[1])
            wind_min = min(wind_chunks[1])
            # wind_summary = " / ".join(wind_chunks[1])
        except Exception as e:
            wind_min = wind_max = None
            print(f"[Gismeteo] Ошибка парсинга ветра: {e}")

        return self.make_dummy(self.provider_name,
                               city=city, 
                               temp = temp_now, 
                               pres = pressure_now, 
                               hum = humidity_now, 
                               max_temp_tomorrow = temp_max, 
                               min_temp_tomorrow = temp_min, 
                               max_wind_tomorrow = wind_max, 
                               min_wind_tomorrow = wind_min, 
                               precips = precipitation_summary)