import json
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
from .config import load_config
from .state import state, lock, battery

TOPIC = "extapi/data/ehub"
client = None

def _phases(payload, key):
    d = payload.get(key, {})
    return {p: float(d.get(p, 0.0)) / 1000.0 for p in ("L1","L2","L3")}

def on_connect(c, userdata, flags, reason_code, properties):
    ok = int(reason_code) == 0
    with lock:
        state["mqtt_connected"] = ok
        state["mqtt_error"] = None if ok else f"MQTT connect failed: {reason_code}"
    if ok: c.subscribe(TOPIC)

def on_disconnect(c, userdata, disconnect_flags, reason_code, properties):
    with lock: state["mqtt_connected"] = False

def on_message(c, userdata, msg):
    try:
        cfg=load_config()
        payload=json.loads(msg.payload.decode("utf-8"))
        pload=_phases(payload,"pload"); pext=_phases(payload,"pext")
        load_kw=sum(pload.values()); grid_kw=sum(pext.values())
        peak=float(cfg["peak_limit_kw"]); maxp=float(cfg["max_power_kw"])
        discharge=min(max(0.0,grid_kw-peak),maxp,max(0.0,load_kw))
        batt=battery.update(discharge)
        now=datetime.now(timezone.utc).isoformat()
        with lock:
            state.update({"mqtt_connected":True,"mqtt_error":None,"messages":state["messages"]+1,
              "last_update":payload.get("ts",{}).get("val",now),"pload_kw":round(load_kw,3),
              "pext_kw":round(grid_kw,3),"pload_phases_kw":pload,"pext_phases_kw":pext,
              "battery":batt,"peak_limit_kw":peak})
            state["history"].append({"t":now,"load":round(load_kw,3),"grid":round(grid_kw,3),
              "battery":batt["power_kw"],"soc":batt["soc"]})
    except Exception as e:
        with lock: state["mqtt_error"]=f"Payload error: {e}"

def reconnect():
    global client
    cfg=load_config()
    if client:
        try: client.disconnect(); client.loop_stop()
        except Exception: pass
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id="energy-ai-v02")
    if cfg.get("mqtt_username"):
        client.username_pw_set(cfg["mqtt_username"],cfg.get("mqtt_password",""))
    client.on_connect=on_connect; client.on_disconnect=on_disconnect; client.on_message=on_message
    with lock:
        state["mqtt_connected"]=False; state["mqtt_error"]=None
    try:
        client.connect_async(cfg["mqtt_host"],int(cfg["mqtt_port"]),keepalive=30); client.loop_start()
    except Exception as e:
        with lock: state["mqtt_error"]=str(e)
    return client

def start_mqtt(): return reconnect()
