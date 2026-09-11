"""Open the local interface after the server is ready."""
from pathlib import Path
import sys
import threading
import time
import urllib.request
import webbrowser
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def open_when_ready():
    for _ in range(60):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=1) as response:
                if response.status == 200:
                    webbrowser.open('http://127.0.0.1:8765')
                    return
        except OSError:
            time.sleep(.5)

if __name__ == '__main__':
    threading.Thread(target=open_when_ready, daemon=True).start()
    uvicorn.run('ivory.app:app', host='127.0.0.1', port=8765)
