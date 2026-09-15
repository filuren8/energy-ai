import json, socket, threading, time
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
from .config import load_config
from .state import state, lock, battery

TOPIC="extapi/data/ehub"
client=None
connect_generation=0

def _set(status,error=None,step=None):
    with lock:
        state["mqtt_status"]=status
        state["mqtt_connected"]=(status=="LIVE")
        state["mqtt_error"]=error
        if step is not None: state["mqtt_step"]=step

def _phases(payload,key):
    d=payload.get(key,{})
    return {p:float(d.get(p,0.0))/1000.0 for p in ("L1","L2","L3")}

def _connect_worker(generation):
    global client
    cfg=load_config(); host=cfg["mqtt_host"]; port=int(cfg["mqtt_port"])
    user=cfg.get("mqtt_username",""); password=cfg.get("mqtt_password","")
    _set("TESTING",None,f"TCP TEST {host}:{port}")
    try:
        with socket.create_connection((host,port),timeout=4): pass
    except Exception as e:
        _set("NETWORK_ERROR",f"{type(e).__name__}: {e}","TCP FAILED"); return

    connected=threading.Event()
    c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id="energy-ai-live",protocol=mqtt.MQTTv311)
    if user: c.username_pw_set(user,password)

    def on_connect(cl,userdata,flags,reason_code,properties):
        if generation!=connect_generation:return
        if reason_code.value == 0:
            _set("SUBSCRIBING",None,"CONNACK SUCCESS → SUBSCRIBE extapi/data/ehub")
            result,_=cl.subscribe(TOPIC,qos=0)
            if result!=mqtt.MQTT_ERR_SUCCESS:
                _set("SUBSCRIBE_ERROR",f"subscribe() returnerade {result}","SUBSCRIBE FAILED")
        else:
            _set("AUTH_ERROR",f"CONNACK {reason_code}","MQTT AUTH FAILED")
        connected.set()

    def on_subscribe(cl,userdata,mid,reason_codes,properties):
        if generation==connect_generation:
            _set("WAITING_DATA",None,"SUBSCRIBED → WAITING FOR FIRST RAW MESSAGE")

    def on_message(cl,userdata,msg):
        if generation!=connect_generation:return
        raw=msg.payload.decode("utf-8",errors="replace")
        with lock:
            state["mqtt_raw_topic"]=msg.topic
            state["mqtt_raw_preview"]=raw[:1000]
            state["mqtt_raw_bytes"]=len(msg.payload)
        try:
            payload=json.loads(raw); pload=_phases(payload,"pload"); pext=_phases(payload,"pext")
            load_kw=sum(pload.values()); grid_kw=sum(pext.values())
            peak=float(cfg["peak_limit_kw"]); maxp=float(cfg["max_power_kw"])
            discharge=min(max(0.0,grid_kw-peak),maxp,max(0.0,load_kw))
            batt=battery.update(discharge); now=datetime.now(timezone.utc).isoformat()
            with lock:
                state.update({"mqtt_connected":True,"mqtt_status":"LIVE","mqtt_step":"RAW DATA RECEIVED → PARSED",
                  "mqtt_error":None,"messages":state["messages"]+1,"last_update":payload.get("ts",{}).get("val",now),
                  "pload_kw":round(load_kw,3),"pext_kw":round(grid_kw,3),"pload_phases_kw":pload,
                  "pext_phases_kw":pext,"battery":batt,"peak_limit_kw":peak})
                state["history"].append({"t":now,"load":round(load_kw,3),"grid":round(grid_kw,3),"battery":batt["power_kw"],"soc":batt["soc"]})
        except Exception as e:
            _set("RAW_DATA",f"Rådata mottagen men kunde inte tolkas: {e}","RAW DATA RECEIVED → PARSE FAILED")

    def on_connect_fail(cl,userdata):
        if generation==connect_generation:_set("CONNECTION_ERROR","MQTT connect failed","MQTT CONNECT FAILED")

    c.on_connect=on_connect;c.on_subscribe=on_subscribe;c.on_message=on_message;c.on_connect_fail=on_connect_fail
    client=c
    _set("CONNECTING",None,"TCP OK → MQTT CONNECT (verified blocking flow)")
    try:
        # Use the same connect path that the diagnostic client has proven works.
        rc=c.connect(host,port,keepalive=30)
        if rc!=mqtt.MQTT_ERR_SUCCESS:
            _set("CONNECTION_ERROR",f"connect() returnerade {rc}","MQTT CONNECT FAILED")
            return
        c.loop_start()
        if not connected.wait(8) and generation==connect_generation:
            _set("MQTT_TIMEOUT","Ingen CONNACK inom 8 sekunder.","MQTT CONNECT TIMEOUT")
            return
        time.sleep(8)
        if generation==connect_generation:
            with lock: status=state.get("mqtt_status")
            if status=="WAITING_DATA":
                _set("NO_DATA",f"CONNACK och SUBSCRIBE lyckades men ingen data kom på {TOPIC} inom 8 sekunder.","MQTT OK → SUBSCRIBED → NO DATA")
    except Exception as e:
        _set("CONNECTION_ERROR",f"{type(e).__name__}: {e}","MQTT CONNECT FAILED")

def reconnect_background():
    global connect_generation,client
    connect_generation+=1; generation=connect_generation
    if client:
        try:client.disconnect();client.loop_stop()
        except Exception:pass
    threading.Thread(target=_connect_worker,args=(generation,),daemon=True,name="ferroamp-mqtt").start()

def start_mqtt():
    cfg=load_config()
    if not cfg.get("mqtt_username") or not cfg.get("mqtt_password"):
        _set("NOT_CONFIGURED","Fyll i Ferroamp-användarnamn och lösenord.","WAITING FOR SETTINGS");return None
    reconnect_background();return None
