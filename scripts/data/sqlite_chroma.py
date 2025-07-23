import os 
import sqlite3

from langchain_core.documents import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from pathlib import Path
from typing import cast, Generator

db_path = "data/sqlite/sqlite.db"
persit_path = "data/vector_db"

EMBEDDING_NAME = "intfloat/multilingual-e5-small"
def retrieve_all_doc_ids(file_path: str):
    conn = sqlite3.connect(file_path)
    conn.execute("PRAGMA journal_model=WAL")
    with conn:
        query = 'SELECT id FROM document WHERE text != ""'
        res = conn.execute(query)
        ids = [row[0] for row in res.fetchall()]
        return ids
def db_iterator(file_path: str) -> Generator[tuple[int, str, str], None, None]:
    conn = sqlite3.connect(file_path)
    conn.execute("PRAGMA journal_model=WAL")
    ids = retrieve_all_doc_ids(file_path)
    for id in ids:
        query = "SELECT school_id, url, text FROM document WHERE id = ?"
        with conn:
            res = conn.execute(
                query,
                (id, )
            )
            row = res.fetchone()
        yield row
def process_and_store_batch(batch, vector_db: Chroma, splitter: CharacterTextSplitter):
    documents = [
        Document(
            page_content=row[2],
            metadata={
                "school": row[0],
                "url": row[1]
            }
        )
        for row in batch
    ]
    chunks = splitter.split_documents(documents)
    vector_db.add_documents(chunks)
    print(f"Processed and stored {len(chunks)} chunks")
def load_all():
    batch_size = 100
    embedding = HuggingFaceEmbeddings(model_name=EMBEDDING_NAME)
    vectordb = Chroma(embedding_function=embedding, persist_directory=persit_path)
    splitter = CharacterTextSplitter(chunk_size = 256, chunk_overlap = 64)
    doc_generator = db_iterator(db_path)
    batch = []
    print("Start")
    for doc in doc_generator:
        batch.append(doc)
        if len(batch) >= batch_size:
            process_and_store_batch(batch, vectordb, splitter)
            batch.clear()
    if len(batch) > 0:
        process_and_store_batch(batch, vectordb, splitter)
    print("Completed")
if __name__ == "__main__":
    load_all()