from ..engines import (
    SearchResult,
    HtmlResult,
    PreProcessedResult,
    ProcessedResult
)
from copy import deepcopy
import os
import json
import shutil

class Logger:
    def __init__(self, folder_path: str) -> None:
        self.enable = True
        self.folder_path = folder_path
        self._count = 0
        os.makedirs(self.folder_path, exist_ok=True)
    def start(self, query: str, k: int, engine_type: str):
        if self.enable:
            self._count = 0
            if os.path.exists(self.folder_path):
                shutil.rmtree(self.folder_path)
            os.makedirs(self.folder_path)
            try:
                with open(os.path.join(self.folder_path, "query.json"), 'w', encoding='utf-8') as file:
                    file.write(json.dumps({
                        "query": query,
                        "k": k,
                        "engine_type": engine_type
                    }))
            except Exception as e:
                print(f"Failed to log Query: {e}")
    def count(self):
        self._count += 1
    def search(self, data: SearchResult):
        if not self.enable: return
        try:
            folder_path = os.path.join(self.folder_path, f"{self._count}")
            os.makedirs(folder_path, exist_ok=True)
            with open(os.path.join(folder_path, f"search.json"), 'w', encoding='utf-8') as file:
                file.write(json.dumps(data))
        except Exception as e:
            print(f"Failed to log Search {self._count}: {e}")
    def html(self, data: HtmlResult):
        if not self.enable: return
        try:
            folder_path = os.path.join(self.folder_path, f"{self._count}")
            os.makedirs(folder_path, exist_ok=True)
            copied_data = deepcopy(data)
            copied_data.pop("html")
            with open(os.path.join(folder_path, f"html.json"), 'w', encoding='utf-8') as file:
                file.write(json.dumps(copied_data))
            with open(os.path.join(folder_path, f"html.html"), 'w', encoding='utf-8') as file:
                file.write(data['html'])
        except Exception as e:
            print(f"Failed to log Html {self._count}: {e}")
    def preprocessed(self, data: PreProcessedResult):
        if not self.enable: return
        try:
            folder_path = os.path.join(self.folder_path, f"{self._count}")
            os.makedirs(folder_path, exist_ok=True)
            copied_data = deepcopy(data)
            copied_data.pop("html")
            copied_data.pop("extracted_content")
            with open(os.path.join(folder_path, f"preprocess.json"), 'w', encoding='utf-8') as file:
                file.write(json.dumps(copied_data))
            with open(os.path.join(folder_path, f"preprocess.txt"), 'w', encoding='utf-8') as file:
                file.write(data["extracted_content"])
        except Exception as e:
            print(f"Failed to log Preprocessed {self._count}: {e}")
    def processed(self, data: ProcessedResult):
        if not self.enable: return
        try:
            folder_path = os.path.join(self.folder_path, f"{self._count}")
            os.makedirs(folder_path, exist_ok=True)
            copied_data = deepcopy(data)
            copied_data.pop("html")
            copied_data.pop("main_content")
            for image in copied_data["image_content"]:
                image.pop("text")
            for pdf in copied_data["pdf_content"]:
                pdf.pop("text")
            with open(os.path.join(folder_path, f"process.json"), 'w', encoding='utf-8') as file:
                file.write(json.dumps(copied_data))
            with open(os.path.join(folder_path, f"process.txt"), 'w', encoding='utf-8') as file:
                file.write(data["main_content"])
                
            image_path = os.path.join(folder_path, f"image")
            os.makedirs(image_path, exist_ok=True)
            for index, image_content in enumerate(data["image_content"]):
                with open(os.path.join(image_path, f"image_{index}.txt"), 'w', encoding='utf-8') as file:
                    file.write(image_content["text"])
                    
            pdf_path = os.path.join(folder_path, f"pdf")
            os.makedirs(pdf_path, exist_ok=True)
            for index, pdf_content in enumerate(data["pdf_content"]):
                with open(os.path.join(pdf_path, f"pdf_{index}.txt"), 'w', encoding='utf-8') as file:
                    file.write(pdf_content["text"])
            
        except Exception as e:
            print(f"Failed to log Processed {self._count}: {e}")