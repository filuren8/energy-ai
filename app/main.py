from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from .mqtt_client import start_mqtt
from .state import snapshot

mqtt_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mqtt_client
    mqtt_client = start_mqtt()
    yield
    if mqtt_client:
        mqtt_client.loop_stop()

app = FastAPI(title="Energy AI", version="0.1.0", lifespan=lifespan)

@app.get("/api/state")
def api_state():
    return snapshot()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
