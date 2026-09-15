import threading
from collections import deque
from .battery import SimulatedBattery
from .config import load_config
cfg=load_config()
lock=threading.Lock()
battery=SimulatedBattery(float(cfg["capacity_kwh"]),float(cfg["max_power_kw"]),float(cfg["min_soc"]),
 float(cfg["max_soc"]),float(cfg["initial_soc"]),float(cfg["efficiency"]))
state={"mqtt_connected":False,"mqtt_status":"STARTING","mqtt_step":"STARTING","mqtt_error":None,"messages":0,"last_update":None,"pload_kw":0.0,"pext_kw":0.0,
 "pload_phases_kw":{"L1":0.0,"L2":0.0,"L3":0.0},"pext_phases_kw":{"L1":0.0,"L2":0.0,"L3":0.0},
 "battery":battery.snapshot(),"peak_limit_kw":float(cfg["peak_limit_kw"]),"mode":"LIVE MQTT + SIMULATED BATTERY",
 "history":deque(maxlen=600)}
def snapshot():
    with lock:
        out={k:v for k,v in state.items() if k!="history"}; out["history"]=list(state["history"]); return out
