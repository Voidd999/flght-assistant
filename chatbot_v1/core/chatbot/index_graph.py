"""This "graph" simply exposes an endpoint for a user to upload docs to be indexed."""

from typing import Optional, Sequence

from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph

from .retrieval import retrieval
from .configuration import IndexConfiguration
from .index_state import IndexState


def get_docs(docs: Sequence[Document], config: RunnableConfig) -> list[Document]:
    return [Document(page_content=doc.page_content, metadata={**doc.metadata}) for doc in docs]

async def index_docs(
    state: IndexState, *, config: Optional[RunnableConfig] = None
) -> dict[str, str]:
    """Asynchronously index documents in the given state using the configured retriever.

    This function takes the documents from the state, ensures they have a user ID,
    adds them to the retriever's index, and then signals for the documents to be
    deleted from the state.

    Args:
        state (IndexState): The current state containing documents and retriever.
        config (Optional[RunnableConfig]): Configuration for the indexing process.r
    """
    if not config:
        raise ValueError("Configuration required to run index_docs.")
    with retrieval.make_retriever(config) as retriever:
        stamped_docs = get_docs(state.docs, config)
        await retriever.aadd_documents(stamped_docs)
        
    return {"docs": "delete"}


# Define a new graph


builder = StateGraph(IndexState, config_schema=IndexConfiguration)
builder.add_node(index_docs)
builder.add_edge("__start__", "index_docs")
# Finally, we compile it!
# This compiles it into a graph you can invoke and deploy.
graph = builder.compile()
graph.name = "IndexGraph"
