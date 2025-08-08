from huggingface_hub import HfApi
import shutil
import os
import time
from typing import TypedDict

class CacheUnit(TypedDict):
    size: float
    last_used: float
    path: str
class CacheControl:
    """
    Custom class for managing HuggingFace hard disk cache
    """
    SIZE_MAP = {
        "BF16": 2,
        "FP16": 2,
        "FP32": 4,
        "FP64": 8
    }
    def __init__(self, folder: str, limit_gb: float = 15):
        self.folder = folder
        if os.path.exists(self.folder):
            shutil.rmtree(self.folder)
        os.makedirs(self.folder, exist_ok=True)
        self.limit = limit_gb
        self.__cache: dict[str, CacheUnit] = {}
    def _get_model_tensor_size_gb(self, model_id: str) -> float:
        model_info = HfApi().model_info(model_id)
        safetensors = model_info.safetensors
        total = 0
        for key, size in safetensors.parameters.items():
            total += CacheControl.SIZE_MAP[key] * size / 1024**3
        return total
    def _remove_last(self) -> float:
        last = time.time()
        last_path = None
        last_size = 0
        last_key = None
        for key, item in self.__cache.items():
            if item["last_used"] < last:
                last = item["last_used"]
                last_path = item["path"]
                last_size = item["size"]
                last_key = key
        if last_key:
            print(f"[Cache] Free {last_size:.2f} GB: {last_path}")
            shutil.rmtree(last_path)
            self.__cache.pop(last_key)
            return last_size
    def _reserve(self, size: float, top: bool = True):
        if size > self.limit:
            raise Exception(f"[Cache] Model size too big to cache: {size}")
        current = sum(s["size"] for s in self.__cache.values())
        if current + size > self.limit:
            self._reserve(current-self._remove_last(), False)
        if top:
            current = sum(s["size"] for s in self.__cache.values())
            print(f"[Cache] Reserved {size:.2f} GB | Left: {self.limit-current-size:.2f} GB | Limit: {self.limit:.2f} GB")
    def _get_last_folder(self):
        entries = [os.path.join(self.folder, d) for d in os.listdir(self.folder)]
        folders = [d for d in entries if os.path.isdir(d)]
        return max(folders, key=os.path.getctime)
    def cache_prepare(self, model_id: str) -> float:
        if model_id not in self.__cache:
            new_model_size = self._get_model_tensor_size_gb(model_id)
            self._reserve(new_model_size)
    def cache_add(self, model_id: str) -> float:
        if model_id not in self.__cache:
            size = self._get_model_tensor_size_gb(model_id)
            self.__cache[model_id] = {
                "size": size,
                "last_used": time.time(),
                "path": self._get_last_folder()
            }
            current = sum(s["size"] for s in self.__cache.values())
            print(f"[Cache] Cached {size:.2f} GB | Left: {self.limit-current:.2f} GB | Limit: {self.limit:.2f} GB")

    def cache_update(self, model_id: str):
        self.__cache[model_id]["last_used"] = time.time()