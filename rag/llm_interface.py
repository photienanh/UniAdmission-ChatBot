import os
import torch
from typing import Dict, Any, Optional, Union, List

from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from langchain_core.language_models import BaseLLM

import google.generativeai as genai
from langchain_community.llms import HuggingFacePipeline
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM

from dotenv import load_dotenv
from . import config

def create_huggingface_llm(
    model_name: str = "meta-llama/Llama-3.2-1B",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
) -> BaseLLM:
    try:
        print(f"Loading HuggingFace model: {model_name}")
        # Initialize tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        
        # Add pad token if it doesn't exist
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # For Llama and Qwen models, load the model directly
        if "llama" in model_name.lower() or "qwen" in model_name.lower():
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                device_map="auto",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            
            pipe_params = {
                "model": model,
                "tokenizer": tokenizer,
                "do_sample": True,
                "temperature": temperature,
                "top_p": 0.95,
                "repetition_penalty": 1.15,
                **kwargs
            }
        else:
            pipe_params = {
                "tokenizer": tokenizer,
                "model": model_name,
                "device": kwargs.get("device", 0 if torch.cuda.is_available() else -1),
                "do_sample": True,
                "temperature": temperature,
                "pad_token_id": tokenizer.eos_token_id,
                **kwargs
            }
        
        # Set max_length if provided
        if max_tokens is not None:
            pipe_params["max_length"] = max_tokens
        
        # Create HuggingFace pipeline
        pipe = pipeline(
            "text-generation",
            **pipe_params
        )
        
        # Create LangChain LLM
        llm = HuggingFacePipeline(pipeline=pipe)
        print("HuggingFace model initialized successfully!")
        return llm
        
    except Exception as e:
        print(f"Error initializing HuggingFace model: {e}")
        return None


def initialize_gemini(
    model_name: str = "gemini-2.0-flash-lite-preview-02-05",
    temperature: float = 0.7,
    api_key: str = None,
    system_instruction: str = "Bạn là một AI tư vấn tuyển sinh đại học chuyên nghiệp. Hãy trả lời các câu hỏi một cách chính xác, hữu ích và thân thiện."
):
    """
    Initialize the Google Gemini model directly (not using LangChain wrapper).
    
    Args:
        model_name: Name of the Gemini model
        temperature: Temperature for text generation
        api_key: Gemini API key (will be loaded from env if not provided)
        system_instruction: System instruction for the model
    
    Returns:
        An initialized Gemini GenerativeModel
    """
    try:
        # Use provided API key or load from environment
        if not api_key:
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                api_key = os.getenv("GOOGLE_API_KEY")
                
        if not api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY in .env file")
        
        # Configure the genai client
        genai.configure(api_key=api_key)
        
        # Create the generative model with system instruction
        model = genai.GenerativeModel(
            model_name,
            system_instruction=system_instruction,
            generation_config={"temperature": temperature}
        )
        
        print(f"Google Gemini model initialized successfully with model: {model_name}")
        return model
        
    except Exception as e:
        print(f"Error initializing Google Gemini model: {e}")
        return None

# Chat sessions dictionary to store conversation history
gemini_chat_sessions = {}

def get_or_create_gemini_chat(model, session_id=None):
    """Get or create a Gemini chat session for the given session ID"""
    if session_id is None:
        # If no session ID is provided, create a new chat without storing it
        return model.start_chat()
        
    if session_id not in gemini_chat_sessions:
        gemini_chat_sessions[session_id] = model.start_chat()
    
    return gemini_chat_sessions[session_id]
