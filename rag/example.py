"""
Example usage of the RAG pipeline.
"""

import os
import pandas as pd
from typing import Dict, Any

from document_processor import DocumentProcessor
from embeddings import get_default_embeddings
from rag_pipeline import create_pipeline, RAGPipeline


def load_sample_data(csv_path: str = "../data/info/info.csv") -> pd.DataFrame:
    """
    Load sample data from a CSV file.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        Pandas DataFrame with the sample data
    """
    try:
        return pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        # Create a small sample dataframe if file doesn't exist
        return pd.DataFrame({
            "Tên trường": ["Đại học Quốc gia Hà Nội", "Đại học Bách Khoa Hà Nội"],
            "Website": ["https://vnu.edu.vn", "https://hust.edu.vn"],
            "Loại hình cơ sở đào tạo": ["Đại học", "Đại học"],
            "Tỉnh, thành phố": ["Hà Nội", "Hà Nội"]
        })

def process_data_and_create_pipeline() -> RAGPipeline:
    """
    Process sample data and create a RAG pipeline.
    
    Returns:
        RAG pipeline instance
    """
    # Load sample data
    df = load_sample_data()
    print(f"Loaded data with {len(df)} rows")
    
    # Create document processor
    processor = DocumentProcessor()
    
    # Process documents
    documents = processor.load_documents_from_dataframe(
        df=df,
        text_column="Tên trường",  # Main text column
        metadata_columns=["Website", "Loại hình cơ sở đào tạo", "Tỉnh, thành phố"]  # Additional metadata
    )
    print(f"Created {len(documents)} documents")
    
    # Split documents if needed
    # chunks = processor.split_documents(documents)
    # print(f"Split into {len(chunks)} chunks")
    
    # Create embeddings
    embedding_function = get_default_embeddings()
    
    # Create RAG pipeline
    pipeline = create_pipeline(
        documents=documents,
        vector_store_type="faiss",  # Use FAISS for in-memory vector store
        llm_provider="gemini",
        verbose=True
    )
    
    return pipeline


def run_query(pipeline: RAGPipeline, question: str) -> Dict[str, Any]:
    """
    Run a query through the RAG pipeline.
    
    Args:
        pipeline: RAG pipeline instance
        question: Question to answer
        
    Returns:
        Response with answer and source documents
    """
    print(f"\nQuery: {question}")
    result = pipeline.query(question)
    
    # Display the answer
    print("\nAnswer:")
    print(result.get("result", "No answer found"))
    
    # Display source documents
    if "source_documents" in result:
        print("\nSource documents:")
        for i, doc in enumerate(result["source_documents"]):
            print(f"\nDocument {i+1}:")
            print(f"Content: {doc.page_content}")
            print(f"Metadata: {doc.metadata}")
    
    return result


if __name__ == "__main__":
    # Process data and create pipeline
    pipeline = process_data_and_create_pipeline()
    
    # Run sample queries
    queries = [
        "Có trường đại học nào ở Hà Nội không?",
        "Cho tôi thông tin về website của Đại học Bách Khoa Hà Nội"
    ]
    
    for query in queries:
        run_query(pipeline, query)