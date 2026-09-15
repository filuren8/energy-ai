import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    mqtt_host = os.getenv("FERROAMP_HOST", "192.168.68.59")
    mqtt_port = int(os.getenv("FERROAMP_PORT", "1883"))
    mqtt_username = os.getenv("FERROAMP_USERNAME", "")
    mqtt_password = os.getenv("FERROAMP_PASSWORD", "")
    capacity_kwh = float(os.getenv("BATTERY_CAPACITY_KWH", "15"))
    max_power_kw = float(os.getenv("BATTERY_MAX_POWER_KW", "5"))
    min_soc = float(os.getenv("BATTERY_MIN_SOC", "10"))
    max_soc = float(os.getenv("BATTERY_MAX_SOC", "95"))
    initial_soc = float(os.getenv("BATTERY_INITIAL_SOC", "50"))
    efficiency = float(os.getenv("BATTERY_EFFICIENCY", "0.95"))
    peak_limit_kw = float(os.getenv("PEAK_LIMIT_KW", "10"))

settings = Settings()
