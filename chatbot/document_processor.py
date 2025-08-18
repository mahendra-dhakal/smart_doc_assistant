import os
import pickle
from typing import List, Optional
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.schema import Document


class DocumentProcessor:
    def __init__(self, api_key: str):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", 
            google_api_key=api_key
        )
        self.vector_store = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def load_documents(self, documents_path: str) -> List[Document]:
        """Load all PDF documents from the specified directory"""
        if not os.path.exists(documents_path):
            return []
        
        loader = DirectoryLoader(
            documents_path,
            glob="*.pdf",
            loader_cls=PyPDFLoader
        )
        documents = loader.load()
        return documents
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks"""
        return self.text_splitter.split_documents(documents)
    
    def create_vector_store(self, documents: List[Document]) -> FAISS:
        """Create FAISS vector store from documents"""
        if not documents:
            # Create empty vector store if no documents
            dummy_doc = Document(page_content="No documents loaded", metadata={})
            self.vector_store = FAISS.from_documents([dummy_doc], self.embeddings)
        else:
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
        return self.vector_store
    
    def save_vector_store(self, path: str):
        """Save vector store to disk"""
        if self.vector_store:
            self.vector_store.save_local(path)
    
    def load_vector_store(self, path: str) -> Optional[FAISS]:
        """Load vector store from disk"""
        if os.path.exists(path):
            self.vector_store = FAISS.load_local(
                path, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
            return self.vector_store
        return None
    
    def process_documents(self, documents_path: str, vector_store_path: str = "vector_store") -> FAISS:
        """Complete document processing pipeline"""
        # Try to load existing vector store first
        if self.load_vector_store(vector_store_path):
            return self.vector_store
        
        # Load and process documents
        documents = self.load_documents(documents_path)
        chunks = self.split_documents(documents)
        vector_store = self.create_vector_store(chunks)
        
        # Save vector store
        self.save_vector_store(vector_store_path)
        
        return vector_store
    
    def search_documents(self, query: str, k: int = 4) -> List[Document]:
        """Search for relevant documents"""
        if not self.vector_store:
            return []
        
        results = self.vector_store.similarity_search(query, k=k)
        return results