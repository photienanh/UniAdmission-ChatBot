"""
LLM interface module for the RAG system.
This module handles different LLM providers and configurations.
"""

import os
import torch
from typing import Dict, Any, Optional, Union, List

from langchain.chains.base import Chain
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_core.language_models import BaseLLM

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_community.llms import HuggingFacePipeline
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM

from dotenv import load_dotenv
import config

class LLMFactory:
    
    @staticmethod
    def create_llm(
        provider: str = "gemini",
        model_name: Optional[str] = None,
        temperature: float = config.DEFAULT_TEMPERATURE,
        max_tokens: Optional[int] = config.DEFAULT_MAX_TOKENS,
        dynamic_length: bool = config.DYNAMIC_RESPONSE_LENGTH,
        **kwargs
    ) -> BaseLLM:
        load_dotenv()
        
        if model_name is None:
            model_name = config.DEFAULT_LLM_MODEL
        
        if provider.lower() == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", config.API_KEYS.get("gemini", ""))
            if not api_key:
                raise ValueError("Gemini API key not found")
                
            genai.configure(api_key=api_key)
            
            llm_params = {
                "model": model_name,
                "temperature": temperature,
                **kwargs
            }
            
            if max_tokens is not None and not dynamic_length:
                llm_params["max_output_tokens"] = max_tokens
            
            return ChatGoogleGenerativeAI(**llm_params)
            
        elif provider.lower() == "openai":
            api_key = os.getenv("OPENAI_API_KEY", config.API_KEYS.get("openai", ""))
            if not api_key:
                raise ValueError("OpenAI API key not found")
            
            llm_params = {
                "model": model_name,
                "temperature": temperature,
                "api_key": api_key,
                **kwargs
            }
            
            # Chỉ thiết lập max_tokens nếu có giá trị cụ thể và không yêu cầu độ dài động
            if max_tokens is not None and not dynamic_length:
                llm_params["max_tokens"] = max_tokens
                
            return ChatOpenAI(**llm_params)
            
        elif provider.lower() == "huggingface":
            # Initialize tokenizer and model
            try:
                print(f"Loading HuggingFace model: {model_name}")
                tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                )
                
                # Add pad token if it doesn't exist
                if tokenizer.pad_token is None:
                    tokenizer.pad_token = tokenizer.eos_token
                
                # For Llama and Qwen models, we load the model directly
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
                        "device": kwargs.get("device", 0 if kwargs.get("use_gpu", False) else -1),
                        "do_sample": True,
                        "temperature": temperature,
                        "pad_token_id": tokenizer.eos_token_id,
                        **kwargs
                    }
                
                # Chỉ thiết lập max_length nếu có giá trị cụ thể và không yêu cầu độ dài động
                if max_tokens is not None and not dynamic_length:
                    pipe_params["max_length"] = max_tokens
                
                # Create HuggingFace pipeline
                pipe = pipeline(
                    "text-generation",
                    **pipe_params
                )
                
                # Create LangChain LLM
                return HuggingFacePipeline(pipeline=pipe)
            except Exception as e:
                raise ValueError(f"Error initializing HuggingFace model: {e}")
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    def create_llm_from_notebook(model_id="meta-llama/Llama-3.2-1B"):
        
        try:
            print(f"Loading model from notebook approach: {model_id}")
            
            # Initialize tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                trust_remote_code=True
            )
            
            # Initialize model with lower precision for memory efficiency
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                trust_remote_code=True,
                device_map="auto",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            
            # Add pad token if it doesn't exist
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # Create HuggingFace pipeline
            pipe = pipeline(
                task="text-generation",
                model=model,
                tokenizer=tokenizer,
                do_sample=True,
                temperature=0.7,
                top_p=0.95,
                repetition_penalty=1.15
            )
            
            # Create LangChain LLM
            llm = HuggingFacePipeline(pipeline=pipe)
            print("LLM initialized successfully!")
            return llm
            
        except Exception as e:
            print(f"Error initializing LLM: {e}")
            return None
            
    @staticmethod
    def create_chain(
        llm: BaseLLM,
        prompt_template: str = config.DEFAULT_RAG_PROMPT_TEMPLATE,
        input_variables: Optional[List[str]] = None,
        output_key: str = "result",
        **kwargs
    ) -> Chain:
        """
        Create an LLM chain with a prompt template.
        
        Args:
            llm: LLM instance
            prompt_template: Template for the prompt
            input_variables: Input variables for the prompt template
            output_key: Key for the output in the chain
            **kwargs: Additional keyword arguments for the chain
            
        Returns:
            An initialized LLMChain
        """
        if input_variables is None:
            input_variables = ["context", "question"]
            
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=input_variables
        )
        
        return LLMChain(
            llm=llm,
            prompt=prompt,
            output_key=output_key,
            **kwargs
        )


def get_default_llm() -> BaseLLM:
    """Get the default LLM."""
    return LLMFactory.create_llm(
        max_tokens=config.DEFAULT_MAX_TOKENS,
        dynamic_length=config.DYNAMIC_RESPONSE_LENGTH
    )
    
def setup_llm(model_id="meta-llama/Llama-3.2-1B"):
    """
    Set up LLM with given model ID (compatibility function for the notebook).
    
    Args:
        model_id: ID of the model to use
        
    Returns:
        LLM instance
    """
    return LLMFactory.create_llm_from_notebook(model_id)