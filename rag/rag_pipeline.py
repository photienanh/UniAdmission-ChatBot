"""
RAG pipeline module for the UniAdmission-ChatBot system.
This module provides a simple interface for RAG (Retrieval-Augmented Generation).
"""

import os
from typing import Dict, Any, List, Optional, Tuple, Union
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.language_models import BaseLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain.retrievers import ContextualCompressionRetriever
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

from . import config
from .llm_interface import create_huggingface_llm, create_gemini_llm, create_openai_llm


class SimplifiedRAG:
    def __init__(
        self, 
        vector_db_path: str = config.VECTOR_DB_DIR,
        embedding_model: str = config.EMBEDDING_MODEL,
        llm_type: str = "gemini",
        llm_model_name: str = None,
        temperature: float = config.DEFAULT_TEMPERATURE,
        top_k: int = config.DEFAULT_TOP_K
    ):
        if vector_db_path is None:
            vector_db_path = config.VECTOR_DB_DIR
        
        if not os.path.exists(vector_db_path):
            raise ValueError(f"Vector database not found at {vector_db_path}")
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            cache_folder="./cache/embedding_cache"
        )
        
        self.vectorstore = Chroma(
            persist_directory=vector_db_path,
            embedding_function=self.embeddings
        )
        
        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": top_k}
        )
        
        if llm_model_name is None:
            if llm_type.lower() == "huggingface":
                llm_model_name = config.HUGGINGFACE_LLM_MODEL
            elif llm_type.lower() == "gemini":
                llm_model_name = config.GOOGLE_GEMINI_MODEL
            else:  # openai
                llm_model_name = config.OPENAI_MODEL
                
        # Initialize LLM
        self.llm_type = llm_type.lower()
        if self.llm_type == "huggingface":
            self.llm = create_huggingface_llm(
                model_name=llm_model_name,
                temperature=temperature
            )
        elif self.llm_type == "gemini":
            self.llm = create_gemini_llm(
                model_name=llm_model_name,
                temperature=temperature
            )
        elif self.llm_type == "openai":
            self.llm = create_openai_llm(
                model_name=llm_model_name,
                temperature=temperature
            )
        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}. Use 'huggingface', 'gemini' or 'openai'")
        
        self.temperature = temperature
        self.top_k = top_k
            
        # Create RAG chain
        prompt_template = PromptTemplate(
            template=config.DEFAULT_RAG_PROMPT_TEMPLATE,
            input_variables=["context", "question"]
        )

        self.qa_chain_huggingface = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            chain_type_kwargs={"prompt": prompt_template},
            return_source_documents=True
        )
        
    def get_llm(self) -> BaseLLM:
        return self.llm
    
    def get_vectorstore(self) -> Chroma:
        return self.vectorstore
    
    def get_retriever(self) -> BaseRetriever:
        return self.retriever
        
    def change_llm(self, llm_type: str, llm_model_name: str = None, temperature: float = None):
        """
        Change the LLM being used in the RAG pipeline.
        
        Args:
            llm_type: Type of LLM to use ('huggingface', 'gemini', or 'openai')
            llm_model_name: Optional model name to use
            temperature: Optional temperature value
        
        Returns:
            The initialized LLM
        """
        if temperature is None:
            temperature = config.DEFAULT_TEMPERATURE
            
        self.llm_type = llm_type.lower()
        
        if llm_model_name is None:
            if self.llm_type == "huggingface":
                llm_model_name = config.HUGGINGFACE_LLM_MODEL
            elif self.llm_type == "gemini":
                llm_model_name = config.GOOGLE_GEMINI_MODEL
            else:  # openai
                llm_model_name = config.OPENAI_MODEL
        
        if self.llm_type == "huggingface":
            self.llm = create_huggingface_llm(
                model_name=llm_model_name,
                temperature=temperature
            )
        elif self.llm_type == "gemini":
            self.llm = create_gemini_llm(
                model_name=llm_model_name,
                temperature=temperature
            )
        elif self.llm_type == "openai":
            self.llm = create_openai_llm(
                model_name=llm_model_name,
                temperature=temperature
            )
        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}. Use 'huggingface', 'gemini' or 'openai'")
        
        # Recreate the QA chain with the new LLM
        prompt_template = PromptTemplate(
            template=config.DEFAULT_RAG_PROMPT_TEMPLATE,
            input_variables=["context", "question"]
        )
        
        self.qa_chain_huggingface = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            chain_type_kwargs={"prompt": prompt_template},
            return_source_documents=True
        )
        
        return self.llm
        
    def ask(self, question: str) -> Dict[str, Any]:
        try:
            result = self.qa_chain_huggingface({"query": question})
            return {
                "question": question,
                "answer": result["result"],
                "source_documents": result["source_documents"]
            }
        except Exception as e:
            print(f"Error in RAG pipeline: {e}")
            # Try to retrieve documents even if LLM fails
            try:
                docs = self.retriever.get_relevant_documents(question)
                return {
                    "question": question,
                    "answer": f"Error generating response: {str(e)}",
                    "source_documents": docs
                }
            except Exception as retrieval_error:
                return {
                    "question": question,
                    "answer": f"Error in RAG pipeline: {str(e)}, Retrieval error: {str(retrieval_error)}",
                    "source_documents": []
                }
    
    def retrieve_documents(self, question: str, k: int = config.DEFAULT_TOP_K) -> List[Document]:
        search_kwargs = {"k": k} if k is not None else None
        return self.retriever.get_relevant_documents(question, search_kwargs=search_kwargs)
    
    def add_documents(self, documents: List[Document]) -> None:
        """
        Add new documents to the vector store.
        
        Args:
            documents: List of Document objects to add
        """
        if not documents:
            raise ValueError("No documents provided to add to the vector store.")
        self.vectorstore.add_documents(documents)
        self.vectorstore.persist()
    
    def change_retriever(self,
        search_kwargs: Optional[Dict[str, Any]] = {"k": config.DEFAULT_TOP_K},
        search_type: Optional[str] = "similarity"
    ) -> BaseRetriever:
        
        if search_kwargs is None:
            search_kwargs = {"k": config.DEFAULT_TOP_K}
        
        self.retriever = self.vectorstore.as_retriever(
            search_kwargs=search_kwargs,
            search_type=search_type
        )
        
        return self.retriever
    
    def rerank_documents(self,
        question: str,
        reranker_model: str = config.RERANKER_MODEL,
        top_k: int = config.DEFAULT_TOP_K
    ) -> List[Document]:
        """
        Rerank the retrieved documents using a cross-encoder reranker.
        
        Args:
            question: The query for which documents are being reranked
            documents: List of Document objects to rerank
            reranker_model: Model name for the reranker
            top_k: Number of top documents to return after reranking
        
        Returns:
            List of reranked Document objects
        """
        reranker = CrossEncoderReranker(model_name=reranker_model)
        compressed_retriever = ContextualCompressionRetriever(
            base_retriever=self.retriever,
            reranker=reranker,
            top_k=top_k
        )
        
        return compressed_retriever.get_relevant_documents(question, search_kwargs={"k": top_k})