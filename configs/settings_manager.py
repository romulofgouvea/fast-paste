import os
import json
from configs.config import DATA_DIR, MAX_HISTORY, DEFAULT_SETTINGS

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

class SettingsManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        self.load()

    def load(self):
        self.settings = DEFAULT_SETTINGS.copy()
        
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                print(f"[FastPaste] Error loading settings: {e}")

    def save(self):
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"[FastPaste] Error saving settings: {e}")

    def get(self, key, default=None):
        if default is None:
            default = DEFAULT_SETTINGS.get(key)
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def update_settings(self, new_settings: dict):
        self.settings.update(new_settings)
        self.save()

# Global instance for easy access
settings = SettingsManager()
