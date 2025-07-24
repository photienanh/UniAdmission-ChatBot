import os
import torch
from typing import Dict, Any, Optional, Union, List

from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from langchain_core.language_models import BaseLLM

import google.generativeai as genai
from langchain_openai import ChatOpenAI
from langchain_community.llms import HuggingFacePipeline
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from langchain_google_genai import ChatGoogleGenerativeAI

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


def create_gemini_llm(
    model_name: str = "gemini-1.5-pro-latest",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
) -> BaseLLM:
    try:
        # Load API key from environment
        load_dotenv()
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY in .env file")
            
        # Import here to avoid potential circular imports
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        # Ensure model_name has a default value if None
        if model_name is None:
            model_name = "gemini-1.5-pro-latest"  # Default model if none is provided
        
        llm_params = {
            "model": model_name,
            "temperature": temperature,
            "google_api_key": api_key,
            **kwargs
        }
        
        # Set max_tokens if provided
        if max_tokens is not None:
            llm_params["max_output_tokens"] = max_tokens
            
        # Use the LangChain wrapper for Google's Generative AI
        llm = ChatGoogleGenerativeAI(**llm_params)
        print(f"Google Gemini model initialized successfully with model: {model_name}")
        return llm
        
    except Exception as e:
        print(f"Error initializing Google Gemini model: {e}")
        return None

def create_openai_llm(
    model_name: str = "gpt-3.5-turbo",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
) -> BaseLLM:
    """
    Create an OpenAI LLM instance.
    Args:
        model_name: Name of the OpenAI model (default: "gpt-3.5-turbo")
        temperature: Temperature for text generation
        max_tokens: Maximum number of tokens to generate
        **kwargs: Additional parameters for the LLM
    Returns:
        An initialized OpenAI LLM instance
    """
    try:
        llm_params = {
            "model": model_name,
            "temperature": temperature,
            **kwargs
        }
        
        # Set max_tokens if provided
        if max_tokens is not None:
            llm_params["max_tokens"] = max_tokens
        
        llm = ChatOpenAI(**llm_params)
        print("OpenAI model initialized successfully!")
        return llm
        
    except Exception as e:
        print(f"Error initializing OpenAI model: {e}")
        return None
    
def create_rag_chain(
    llm,
    prompt_template: str = config.DEFAULT_RAG_PROMPT_TEMPLATE,
    input_variables: Optional[List[str]] = None,
    output_key: str = "result"
) -> LLMChain:
    if input_variables is None:
        input_variables = ["context", "question"]
        
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=input_variables
    )
    
    return LLMChain(
        llm=llm,
        prompt=prompt,
        output_key=output_key
    )