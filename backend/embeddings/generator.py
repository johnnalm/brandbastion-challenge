from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from typing import List, Dict, Any
import numpy as np
import os
from pathlib import Path
import pickle

class EmbeddingGenerator:
    """Generate embeddings for text data and manage FAISS index"""
    
    def __init__(self, model_name: str = "text-embedding-ada-002"):
        self.embeddings = OpenAIEmbeddings(
            model=model_name,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        self.index_path = Path(os.getenv("FAISS_INDEX_PATH", "/app/vector-db/indices"))
        self.index_path.mkdir(parents=True, exist_ok=True)
    
    def create_embeddings_from_texts(self, texts: List[str], metadatas: List[Dict[str, Any]] = None) -> FAISS:
        """Create embeddings from a list of texts"""
        # Split texts into chunks
        documents = self.text_splitter.create_documents(texts, metadatas=metadatas)
        
        # Create FAISS index
        vectorstore = FAISS.from_documents(documents, self.embeddings)
        
        return vectorstore
    
    def add_to_existing_index(self, index_name: str, texts: List[str], metadatas: List[Dict[str, Any]] = None):
        """Add new embeddings to an existing FAISS index"""
        index_path = self.index_path / index_name
        
        # Process in batches to avoid rate limits
        batch_size = 20
        vectorstore = None
        
        if index_path.exists():
            # Load existing index
            try:
                vectorstore = self.load_index(index_name)
            except FileNotFoundError:
                # Index was corrupted and removed, start fresh
                print(f"Starting fresh index for {index_name}")
                vectorstore = None
        
        # Process texts in batches
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size] if metadatas else None
            
            print(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} ({len(batch_texts)} texts)")
            
            # Split batch texts
            documents = self.text_splitter.create_documents(batch_texts, metadatas=batch_metadatas)
            
            if vectorstore is None:
                # Create new index with first batch
                vectorstore = FAISS.from_documents(documents, self.embeddings)
            else:
                # Add to existing index
                vectorstore.add_documents(documents)
        
        # Save updated index
        if vectorstore:
            self.save_index(vectorstore, index_name)
        
        return vectorstore
    
    def save_index(self, vectorstore: FAISS, index_name: str):
        """Save FAISS index to disk"""
        index_path = self.index_path / index_name
        
        # Use FAISS native save method instead of pickle
        vectorstore.save_local(str(index_path))
        
        print(f"Index saved to {index_path}")
    
    def load_index(self, index_name: str) -> FAISS:
        """Load FAISS index from disk"""
        index_path = self.index_path / index_name
        
        if not index_path.exists():
            raise FileNotFoundError(f"Index directory not found: {index_path}")
        
        # Check if required files exist
        index_file = index_path / "index.faiss"
        pkl_file = index_path / "index.pkl"
        
        if not (index_file.exists() and pkl_file.exists()):
            print(f"Warning: Index files incomplete in {index_path}. Removing directory.")
            import shutil
            shutil.rmtree(index_path, ignore_errors=True)
            raise FileNotFoundError(f"Index was incomplete and has been removed: {index_path}")
        
        try:
            # Use FAISS native load method
            vectorstore = FAISS.load_local(str(index_path), self.embeddings, allow_dangerous_deserialization=True)
            return vectorstore
        except Exception as e:
            print(f"Error loading index from {index_path}: {e}")
            print(f"Removing corrupted index directory...")
            import shutil
            shutil.rmtree(index_path, ignore_errors=True)
            raise FileNotFoundError(f"Index was corrupted and has been removed: {index_path}")
    
    def search_similar(self, index_name: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents in the index"""
        vectorstore = self.load_index(index_name)
        
        # Perform similarity search
        results = vectorstore.similarity_search_with_score(query, k=k)
        
        # Format results
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": float(score)
            })
        
        return formatted_results
    
    def create_index_from_pdf_data(self, pdf_data: Dict[str, Any], index_name: str = "charts"):
        """Create embeddings from parsed PDF data"""
        texts = []
        metadatas = []
        
        # Process text content
        for text_item in pdf_data.get('text', []):
            texts.append(text_item['content'])
            metadatas.append({
                "source": "pdf_text",
                "page": text_item['page']
            })
        
        # Process table data
        for table_item in pdf_data.get('tables', []):
            # Convert table to text representation
            table_text = self._table_to_text(table_item['data'])
            texts.append(table_text)
            metadatas.append({
                "source": "pdf_table",
                "page": table_item['page']
            })
        
        # Create and save index
        if texts:
            vectorstore = self.create_embeddings_from_texts(texts, metadatas)
            self.save_index(vectorstore, index_name)
            return True
        
        return False
    
    def create_index_from_comments(self, comments: List[Dict[str, Any]], index_name: str = "comments"):
        """Create embeddings from parsed comments"""
        texts = []
        metadatas = []
        
        for comment in comments:
            texts.append(comment['text'])
            metadatas.append({
                "source": "user_comment",
                "comment_id": comment['id']
            })
        
        # Create and save index
        if texts:
            vectorstore = self.create_embeddings_from_texts(texts, metadatas)
            self.save_index(vectorstore, index_name)
            return True
        
        return False
    
    def _table_to_text(self, table_data: List[List[str]]) -> str:
        """Convert table data to text representation"""
        if not table_data:
            return ""
        
        # Simple conversion - join cells with spaces and rows with newlines
        text_rows = []
        for row in table_data:
            text_rows.append(" | ".join(str(cell) for cell in row if cell))
        
        return "\n".join(text_rows)