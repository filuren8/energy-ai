from contextlib import asynccontextmanager
from pathlib import Path
import sys, time, socket, ssl, json, threading
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import paho.mqtt.client as mqtt
from .mqtt_client import start_mqtt, reconnect_background
from .state import snapshot
from .config import load_config, save_config

mqtt_client=None
@asynccontextmanager
async def lifespan(app: FastAPI):
    global mqtt_client
    mqtt_client=start_mqtt(); yield
    if mqtt_client:
        try: mqtt_client.loop_stop()
        except Exception: pass

app=FastAPI(title="Energy AI",version="0.2.0",lifespan=lifespan)

class ConfigIn(BaseModel):
    mqtt_host:str
    mqtt_port:int=1883
    mqtt_username:str=""
    mqtt_password:str=""
    peak_limit_kw:float=10.0

@app.get("/api/state")
def api_state(): return snapshot()

@app.get("/api/config")
def get_config():
    c=load_config()
    return {"mqtt_host":c["mqtt_host"],"mqtt_port":c["mqtt_port"],"mqtt_username":c["mqtt_username"],
            "has_password":bool(c.get("mqtt_password")),"peak_limit_kw":c["peak_limit_kw"]}

@app.post("/api/config")
def set_config(x:ConfigIn):
    old=load_config()
    password=x.mqtt_password if x.mqtt_password else old.get("mqtt_password","")
    save_config({"mqtt_host":x.mqtt_host.strip(),"mqtt_port":x.mqtt_port,
                 "mqtt_username":x.mqtt_username.strip(),"mqtt_password":password,
                 "peak_limit_kw":x.peak_limit_kw})
    reconnect_background()
    return {"ok":True}

@app.get("/",response_class=HTMLResponse)
def dashboard():
    base=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parents[1]))
    return (base/"app"/"static"/"index.html").read_text(encoding="utf-8")


@app.post("/api/ferroamp-diagnostics")
def ferroamp_diagnostics():
    cfg=load_config()
    host=cfg["mqtt_host"]; user=cfg.get("mqtt_username",""); password=cfg.get("mqtt_password","")
    tests=[
        ("MQTT 3.1.1 / 1883 / empty client-id",1883,mqtt.MQTTv311,"",False),
        ("MQTT 3.1.1 / 1883 / named client-id",1883,mqtt.MQTTv311,"energy-ai-diag",False),
        ("MQTT 3.1 / 1883 / named client-id",1883,mqtt.MQTTv31,"energy-ai-diag",False),
        ("MQTT 3.1.1 / 8883 / TLS",8883,mqtt.MQTTv311,"energy-ai-diag",True),
    ]
    results=[]
    for name,port,proto,cid,use_tls in tests:
        row={"name":name,"port":port,"tcp":False,"mqtt":False,"data":False,"detail":""}
        try:
            with socket.create_connection((host,port),timeout=3): row["tcp"]=True
        except Exception as e:
            row["detail"]=f"TCP: {type(e).__name__}: {e}"; results.append(row); continue
        connected=threading.Event(); got_data=threading.Event(); outcome={"detail":"No CONNACK"}
        try:
            c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=cid,protocol=proto)
            if user:c.username_pw_set(user,password)
            if use_tls:
                c.tls_set(cert_reqs=ssl.CERT_NONE); c.tls_insecure_set(True)
            def oc(client,userdata,flags,reason_code,properties):
                outcome["detail"]=f"CONNACK {reason_code}"
                if int(reason_code)==0:
                    row["mqtt"]=True; client.subscribe("extapi/data/ehub")
                connected.set()
            def om(client,userdata,msg):
                row["data"]=True; outcome["detail"]+=f"; DATA {len(msg.payload)} bytes"; got_data.set()
            c.on_connect=oc;c.on_message=om
            c.connect_async(host,port,keepalive=15);c.loop_start()
            connected.wait(5)
            if row["mqtt"]:got_data.wait(3)
            c.disconnect();c.loop_stop()
            row["detail"]=outcome["detail"]
        except Exception as e:row["detail"]=f"MQTT: {type(e).__name__}: {e}"
        results.append(row)
    return {"host":host,"topic":"extapi/data/ehub","results":results}
