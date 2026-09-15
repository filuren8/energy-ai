import json, socket, threading, time
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
from .config import load_config
from .state import state, lock, battery

TOPIC="extapi/data/ehub"
client=None

def _set_status(status, error=None):
    with lock:
        state["mqtt_status"]=status
        state["mqtt_connected"]=(status=="LIVE")
        state["mqtt_error"]=error

def _phases(payload,key):
    d=payload.get(key,{})
    return {p:float(d.get(p,0.0))/1000.0 for p in ("L1","L2","L3")}

def on_connect(c,userdata,flags,reason_code,properties):
    if int(reason_code)==0:
        _set_status("LIVE",None); c.subscribe(TOPIC)
    else:
        _set_status("AUTH_ERROR",f"MQTT nekade anslutningen: {reason_code}. Kontrollera användarnamn/lösenord.")

def on_connect_fail(c,userdata):
    _set_status("CONNECTION_ERROR","Kunde inte ansluta till MQTT-brokern.")

def on_disconnect(c,userdata,disconnect_flags,reason_code,properties):
    if int(reason_code)!=0: _set_status("DISCONNECTED",f"MQTT frånkopplad: {reason_code}")

def on_message(c,userdata,msg):
    try:
        cfg=load_config(); payload=json.loads(msg.payload.decode("utf-8"))
        pload=_phases(payload,"pload"); pext=_phases(payload,"pext")
        load_kw=sum(pload.values()); grid_kw=sum(pext.values())
        peak=float(cfg["peak_limit_kw"]); maxp=float(cfg["max_power_kw"])
        discharge=min(max(0.0,grid_kw-peak),maxp,max(0.0,load_kw))
        batt=battery.update(discharge); now=datetime.now(timezone.utc).isoformat()
        with lock:
            state.update({"mqtt_connected":True,"mqtt_status":"LIVE","mqtt_error":None,
              "messages":state["messages"]+1,"last_update":payload.get("ts",{}).get("val",now),
              "pload_kw":round(load_kw,3),"pext_kw":round(grid_kw,3),"pload_phases_kw":pload,
              "pext_phases_kw":pext,"battery":batt,"peak_limit_kw":peak})
            state["history"].append({"t":now,"load":round(load_kw,3),"grid":round(grid_kw,3),
              "battery":batt["power_kw"],"soc":batt["soc"]})
    except Exception as e: _set_status("PAYLOAD_ERROR",f"Payload-fel: {e}")

def _tcp_precheck(host,port):
    _set_status("TESTING",None)
    try:
        with socket.create_connection((host,port),timeout=4):
            return True
    except socket.timeout:
        _set_status("NETWORK_ERROR",f"Timeout mot {host}:{port}. Kontrollera IP, port och att datorn är på samma nät.")
    except OSError as e:
        _set_status("NETWORK_ERROR",f"Kan inte nå {host}:{port}: {e}")
    return False

def reconnect():
    global client
    cfg=load_config(); host=cfg["mqtt_host"]; port=int(cfg["mqtt_port"])
    if client:
        try: client.disconnect(); client.loop_stop()
        except Exception: pass
    if not _tcp_precheck(host,port): return None
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id="energy-ai-v03")
    if cfg.get("mqtt_username"): client.username_pw_set(cfg["mqtt_username"],cfg.get("mqtt_password",""))
    client.on_connect=on_connect; client.on_connect_fail=on_connect_fail
    client.on_disconnect=on_disconnect; client.on_message=on_message
    try:
        _set_status("CONNECTING",None)
        client.connect_async(host,port,keepalive=30); client.loop_start()
    except Exception as e: _set_status("CONNECTION_ERROR",str(e))
    return client

def start_mqtt():
    cfg=load_config()
    if not cfg.get("mqtt_username"):
        _set_status("NOT_CONFIGURED","Fyll i Ferroamp-användarnamn och lösenord.")
        return None
    return reconnect()
