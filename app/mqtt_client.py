import json, socket, threading, time
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
from .config import load_config
from .state import state, lock, battery
TOPIC="extapi/data/ehub"; client=None; connect_generation=0
def _set_status(status,error=None,step=None):
    with lock:
        state["mqtt_status"]=status; state["mqtt_connected"]=(status=="LIVE"); state["mqtt_error"]=error
        if step is not None: state["mqtt_step"]=step
def _phases(payload,key):
    d=payload.get(key,{})
    return {p:float(d.get(p,0.0))/1000.0 for p in ("L1","L2","L3")}
def on_connect(c,userdata,flags,reason_code,properties):
    if int(reason_code)==0:
        _set_status("SUBSCRIBING",None,"MQTT AUTH OK → SUBSCRIBE"); result,_=c.subscribe(TOPIC)
        if result!=mqtt.MQTT_ERR_SUCCESS:_set_status("SUBSCRIBE_ERROR",f"Kunde inte prenumerera på {TOPIC}: {result}","SUBSCRIBE FAILED")
    else:_set_status("AUTH_ERROR",f"MQTT nekade anslutningen: {reason_code}. Kontrollera användarnamn/lösenord.","MQTT AUTH FAILED")
def on_subscribe(c,userdata,mid,reason_codes,properties):_set_status("WAITING_DATA",None,f"SUBSCRIBED → väntar på {TOPIC}")
def on_connect_fail(c,userdata):_set_status("CONNECTION_ERROR","Kunde inte etablera MQTT-anslutning.","MQTT CONNECT FAILED")
def on_disconnect(c,userdata,disconnect_flags,reason_code,properties):
    if int(reason_code)!=0:_set_status("DISCONNECTED",f"MQTT frånkopplad: {reason_code}","DISCONNECTED")
def on_message(c,userdata,msg):
    try:
        cfg=load_config(); payload=json.loads(msg.payload.decode("utf-8")); pload=_phases(payload,"pload"); pext=_phases(payload,"pext")
        load_kw=sum(pload.values()); grid_kw=sum(pext.values()); peak=float(cfg["peak_limit_kw"]); maxp=float(cfg["max_power_kw"])
        discharge=min(max(0.0,grid_kw-peak),maxp,max(0.0,load_kw)); batt=battery.update(discharge); now=datetime.now(timezone.utc).isoformat()
        with lock:
            state.update({"mqtt_connected":True,"mqtt_status":"LIVE","mqtt_step":"DATA RECEIVED","mqtt_error":None,"messages":state["messages"]+1,
              "last_update":payload.get("ts",{}).get("val",now),"pload_kw":round(load_kw,3),"pext_kw":round(grid_kw,3),
              "pload_phases_kw":pload,"pext_phases_kw":pext,"battery":batt,"peak_limit_kw":peak})
            state["history"].append({"t":now,"load":round(load_kw,3),"grid":round(grid_kw,3),"battery":batt["power_kw"],"soc":batt["soc"]})
    except Exception as e:_set_status("PAYLOAD_ERROR",f"Payload-fel: {e}","DATA PARSE FAILED")
def _watchdog(generation):
    time.sleep(8)
    if generation!=connect_generation:return
    with lock:status=state.get("mqtt_status")
    if status in ("CONNECTING","TCP_OK"):_set_status("MQTT_TIMEOUT","TCP fungerar, men EnergyHub svarade inte på MQTT CONNECT inom 8 sekunder.","TCP OK → MQTT CONNECT TIMEOUT")
    elif status in ("SUBSCRIBING","WAITING_DATA"):
        time.sleep(4)
        if generation!=connect_generation:return
        with lock:status2=state.get("mqtt_status")
        if status2 in ("SUBSCRIBING","WAITING_DATA"):_set_status("NO_DATA",f"MQTT ansluten men ingen data mottogs på {TOPIC}.","MQTT OK → NO DATA")
def reconnect():
    global client, connect_generation
    cfg = load_config()
    host = cfg["mqtt_host"]
    port = int(cfg["mqtt_port"])
    connect_generation += 1
    generation = connect_generation
    if client:
        try:
            client.disconnect()
            client.loop_stop()
        except Exception:
            pass
    _set_status("TESTING", None, f"TCP TEST {host}:{port}")
    try:
        with socket.create_connection((host, port), timeout=4):
            pass
        _set_status("TCP_OK", None, "TCP OK → MQTT CONNECT")
    except socket.timeout:
        _set_status("NETWORK_ERROR", f"Timeout mot {host}:{port}.", "TCP FAILED")
        return None
    except OSError as e:
        _set_status("NETWORK_ERROR", f"Kan inte nå {host}:{port}: {e}", "TCP FAILED")
        return None

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="", protocol=mqtt.MQTTv311)
    if cfg.get("mqtt_username"):
        client.username_pw_set(cfg["mqtt_username"], cfg.get("mqtt_password", ""))
    client.on_connect = on_connect
    client.on_connect_fail = on_connect_fail
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    _set_status("CONNECTING", None, "TCP OK → MQTT 3.1.1 CONNECT")
    try:
        rc = client.connect(host, port, keepalive=30)
        if rc != mqtt.MQTT_ERR_SUCCESS:
            _set_status("CONNECTION_ERROR", f"MQTT connect() returnerade {rc}", "MQTT CONNECT FAILED")
            return client
        client.loop_start()
        threading.Thread(target=_watchdog, args=(generation,), daemon=True).start()
    except Exception as e:
        _set_status("CONNECTION_ERROR", str(e), "MQTT CONNECT FAILED")
    return client

def reconnect_background():
    # Never let a slow/non-responsive MQTT broker block the web UI.
    threading.Thread(target=reconnect, daemon=True, name="mqtt-connect").start()
    return None

def start_mqtt():
    cfg=load_config()
    if not cfg.get("mqtt_username"):
        _set_status("NOT_CONFIGURED","Fyll i Ferroamp-användarnamn och lösenord.","WAITING FOR SETTINGS")
        return None
    return reconnect_background()
