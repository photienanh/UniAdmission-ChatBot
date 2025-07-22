"""
Embeddings module for the RAG system.
This module handles different embedding models and their configuration.
"""

from typing import Optional, Dict, Any
import os

from langchain_huggingface import HuggingFaceEmbeddings
from langchain.embeddings.base import Embeddings
from langchain_openai import OpenAIEmbeddings

import config

class EmbeddingFactory:
    """Factory class for creating embedding models."""

    @staticmethod
    def create_embeddings(
        model_name: Optional[str] = None,
        provider: str = "huggingface",
        model_kwargs: Optional[Dict[str, Any]] = None,
        encode_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Embeddings:
        """
        Create an embedding model based on the provider.
        
        Args:
            model_name: Name of the embedding model
            provider: Provider of the embedding model (huggingface, openai)
            model_kwargs: Additional keyword arguments for the model
            encode_kwargs: Additional keyword arguments for encoding
            
        Returns:
            An initialized embedding model
        """
        if model_name is None:
            model_name = config.EMBEDDING_MODEL
            
        if model_kwargs is None:
            model_kwargs = {}
            
        if encode_kwargs is None:
            encode_kwargs = {}
        
        # Create cache directory if it doesn't exist
        os.makedirs(config.EMBEDDING_CACHE, exist_ok=True)
        
        if provider.lower() == "huggingface":
            return HuggingFaceEmbeddings(
                model_name=model_name,
                cache_folder=config.EMBEDDING_CACHE,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
        elif provider.lower() == "openai":
            return OpenAIEmbeddings(
                model=model_name,
                **model_kwargs
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")


def get_default_embeddings() -> Embeddings:
    """Get the default embedding model."""
    return EmbeddingFactory.create_embeddings()