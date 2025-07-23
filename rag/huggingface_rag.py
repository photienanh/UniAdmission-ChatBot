"""
Implementation of RAGtuyensinh notebook functionality as a Python module.
This module provides functions to directly use the RAG system from the notebook.
"""

import os
import torch
from typing import Dict, Any, Optional, List

from langchain.schema import Document
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_core.retrievers import BaseRetriever

# Import from our local modules
from llm_interface import setup_llm


def initialize_embeddings(model_name="intfloat/multilingual-e5-small"):
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"}
    )

def initialize_retriever(vector_db_path="vector_db_21_7", embedding_function=None, top_k=3):
    possible_paths = [
        vector_db_path,
        f"./{vector_db_path}",
        f"../{vector_db_path}",
        f"../../{vector_db_path}",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), f"../{vector_db_path}"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), f"../../{vector_db_path}"),
        "./vector_db_21_7"
    ]
    
    vector_db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            vector_db_path = path
            break
            
    if not vector_db_path:
        raise ValueError(f"Vector database path not found. Checked paths: {possible_paths}")
    
    print(f"Using vector database at: {vector_db_path}")
    
    if embedding_function is None:
        embedding_function = initialize_embeddings()
    
    try:
        vectordb = Chroma(
            persist_directory=vector_db_path,
            embedding_function=embedding_function
        )
        print(f"Successfully loaded vector database with {vectordb._collection.count()} documents")
        
        return vectordb.as_retriever(search_kwargs={"k": top_k})
    except Exception as e:
        raise ValueError(f"Error loading vector database: {e}")


def create_rag_chain(llm=None, retriever=None, template=None):
    """
    Create RAG chain with LLM and retriever.
    
    Args:
        llm: Language model
        retriever: Document retriever
        template: Prompt template string
        
    Returns:
        RetrievalQA chain
    """
    if llm is None:
        llm = setup_llm("meta-llama/Llama-3.2-1B")
        
    if retriever is None:
        retriever = initialize_retriever()
        
    if template is None:
        template = """Dưới đây là một câu hỏi và một số thông tin liên quan về tuyển sinh đại học ở Việt Nam. Hãy trả lời câu hỏi dựa trên thông tin được cung cấp.

Thông tin liên quan:
{context}

Câu hỏi: {question}

Trả lời một cách ngắn gọn, chính xác và dễ hiểu. Nếu không có thông tin đủ để trả lời, hãy nói "Tôi không có đủ thông tin để trả lời câu hỏi này."

Trả lời:"""
    
    prompt = PromptTemplate(
        template=template,
        input_variables=["context", "question"]
    )
    
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True
    )


def query_rag(question, qa_chain=None, retriever=None):
    if qa_chain is None:
        qa_chain = create_rag_chain(retriever=retriever)
        
    try:
        result = qa_chain({"query": question})
        return result
    except Exception as e:
        print(f"Error during RAG query: {e}")
        
        # Fallback to retrieval only
        if retriever is None and hasattr(qa_chain, "retriever"):
            retriever = qa_chain.retriever
        
        if retriever:
            docs = retriever.get_relevant_documents(question)
            return {
                "query": question,
                "result": f"Error: {str(e)}",
                "source_documents": docs
            }
        else:
            return {
                "query": question,
                "result": f"Error: {str(e)}",
                "source_documents": []
            }


def display_rag_results(result):
    print(f"\nQuestion: {result['query']}")
    print("\n" + "="*50)
    
    ans = result.get('result', 'No answer found.')
    if "Trả lời:" in ans:
        ans = ans.split("Trả lời:", 1)[1].strip()
    
    print(f"\nAnswer: {ans}")
    print("\n" + "="*50)
    
    print("\nSource Documents:")
    for i, doc in enumerate(result.get('source_documents', [])):
        print(f"\n[Document {i+1}]")
        print(f"Content: {doc.page_content[:150]}..." if len(doc.page_content) > 150 else f"Content: {doc.page_content}")
        print(f"Source: {doc.metadata.get('source', 'unknown')}")

class NotebookRAGPipeline:
    def __init__(
        self,
        vector_db_path="./vector_db_21_7",
        model_id="meta-llama/Llama-3.2-1B",
        top_k=3
    ):
        self.embeddings = initialize_embeddings()
        self.retriever = initialize_retriever(vector_db_path, self.embeddings, top_k)
        self.llm = setup_llm(model_id)
        self.qa_chain = create_rag_chain(self.llm, self.retriever)
        
    def query(self, question):
        return query_rag(question, self.qa_chain, self.retriever)
        
    def display_results(self, result):
        display_rag_results(result)


# Create a pipeline instance
def create_notebook_pipeline(vector_db_path="./vector_db_21_7", model_id="meta-llama/Llama-3.2-1B", top_k=3):
    return NotebookRAGPipeline(vector_db_path, model_id, top_k)


# Function to handle simple queries (for API integration)
def notebook_ask(question, vector_db_path="./vector_db_21_7", model_id=None):
    retriever = initialize_retriever(vector_db_path)
    
    if model_id:
        llm = setup_llm(model_id)
        qa_chain = create_rag_chain(llm, retriever)
        result = query_rag(question, qa_chain)
    else:
        docs = retriever.get_relevant_documents(question)
        result = {
            "query": question,
            "result": "Model not specified, showing retrieved documents only.",
            "source_documents": docs
        }
    
    ans = result.get('result', 'No answer found.')
    if "Trả lời:" in ans:
        ans = ans.split("Trả lời:", 1)[1].strip()
        
    return {
        "question": question,
        "answer": ans,
        "source_documents": [
            {
                "content": doc.page_content,
                "source": doc.metadata.get('source', 'unknown')
            }
            for doc in result.get('source_documents', [])
        ]
    }