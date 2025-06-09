import json

class SettingsManager:
    def __init__(self):
        self.SETTINGS_FILE = "settings.json"
        
        
    def load_settings(self):
        with open(self.SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)


    def save_settings(self, data):
        with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)