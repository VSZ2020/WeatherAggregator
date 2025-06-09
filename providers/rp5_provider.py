import re, time
from bs4 import BeautifulSoup
from providers.weather_provider import WeatherProvider
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class RP5Provider(WeatherProvider):
    def __init__(self):
        super().__init__()
        self.provider_name = "RP5"
        
    def fetch(self, city: str) -> dict:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        url = f"https://rp5.ru/Погода_в_{city}"
        driver.get(url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()
        try:
            temp = soup.select_one("span.t_0").text.strip()
            pressure = soup.select_one("span.p_0").text.strip()
            humidity = soup.select_one("span.h_0").text.strip()
        except:
            temp = pressure = humidity = None
        self.make_dummy(self.provider_name,
                        city=city, 
                        temp=temp,
                        pres=pressure, 
                        hum=humidity)