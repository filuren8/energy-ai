import threading
from collections import deque
from datetime import datetime, timezone
from .battery import SimulatedBattery
from .config import settings

lock = threading.Lock()
battery = SimulatedBattery(settings.capacity_kwh, settings.max_power_kw, settings.min_soc,
                           settings.max_soc, settings.initial_soc, settings.efficiency)
state = {
    "mqtt_connected": False, "mqtt_error": None, "messages": 0, "last_update": None,
    "pload_kw": 0.0, "pext_kw": 0.0,
    "pload_phases_kw": {"L1":0.0,"L2":0.0,"L3":0.0},
    "pext_phases_kw": {"L1":0.0,"L2":0.0,"L3":0.0},
    "battery": battery.snapshot(), "peak_limit_kw": settings.peak_limit_kw,
    "mode": "LIVE MQTT + SIMULATED BATTERY",
    "history": deque(maxlen=600)
}

def snapshot():
    with lock:
        out = {k:v for k,v in state.items() if k != "history"}
        out["history"] = list(state["history"])
        return out
