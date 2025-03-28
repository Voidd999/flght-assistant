"""Build and save FAISS vector store from FAQ markdown files."""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings

# Load environment variables
load_dotenv()

def load_markdown_files(faqs_dir: str = "faqs") -> List[Document]:
    """Load all markdown files from the faqs directory."""
    docs = []
    faqs_path = Path(faqs_dir).absolute()
    
    if not faqs_path.exists():
        raise ValueError(f"FAQs directory not found: {faqs_dir}")
    
    for md_file in faqs_path.glob("*.md"):
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
            # Store filename in metadata for reference
            docs.append(Document(
                page_content=content,
                metadata={"source": md_file.name}
            ))
    
    return docs

def split_documents(docs: List[Document]) -> List[Document]:
    """Split markdown documents into smaller chunks."""
    splitter = MarkdownTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        keep_separator=False
    )
    
    return splitter.split_documents(docs)

def build_and_save_vectordb() -> None:
    """Build and save FAISS vector store from documents."""
    docs = load_markdown_files()
    split_docs = split_documents(docs)
    
    embedding_model = AzureOpenAIEmbeddings(
        model="text-embedding-3-small",
        deployment=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]
    )
    
    # Create and save FAISS index
    vstore = FAISS.from_documents(split_docs, embedding_model)
    vstore.save_local("storage/faiss")

def main():
    """Main function to build and save the vectorstore."""
    docs = load_markdown_files()
    split_docs = split_documents(docs)
    build_and_save_vectordb()
    return

if __name__ == "__main__":
    main()
