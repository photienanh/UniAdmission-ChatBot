from dotenv import load_dotenv
load_dotenv("app/server.env")
import os
import time

from pyngrok import ngrok
ngrok.set_auth_token(os.environ["NGROK_TOKEN"])
public_url = ngrok.connect(8000)
print("Public url:", public_url)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down")
    ngrok.kill()