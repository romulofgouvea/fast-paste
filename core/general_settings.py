import sys
from configs.settings_manager import settings
from configs.config import DEFAULT_SETTINGS
from core import autostart

def get_hotkey():
    return settings.get('hotkey', DEFAULT_SETTINGS['hotkey'])

def set_hotkey(hotkey_str, mac_code=None):
    settings.set('hotkey', hotkey_str)
    if mac_code is not None:
        settings.set('hotkey_mac_key_code', mac_code)

def get_theme_color():
    return settings.get('theme_color', DEFAULT_SETTINGS['theme_color'])

def set_theme_color(color_hex):
    settings.set('theme_color', color_hex)

def is_autostart_enabled():
    try:
        return autostart.is_autostart_enabled()
    except Exception as e:
        print(f"[GeneralSettings] Error checking autostart: {e}")
        return False

def set_autostart_enabled(enabled):
    try:
        if enabled:
            return autostart.enable_autostart()
        else:
            return autostart.disable_autostart()
    except Exception as e:
        print(f"[GeneralSettings] Error setting autostart: {e}")
        return False

def get_interaction_mode():
    return settings.get('interaction_mode', DEFAULT_SETTINGS['interaction_mode'])

def set_interaction_mode(mode):
    settings.set('interaction_mode', mode)
