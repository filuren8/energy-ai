import threading, time, webbrowser, traceback
from pathlib import Path
import uvicorn

LOG=Path.home()/"EnergyAI-startup.log"

def log(msg):
    try:
        with LOG.open("a",encoding="utf-8") as f:f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except Exception:pass

def open_browser():
    # Wait until server has had time to bind.
    time.sleep(3)
    webbrowser.open("http://127.0.0.1:8000")

if __name__=="__main__":
    try:
        log("EnergyAI V0.7 starting")
        from app.main import app
        threading.Thread(target=open_browser,daemon=True).start()
        uvicorn.run(app,host="127.0.0.1",port=8000,log_level="info")
    except Exception:
        err=traceback.format_exc()
        log(err)
        print(err)
        print("\nStartup log:",LOG)
        input("\nTryck Enter för att stänga...")
