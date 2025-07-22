"""
Document processing module for the RAG system.
This module handles document loading, text splitting, and preprocessing.
"""

import os
from typing import List, Optional, Union, Dict, Any
import pandas as pd

from langchain.text_splitter import RecursiveCharacterTextSplitter, TextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader, CSVLoader
from langchain.docstore.document import Document

import config

class DocumentProcessor:
    """Class for processing documents for RAG."""
    
    def __init__(
        self,
        chunk_size: int = config.CHUNK_SIZE,
        chunk_overlap: int = config.CHUNK_OVERLAP,
        text_splitter: Optional[TextSplitter] = None,
    ):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            text_splitter: Custom text splitter instance
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if text_splitter is None:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
            )
        else:
            self.text_splitter = text_splitter
            
    def load_documents_from_directory(self, directory_path: str, file_extension: str = ".txt") -> List[Document]:
        """
        Load documents from a directory.
        
        Args:
            directory_path: Path to the directory
            file_extension: File extension to filter by
            
        Returns:
            List of loaded documents
        """
        documents = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith(file_extension):
                    file_path = os.path.join(root, file)
                    try:
                        if file_extension == ".txt":
                            loader = TextLoader(file_path, encoding='utf-8')
                        elif file_extension == ".pdf":
                            loader = PyPDFLoader(file_path)
                        elif file_extension == ".csv":
                            loader = CSVLoader(file_path)
                        else:
                            continue
                            
                        docs = loader.load()
                        documents.extend(docs)
                    except Exception as e:
                        print(f"Error loading {file_path}: {e}")
        
        return documents
    
    def load_documents_from_dataframe(self, df: pd.DataFrame, text_column: str, metadata_columns: Optional[List[str]] = None) -> List[Document]:
        """
        Load documents from a pandas DataFrame.
        
        Args:
            df: Pandas DataFrame
            text_column: Column containing the text
            metadata_columns: Columns to include as metadata
            
        Returns:
            List of documents
        """
        documents = []
        
        for i, row in df.iterrows():
            if pd.isna(row[text_column]):
                continue
                
            metadata = {"source": f"row_{i}"}
            
            if metadata_columns:
                for col in metadata_columns:
                    if col in df.columns and not pd.isna(row[col]):
                        metadata[col] = row[col]
            
            doc = Document(
                page_content=row[text_column],
                metadata=metadata
            )
            documents.append(doc)
            
        return documents
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks.
        
        Args:
            documents: List of documents to split
            
        Returns:
            List of split documents
        """
        return self.text_splitter.split_documents(documents)
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text before splitting.
        Override this method to implement custom preprocessing.
        
        Args:
            text: Text to preprocess
            
        Returns:
            Preprocessed text
        """
        # Implement custom preprocessing here
        return text