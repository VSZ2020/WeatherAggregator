from bs4 import BeautifulSoup
from providers.weather_provider import WeatherProvider


class WeatherChannelProvider(WeatherProvider):
    def __init__(self):
        super().__init__()
        
    def fetch(self, city: str) -> dict:
        return self.make_dummy('Weather Channel',city=city)
