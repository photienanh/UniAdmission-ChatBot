DOMAIN = "https://03a404f7578c.ngrok-free.app"
import requests
import io
import tarfile
def unpack(data: bytes, path: str):
    with io.BytesIO(data) as tar_buffer:
        with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
            tar.extractall(path=path)
unpack(requests.get(f"{DOMAIN}/script/kaggle_client").content, "kaggle_client")
unpack(requests.get(f"{DOMAIN}/script/search_engines").content, "search_engines")