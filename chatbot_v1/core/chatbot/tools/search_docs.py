"""Tool for searching documents in the knowledge base."""

from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langchain_core.runnables.config import RunnableConfig
from app.core.chatbot.retrieval import make_retriever
import logging

logger = logging.getLogger(__name__)
    
@tool
def search_docs(query: str, state: Annotated[dict, InjectedState], config: RunnableConfig) -> str:
    """Query knowledge base for any information before answering any questions."""    
    
    logger.info(f"TOOL: Searching for documents with query: {query}")
    
    try:
        with make_retriever(config) as retriever:
            docs = retriever.get_relevant_documents(query)
            logger.debug(f"Found {len(docs)} documents")
            
            if not docs:
                logger.debug("No documents found")
                return "No relevant documents found."
            
            results = []
            for i, doc in enumerate(docs, 1):
                content = doc.page_content.replace("\n", " ").strip()
                results.append(f"{i}. {content}")
                logger.debug(f"Doc {i}: {content[:50]}...")  # Truncate for readability
                
            logger.debug("Search completed successfully")
            return "\n\n".join(results)
            
    except Exception as e:
        logger.error(f"SEARCH_DOCS ERROR: {str(e)}")
        raise 