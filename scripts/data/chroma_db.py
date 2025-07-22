import os 


from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from pathlib import Path

EMBEDDING_NAME = "intfloat/multilingual-e5-small"

def load_documents():
    all_docs = []
    for folder_name in os.listdir("data/parsed_x"):
        folder_path = os.path.join("data/parsed_x", folder_name)
        if os.path.isdir(folder_path):
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                loader = TextLoader(file_path, encoding='utf-8')
                docs = loader.load()
                all_docs.extend(docs)
    # for folder_name in os.listdir("data/raw_pdf"):
    #     folder_path = os.path.join("data/raw_pdf", folder_name)
    #     for file_name in os.listdir(folder_path):
    #         file_path = os.path.join(folder_path, file_name)
    #         loader = PyPDFLoader(file_path)
    #         try:
    #             docs = loader.load()
    #             all_docs.extend(docs)
    #         except Exception as e:
    #             print(f"Failed to load {file_path}")
    return all_docs

def split_documents(documents, chunk_size = 256, chunk_overlap = 64):
    splitter = CharacterTextSplitter(chunk_size = chunk_size, chunk_overlap = chunk_overlap)
    return splitter.split_documents(documents)

def store_in_vector_db(docs, persit_path: str):
    embedding = HuggingFaceEmbeddings(model_name=EMBEDDING_NAME)
    vectordb = Chroma.from_documents(docs, embedding, persist_directory=persit_path)
    vectordb.persist()
    print(f"Stored {len(docs)} chunks in Chrome at {persit_path}")
    
if __name__ == "__main__":
    raw_docs = load_documents()
    print(f"Loaded {len(raw_docs)} docs")
    chunks = split_documents(raw_docs)
    print(f"Split in {len(chunks)} chunks")
    store_in_vector_db(chunks, 'data/vector_db')