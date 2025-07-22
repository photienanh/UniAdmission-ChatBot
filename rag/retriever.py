"""
Retriever module for the RAG system.
This module handles retrieval of relevant documents from vector stores.
"""

import os
from typing import List, Dict, Any, Optional, Union, Tuple

from langchain_core.vectorstores import VectorStore
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_transformers import EmbeddingsRedundantFilter
from langchain.retrievers.document_compressors import DocumentCompressorPipeline
from langchain.schema import Document

import config
from embeddings import get_default_embeddings

class RetrieverFactory:
    """Factory for creating retrievers."""
    
    @staticmethod
    def create_vector_store(
        vector_store_type: str = "chroma",
        documents: Optional[List[Document]] = None,
        embedding_function = None,
        persist_directory: Optional[str] = None,
        **kwargs
    ) -> VectorStore:
        """
        Create a vector store.
        
        Args:
            vector_store_type: Type of vector store (chroma, faiss, etc.)
            documents: List of documents to add to the vector store
            embedding_function: Embedding function to use
            persist_directory: Directory to persist the vector store
            **kwargs: Additional keyword arguments for the vector store
            
        Returns:
            Initialized vector store
        """
        if embedding_function is None:
            embedding_function = get_default_embeddings()
            
        if persist_directory is None:
            persist_directory = config.VECTOR_DB_DIR
            
        if vector_store_type.lower() == "chroma":
            from langchain_chroma import Chroma
            
            if documents is not None:
                vector_store = Chroma.from_documents(
                    documents=documents,
                    embedding=embedding_function,
                    persist_directory=persist_directory,
                    **kwargs
                )
                vector_store.persist()
            else:
                # Load existing vector store
                vector_store = Chroma(
                    persist_directory=persist_directory,
                    embedding_function=embedding_function,
                    **kwargs
                )
                
            return vector_store
            
        elif vector_store_type.lower() == "faiss":
            from langchain_community.vectorstores import FAISS
            
            if documents is not None:
                vector_store = FAISS.from_documents(
                    documents=documents,
                    embedding=embedding_function,
                    **kwargs
                )
                
                # Save FAISS index if persist_directory is provided
                if persist_directory:
                    os.makedirs(persist_directory, exist_ok=True)
                    vector_store.save_local(persist_directory)
            else:
                # Load existing vector store
                vector_store = FAISS.load_local(
                    persist_directory,
                    embedding_function,
                    **kwargs
                )
                
            return vector_store
            
        else:
            raise ValueError(f"Unsupported vector store type: {vector_store_type}")
    
    @staticmethod
    def create_retriever(
        vector_store: VectorStore,
        search_type: str = "similarity",
        search_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> BaseRetriever:
        """
        Create a retriever from a vector store.
        
        Args:
            vector_store: Vector store to create a retriever from
            search_type: Type of search to perform
            search_kwargs: Keyword arguments for the search
            **kwargs: Additional keyword arguments for the retriever
            
        Returns:
            Initialized retriever
        """
        if search_kwargs is None:
            search_kwargs = {"k": config.DEFAULT_TOP_K}
            
        if hasattr(vector_store, "as_retriever"):
            retriever = vector_store.as_retriever(
                search_type=search_type,
                search_kwargs=search_kwargs,
                **kwargs
            )
            return retriever
        else:
            raise ValueError(f"Vector store does not support retrieval")
    
    @staticmethod
    def create_enhanced_retriever(
        base_retriever: BaseRetriever,
        use_reranking: bool = False,
        use_query_expansion: bool = False,
        **kwargs
    ) -> BaseRetriever:
        """
        Create an enhanced retriever with reranking and/or query expansion capabilities.
        
        Args:
            base_retriever: Base retriever to enhance
            use_reranking: Whether to use reranking
            use_query_expansion: Whether to use query expansion
            **kwargs: Additional keyword arguments for the retriever components
            
        Returns:
            Enhanced retriever
        """
        if not (use_reranking or use_query_expansion):
            # No enhancements requested, return base retriever
            return base_retriever
            
        enhanced_retriever = base_retriever
        
        if use_reranking:
            # Create a reranking pipeline - example with redundant filter
            embeddings = kwargs.get("embeddings", get_default_embeddings())
            redundant_filter = EmbeddingsRedundantFilter(embeddings=embeddings)
            
            # You can add more compressors to the pipeline as needed
            compressor_pipeline = DocumentCompressorPipeline(transformers=[redundant_filter])
            
            enhanced_retriever = ContextualCompressionRetriever(
                base_compressor=compressor_pipeline,
                base_retriever=enhanced_retriever
            )
            
        if use_query_expansion:
            # Placeholder for query expansion implementation
            # This will be implemented in the future
            pass
            
        return enhanced_retriever


def get_default_retriever(
    documents: Optional[List[Document]] = None,
    embedding_function = None,
    vector_store_type: str = "chroma",
    persist_directory: Optional[str] = None,
    use_reranking: bool = False,
    use_query_expansion: bool = False,
    **kwargs
) -> BaseRetriever:
    """
    Get the default retriever.
    
    Args:
        documents: List of documents to add to the vector store
        embedding_function: Embedding function to use
        vector_store_type: Type of vector store
        persist_directory: Directory to persist the vector store
        use_reranking: Whether to use reranking
        use_query_expansion: Whether to use query expansion
        **kwargs: Additional keyword arguments for the retriever
        
    Returns:
        Default retriever
    """
    vector_store = RetrieverFactory.create_vector_store(
        vector_store_type=vector_store_type,
        documents=documents,
        embedding_function=embedding_function,
        persist_directory=persist_directory
    )
    
    base_retriever = RetrieverFactory.create_retriever(
        vector_store=vector_store,
        search_kwargs={"k": config.DEFAULT_TOP_K, "score_threshold": config.SIMILARITY_THRESHOLD}
    )
    
    if use_reranking or use_query_expansion:
        return RetrieverFactory.create_enhanced_retriever(
            base_retriever=base_retriever,
            use_reranking=use_reranking,
            use_query_expansion=use_query_expansion,
            embeddings=embedding_function,
            **kwargs
        )
    
    return base_retriever