from configs.settings_manager import settings
from configs.config import MAX_HISTORY, DEFAULT_SETTINGS
from core import variables

def get_max_history():
    return settings.get('max_history', DEFAULT_SETTINGS['max_history'])

def set_max_history(val):
    settings.set('max_history', val)

def get_retention_days():
    return settings.get('retention_days', DEFAULT_SETTINGS['retention_days'])

def set_retention_days(val):
    settings.set('retention_days', val)

def load_all_variables():
    return variables.load_variables()

def add_variable(name, value, is_secret=False):
    variables.add_variable(name, value, is_secret)

def remove_variable(name):
    variables.remove_variable(name)
