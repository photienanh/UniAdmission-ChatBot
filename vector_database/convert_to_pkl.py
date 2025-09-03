import asyncio
import time
from typing import Optional
from pathlib import Path
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from huggingface_hub import login

hf_token = os.getenv("HUGGING_FACE_TOKEN")
login(hf_token)

def load_model_embedding():
    """Load HuggingFace embedding model"""
    return HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small")

def load_database(index_path, embedding_model):
    """Load FAISS vector database"""
    vectorstore = FAISS.load_local(index_path, embedding_model, allow_dangerous_deserialization=True)
    all_docs = list(vectorstore.docstore._dict.values())
    return all_docs

import pickle

model = load_model_embedding()

all_docs = load_database("vector_database/vectordb", model)

with open("static.pkl", 'wb') as file:
    pickle.dump(all_docs, file)