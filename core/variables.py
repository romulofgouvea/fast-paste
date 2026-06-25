import json
import os
from configs.config import DATA_DIR

VARIABLES_FILE = os.path.join(DATA_DIR, "variables.json")

def load_variables():
    if not os.path.exists(VARIABLES_FILE):
        return {}
    try:
        with open(VARIABLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in data.items():
                if isinstance(v, str):
                    data[k] = {"value": v, "is_secret": False}
            return data
    except Exception as e:
        print(f"[Variables] Erro ao carregar variables.json: {e}")
        return {}

def save_variables(vars_dict):
    try:
        with open(VARIABLES_FILE, "w", encoding="utf-8") as f:
            json.dump(vars_dict, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving variables: {e}")

def add_variable(name, value, is_secret=False):
    vars_dict = load_variables()
    # Remove prefix / if added
    if name.startswith('/'):
        name = name[1:]
    vars_dict[name] = {"value": value, "is_secret": is_secret}
    save_variables(vars_dict)

def remove_variable(name):
    vars_dict = load_variables()
    if name.startswith('/'):
        name = name[1:]
    if name in vars_dict:
        del vars_dict[name]
        save_variables(vars_dict)
