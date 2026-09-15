from contextlib import asynccontextmanager
from pathlib import Path
import sys, time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from .mqtt_client import start_mqtt, reconnect
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
    reconnect()
    return {"ok":True}

@app.get("/",response_class=HTMLResponse)
def dashboard():
    base=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parents[1]))
    return (base/"app"/"static"/"index.html").read_text(encoding="utf-8")
