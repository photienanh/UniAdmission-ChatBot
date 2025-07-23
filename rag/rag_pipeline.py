"""
Main RAG pipeline module.
This module connects all RAG components together and provides the main interface.
"""

import os
import json
from typing import List, Dict, Any, Optional, Union, Tuple

from langchain.schema import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.language_models import BaseLLM
from langchain.chains import RetrievalQA
from langchain.chains.base import Chain
from langchain.prompts import PromptTemplate

import config
from embeddings import get_default_embeddings
from document_processor import DocumentProcessor
from retriever import get_default_retriever, RetrieverFactory
from llm_interface import get_default_llm, LLMFactory


class RAGPipeline:
    """Main class for the RAG pipeline."""
    
    def __init__(
        self,
        retriever: Optional[BaseRetriever] = None,
        llm: Optional[BaseLLM] = None,
        prompt_template: str = config.DEFAULT_RAG_PROMPT_TEMPLATE,
        chain_type: str = "stuff",  # Options: stuff, map_reduce, refine, map_rerank
        return_source_documents: bool = True,
        verbose: bool = False
    ):
        """
        Initialize the RAG pipeline.
        
        Args:
            retriever: Document retriever
            llm: Language model
            prompt_template: Template for the prompt
            chain_type: Type of retrieval chain
            return_source_documents: Whether to return source documents
            verbose: Whether to print verbose output
        """
        self.retriever = retriever if retriever is not None else get_default_retriever()
        self.llm = llm if llm is not None else get_default_llm()
        self.prompt_template = prompt_template
        self.chain_type = chain_type
        self.return_source_documents = return_source_documents
        self.verbose = verbose
        
        # Create the prompt template
        self.prompt = PromptTemplate(
            template=self.prompt_template,
            input_variables=["context", "question"]
        )
        
        # Create the QA chain
        self.qa_chain = self._create_qa_chain()
        
    def _create_qa_chain(self) -> Chain:
        """
        Create the QA chain.
        
        Returns:
            QA chain instance
        """
        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type=self.chain_type,
            retriever=self.retriever,
            chain_type_kwargs={"prompt": self.prompt},
            return_source_documents=self.return_source_documents,
            verbose=self.verbose
        )
        
    def query(self, question: str) -> Dict[str, Any]:
        """
        Query the RAG pipeline.
        
        Args:
            question: Question to answer
            
        Returns:
            Response with answer and source documents
        """
        try:
            result = self.qa_chain({"query": question})
            return result
        except Exception as e:
            if self.verbose:
                print(f"Error during RAG query: {e}")
                
            # Fallback to retrieval only
            docs = self.retriever.get_relevant_documents(question)
            return {
                "query": question,
                "result": f"Error: {str(e)}",
                "source_documents": docs
            }
            
    def update_retriever(self, retriever: BaseRetriever) -> None:
        """
        Update the retriever and recreate the QA chain.
        
        Args:
            retriever: New retriever instance
        """
        self.retriever = retriever
        self.qa_chain = self._create_qa_chain()
        
    def update_llm(self, llm: BaseLLM) -> None:
        """
        Update the LLM and recreate the QA chain.
        
        Args:
            llm: New LLM instance
        """
        self.llm = llm
        self.qa_chain = self._create_qa_chain()
        
    def update_prompt(self, prompt_template: str) -> None:
        self.prompt_template = prompt_template
        self.prompt = PromptTemplate(
            template=self.prompt_template,
            input_variables=["context", "question"]
        )
        self.qa_chain = self._create_qa_chain()
        
    @classmethod
    def from_documents(
        cls,
        documents: List[Document],
        embedding_function=None,
        vector_store_type: str = "chroma",
        llm: Optional[BaseLLM] = None,
        persist_directory: Optional[str] = None,
        **kwargs
    ) -> "RAGPipeline":
        """
        Create a RAG pipeline from documents.
        
        Args:
            documents: List of documents
            embedding_function: Embedding function to use
            vector_store_type: Type of vector store
            llm: Language model
            persist_directory: Directory to persist the vector store
            **kwargs: Additional keyword arguments for the RAG pipeline
            
        Returns:
            RAG pipeline instance
        """
        # Create retriever
        retriever = get_default_retriever(
            documents=documents,
            embedding_function=embedding_function,
            vector_store_type=vector_store_type,
            persist_directory=persist_directory
        )
        
        # Create LLM if not provided
        if llm is None:
            llm = get_default_llm()
            
        return cls(
            retriever=retriever,
            llm=llm,
            **kwargs
        )
        
    @classmethod
    def load(
        cls,
        persist_directory: Optional[str] = None,
        vector_store_type: str = "chroma",
        llm_provider: str = "gemini",
        llm_model_name: Optional[str] = None,
        **kwargs
    ) -> "RAGPipeline":
        # Load retriever
        if persist_directory is None:
            persist_directory = config.VECTOR_DB_DIR
            
        retriever = get_default_retriever(
            vector_store_type=vector_store_type,
            persist_directory=persist_directory
        )
        
        # Create LLM with dynamic response length support
        llm = LLMFactory.create_llm(
            provider=llm_provider,
            model_name=llm_model_name,
            max_tokens=config.DEFAULT_MAX_TOKENS,
            dynamic_length=config.DYNAMIC_RESPONSE_LENGTH
        )
            
        return cls(
            retriever=retriever,
            llm=llm,
            **kwargs
        )


def create_pipeline(
    documents: Optional[List[Document]] = None,
    vector_store_type: str = "chroma",
    llm_provider: str = "gemini",
    llm_model_name: Optional[str] = None,
    persist_directory: Optional[str] = None,
    **kwargs
) -> RAGPipeline:
    if persist_directory is None:
        persist_directory = config.VECTOR_DB_DIR
        
    try:
        # Try to load existing pipeline
        return RAGPipeline.load(
            persist_directory=persist_directory,
            vector_store_type=vector_store_type,
            llm_provider=llm_provider,
            llm_model_name=llm_model_name,
            **kwargs
        )
    except Exception as e:
        # If loading fails, create a new pipeline from documents
        if documents is None:
            raise ValueError(f"Could not load existing pipeline ({str(e)}) and no documents provided to create a new one")
            
        return RAGPipeline.from_documents(
            documents=documents,
            vector_store_type=vector_store_type,
            persist_directory=persist_directory,
            llm=LLMFactory.create_llm(
                provider=llm_provider,
                model_name=llm_model_name,
                max_tokens=config.DEFAULT_MAX_TOKENS,
                dynamic_length=config.DYNAMIC_RESPONSE_LENGTH
            ),
            **kwargs
        )