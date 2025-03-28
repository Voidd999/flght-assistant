"""Manage the configuration of various retrievers.

This module provides functionality to create and manage retrievers for different
vector store backends, specifically Elasticsearch, Pinecone, and MongoDB.

The retrievers support filtering results by user_id to ensure data isolation between users.
"""

import os
from contextlib import contextmanager
from typing import Generator

from langchain_core.embeddings import Embeddings
from langchain_core.runnables import RunnableConfig
from langchain_core.vectorstores import VectorStoreRetriever

from app.core.chatbot.configuration import IndexConfiguration

## Encoder constructors


def make_text_encoder(model: str) -> Embeddings:
    """Connect to the configured text encoder."""
    provider, model = model.split("/", maxsplit=1)
    match provider:
        case "openai":
            from langchain_openai import AzureOpenAIEmbeddings

            return AzureOpenAIEmbeddings(model=model, deployment=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"])
        case _:
            raise ValueError(f"Unsupported embedding provider: {provider}")


## Retriever constructors

@contextmanager
def make_faiss_retriever(
    configuration: IndexConfiguration, embedding_model: Embeddings
) -> Generator[VectorStoreRetriever, None, None]:
    """Configure this agent to connect to the pre-built FAISS vector store."""
    from langchain_community.vectorstores import FAISS
    
    # Load pre-built FAISS index
    vstore = FAISS.load_local(
        folder_path="app/core/chatbot/kbs/store",
        embeddings=embedding_model,
        allow_dangerous_deserialization=True
    )
    
    search_kwargs = configuration.search_kwargs
    if "k" not in search_kwargs:
        search_kwargs["k"] = 5
        
    yield vstore.as_retriever(
        search_type="similarity",  # Explicitly set similarity search
        search_kwargs=search_kwargs
    )


@contextmanager
def make_retriever(config: RunnableConfig) -> Generator[VectorStoreRetriever, None, None]:
    """Create a retriever for the agent, based on the current configuration."""
    configuration = IndexConfiguration.from_runnable_config(config)
    embedding_model = make_text_encoder(configuration.embedding_model)
    match configuration.retriever_provider:
        case "faiss":
            with make_faiss_retriever(configuration, embedding_model) as retriever:
                yield retriever

        case _:
            raise ValueError(
                "Unrecognized retriever_provider in configuration. "
                f"Expected one of: {', '.join(Configuration.__annotations__['retriever_provider'].__args__)}\n"
                f"Got: {configuration.retriever_provider}"
            )
