from typing import Any, Dict
from langchain_core.language_models import BaseChatModel
from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq

import os

class LLMConfig:
    def __init__(self, provider: str, model: str, config: Dict[str, Any]):
        self.provider = provider
        self.model = model
        self.config = config

class LLMManager:
    @staticmethod
    def get_llm(config: LLMConfig) -> BaseChatModel:
        """Factory method to create LLM instances"""
        if config.provider == "azure":
            return AzureChatOpenAI(
                model_name=config.model,
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                **config.config
            )
        elif config.provider == "google":
            return ChatGoogleGenerativeAI(
                model=config.model,
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                **config.config
            )
        elif config.provider == "ollama":
            return ChatOllama(
                model=config.model,
                base_url=os.getenv("OLLAMA_BASE_URL"),
                **config.config
            )
        elif config.provider == "groq":
            return ChatGroq(
                model_name=config.model,
                groq_api_key=os.getenv("GROQ_API_KEY"),
                **config.config
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")

    @staticmethod
    def from_settings(settings: Dict[str, Any]) -> BaseChatModel:
        """Create LLM instance from settings dictionary"""
        config = LLMConfig(
            provider=settings["provider"],
            model=settings["model"],
            config=settings["config"]
        )
        return LLMManager.get_llm(config) 