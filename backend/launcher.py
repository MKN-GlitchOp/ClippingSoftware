"""Single local server with a browser opened only once the service is ready."""
import threading
import time
import webbrowser
from urllib.request import urlopen
import uvicorn


def open_when_ready():
    for _ in range(30):
        try:
            with urlopen('http://127.0.0.1:8000/api/health',timeout=1) as response:
                if response.status==200:
                    webbrowser.open('http://127.0.0.1:8000')
                    return
        except OSError:
            time.sleep(1)


if __name__=='__main__':
    threading.Thread(target=open_when_ready,daemon=True).start()
    uvicorn.run('backend.main:app',host='127.0.0.1',port=8000)
