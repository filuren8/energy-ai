import json, os, sys
from pathlib import Path

def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()

CONFIG_PATH = app_dir() / "energyai-config.json"

DEFAULTS = {
    "mqtt_host": "192.168.68.59", "mqtt_port": 1883, "mqtt_username": "", "mqtt_password": "",
    "capacity_kwh": 15.0, "max_power_kw": 5.0, "min_soc": 10.0, "max_soc": 95.0,
    "initial_soc": 50.0, "efficiency": 0.95, "peak_limit_kw": 10.0
}

def load_config():
    data = DEFAULTS.copy()
    if CONFIG_PATH.exists():
        try:
            data.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass
    return data

def save_config(values):
    data = load_config()
    data.update(values)
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data
