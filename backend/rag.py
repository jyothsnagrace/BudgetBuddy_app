"""
RAG system for Budget Buddy chatbot.
Indexes the requested finance web pages and PDF into a LangChain vector store.
"""

import math
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

os.environ.setdefault("USER_AGENT", "BudgetBuddy/1.0 (+https://budgetbuddy.local)")

try:
    from langchain_community.document_loaders import PDFMinerLoader, WebBaseLoader
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import InMemoryVectorStore
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    Embeddings = object
    print(f"Warning: LangChain import failed: {e}")
    print("Warning: LangChain not available. RAG functionality disabled.")


WEB_PAGES = [
    "https://finance.yahoo.com/markets/",
    "https://thebudgetmom.com/the-secret-to-personal-finance-i-never-learned-about-in-business-school/",
    "https://thebudgetmom.com/the-hidden-cost-of-financial-comparison-in-the-age-of-social-media/",
    "https://thebudgetmom.com/the-truth-about-tax-refunds/",
    "https://thebudgetmom.com/why-more-money-doesnt-fix-bad-money-habits-and-what-actually-does/",
    "https://thebudgetmom.com/recovering-financially-after-the-holidays/",
]

PDF_URL = "https://cdn.bookey.app/files/pdf/book/en/personal-finance-for-dummies.pdf"


class HashEmbeddings(Embeddings):
    """Lightweight deterministic embeddings for local retrieval."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_text(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_text(text)

    def _embed_text(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[a-z0-9]+", text.lower())

        if not tokens:
            return vector

        for token in tokens:
            index = hash(token) % self.dimension
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class RAGRetriever:
    """Loads finance sources and retrieves relevant context for chat."""

    def __init__(self, cache_directory: str = "./rag_cache"):
        self.cache_directory = Path(cache_directory)
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        self.pdf_cache_path = self.cache_directory / "personal-finance-for-dummies.pdf"
        self.vectorstore: Optional[InMemoryVectorStore] = None
        self.enabled = LANGCHAIN_AVAILABLE
        self._initialized = False
        self._init_lock = threading.Lock()
        self.embeddings: Optional[HashEmbeddings] = HashEmbeddings() if LANGCHAIN_AVAILABLE else None

        if not LANGCHAIN_AVAILABLE:
            print("RAG: Required packages not available")

    def _ensure_initialized(self) -> bool:
        if not self.enabled:
            return False

        if self._initialized and self.vectorstore is not None:
            return True

        with self._init_lock:
            if self._initialized and self.vectorstore is not None:
                return True

            self._build_vectorstore()
            self._initialized = True

        return self.vectorstore is not None

    def _build_vectorstore(self) -> None:
        try:
            documents = self._load_documents()
            if not documents:
                print("RAG: No source documents were loaded")
                self.vectorstore = None
                return

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1200,
                chunk_overlap=200,
                length_function=len,
            )
            chunks = text_splitter.split_documents(documents)

            if not chunks:
                print("RAG: No document chunks were created")
                self.vectorstore = None
                return

            self.vectorstore = InMemoryVectorStore(self.embeddings)
            self.vectorstore.add_documents(chunks)
            print(f"RAG: Indexed {len(chunks)} chunks from {len(documents)} source documents")
        except Exception as error:
            print(f"RAG: Failed to build vector store: {error}")
            self.vectorstore = None

    def _load_documents(self) -> List[Document]:
        documents: List[Document] = []

        documents.extend(self._load_web_documents())

        pdf_document = self._load_pdf_document()
        if pdf_document:
            documents.extend(pdf_document)

        return documents

    def _load_web_documents(self) -> List[Document]:
        try:
            loader = WebBaseLoader(web_paths=WEB_PAGES)
            documents = loader.load()
            for document in documents:
                document.metadata.setdefault("source", document.metadata.get("title") or "web")
            return documents
        except Exception as error:
            print(f"RAG: Bulk web load failed, retrying per-page: {error}")

        documents: List[Document] = []
        for url in WEB_PAGES:
            try:
                loader = WebBaseLoader(web_paths=[url])
                page_documents = loader.load()
                for document in page_documents:
                    document.metadata["source"] = url
                documents.extend(page_documents)
            except Exception as error:
                print(f"RAG: Failed to load {url}: {error}")

        return documents

    def _load_pdf_document(self) -> List[Document]:
        pdf_path = self._download_pdf()
        if not pdf_path:
            return []

        try:
            loader = PDFMinerLoader(str(pdf_path))
            documents = loader.load()
            for document in documents:
                document.metadata["source"] = PDF_URL
            return documents
        except Exception as error:
            print(f"RAG: Failed to load PDF source: {error}")
            return []

    def _download_pdf(self) -> Optional[Path]:
        if self.pdf_cache_path.exists():
            return self.pdf_cache_path

        try:
            response = requests.get(PDF_URL, timeout=60)
            response.raise_for_status()
            self.pdf_cache_path.write_bytes(response.content)
            return self.pdf_cache_path
        except Exception as error:
            print(f"RAG: Failed to download PDF source: {error}")
            return None

    def retrieve_documents(self, query: str, k: int = 4) -> List[Document]:
        if not self._ensure_initialized() or not self.vectorstore:
            return []

        try:
            return self.vectorstore.similarity_search(query, k=k)
        except Exception as error:
            print(f"RAG: Error retrieving context: {error}")
            return []

    def retrieve_context(self, query: str, k: int = 4) -> Dict[str, Any]:
        documents = self.retrieve_documents(query, k=k)
        if not documents:
            return {"context": "", "sources": []}

        context_parts: List[str] = []
        sources: List[str] = []

        for index, document in enumerate(documents, start=1):
            source = self._normalize_source(document.metadata.get("source", "Unknown source"))
            sources.append(source)
            context_parts.append(
                f"Source {index}: {source}\n{document.page_content.strip()}"
            )

        unique_sources = list(dict.fromkeys(sources))
        return {
            "context": "\n\n".join(context_parts),
            "sources": unique_sources,
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "initialized": self._initialized,
            "vectorstore_loaded": self.vectorstore is not None,
            "cached_pdf": self.pdf_cache_path.exists(),
            "web_sources": len(WEB_PAGES),
        }

    def _normalize_source(self, source: str) -> str:
        if not source:
            return "Unknown source"

        if source == PDF_URL:
            return "Personal Finance For Dummies PDF"

        if source.startswith("http"):
            cleaned = source.replace("https://", "").replace("http://", "")
            return cleaned.rstrip("/")

        return source