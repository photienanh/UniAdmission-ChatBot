"""
Retriever module for the RAG system.
This module handles vector database and retrieval functionality.
"""

import os
from typing import List, Dict, Any, Optional, Union, Callable

from langchain.schema import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma
from langchain_community.vectorstores import FAISS

import config
from embeddings import get_default_embeddings


class RetrieverFactory:
    """Factory class for retrievers."""
    
    @staticmethod
    def create_retriever(
        vector_store_type: str = "chroma",
        documents: Optional[List[Document]] = None,
        embedding_function: Optional[Embeddings] = None,
        persist_directory: Optional[str] = None,
        collection_name: str = "university_admission",
        search_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> BaseRetriever:
        """
        Create a retriever.
        
        Args:
            vector_store_type: Type of vector store (chroma, faiss, etc.)
            documents: List of documents
            embedding_function: Embedding function to use
            persist_directory: Directory to persist the vector store
            collection_name: Name of the collection
            search_kwargs: Search parameters
            **kwargs: Additional keyword arguments for the vector store
            
        Returns:
            Retriever instance
        """
        if embedding_function is None:
            embedding_function = get_default_embeddings()
            
        if search_kwargs is None:
            search_kwargs = {"k": config.DEFAULT_TOP_K}
        
        # Allow using specific vector_db_21_7 path from notebook
        if persist_directory == "vector_db_21_7" or persist_directory == "./vector_db_21_7":
            # Check both relative and absolute paths
            possible_paths = [
                "./vector_db_21_7",
                "../vector_db_21_7",
                "../../vector_db_21_7",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "../vector_db_21_7"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../vector_db_21_7"),
                "d:/ASUS/Courses/Intern/LLMforUni/vector_db_21_7"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    persist_directory = path
                    break
                    
            print(f"Using vector database at: {persist_directory}")
            
        if vector_store_type == "chroma":
            # Load existing vector store if persist_directory is provided
            if persist_directory and os.path.exists(persist_directory):
                vector_store = Chroma(
                    persist_directory=persist_directory,
                    embedding_function=embedding_function,
                    collection_name=collection_name,
                    **kwargs
                )
            # Create new vector store if documents are provided
            elif documents:
                vector_store = Chroma.from_documents(
                    documents=documents,
                    embedding=embedding_function,
                    collection_name=collection_name,
                    persist_directory=persist_directory,
                    **kwargs
                )
            else:
                raise ValueError("Either documents or a valid persist_directory must be provided")
                
        elif vector_store_type == "faiss":
            # Load existing vector store if persist_directory is provided
            if persist_directory and os.path.exists(persist_directory):
                vector_store = FAISS.load_local(
                    folder_path=persist_directory,
                    embeddings=embedding_function,
                    **kwargs
                )
            # Create new vector store if documents are provided
            elif documents:
                vector_store = FAISS.from_documents(
                    documents=documents,
                    embedding=embedding_function,
                    **kwargs
                )
                
                # Save the vector store if persist_directory is provided
                if persist_directory:
                    vector_store.save_local(persist_directory)
            else:
                raise ValueError("Either documents or a valid persist_directory must be provided")
        else:
            raise ValueError(f"Unsupported vector store type: {vector_store_type}")
            
        # Create and return the retriever
        return vector_store.as_retriever(
            search_kwargs=search_kwargs
        )


def get_default_retriever(
    documents: Optional[List[Document]] = None,
    embedding_function: Optional[Embeddings] = None,
    vector_store_type: str = "chroma",
    persist_directory: Optional[str] = None,
    collection_name: str = "university_admission",
    **kwargs
) -> BaseRetriever:
    """
    Get the default retriever.
    
    Args:
        documents: List of documents
        embedding_function: Embedding function to use
        vector_store_type: Type of vector store
        persist_directory: Directory to persist the vector store
        collection_name: Name of the collection
        **kwargs: Additional keyword arguments for the retriever
        
    Returns:
        Default retriever instance
    """
    if persist_directory is None:
        persist_directory = config.VECTOR_DB_DIR
        
    return RetrieverFactory.create_retriever(
        vector_store_type=vector_store_type,
        documents=documents,
        embedding_function=embedding_function,
        persist_directory=persist_directory,
        collection_name=collection_name,
        **kwargs
    )