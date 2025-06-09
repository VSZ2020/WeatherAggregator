import os
import pandas as pd

class WeatherAggregator:
    def __init__(self, providers, excel_filename:str):
        self.providers = providers
        self.EXCEL_FILE = excel_filename

    def append_to_excel(self, df_new):
        # Если файл существует, читаем старые данные
        if os.path.exists(self.EXCEL_FILE):
            df_old = pd.read_excel(self.EXCEL_FILE)
            df_combined = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_combined = df_new

        # Сохраняем объединённую таблицу
        df_combined.to_excel(self.EXCEL_FILE, index=False)
    
    def collect_data(self, city: str):
        data = []
        for provider in self.providers:
            try:
                weather = provider.fetch(city)
                data.append(weather)
            except Exception as e:
                print(f"Ошибка у {provider.__class__.__name__}: {e}")
        return pd.DataFrame(data)
