import os
import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings

from . import config

def get_default_embeddings() -> Embeddings:
    os.makedirs(config.EMBEDDING_CACHE, exist_ok=True)
    
    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        cache_folder=config.EMBEDDING_CACHE,
        model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"}
    )