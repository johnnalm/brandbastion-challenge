"""
Supabase client configuration and utilities
"""
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseManager:
    """Manage Supabase connections and operations"""
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.service_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.storage_bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "brandbastion-files")
        
        if not self.url or not self.key:
            raise ValueError("Supabase URL and KEY must be set in environment variables")
        
        # Use anon key for public operations, service key for admin operations
        self.client: Client = create_client(self.url, self.key)
        self.admin_client: Client = create_client(self.url, self.service_key) if self.service_key else None
    
    # Conversation Management
    
    async def create_conversation(self, user_id: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
        """Create a new conversation"""
        data = {
            "title": title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "metadata": {}
        }
        
        if user_id:
            data["user_id"] = user_id
        
        result = self.client.table("conversations").insert(data).execute()
        return result.data[0] if result.data else None
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID"""
        result = self.client.table("conversations").select("*").eq("id", conversation_id).execute()
        return result.data[0] if result.data else None
    
    async def list_conversations(self, user_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """List conversations, optionally filtered by user"""
        query = self.client.table("conversations").select("*")
        
        if user_id:
            query = query.eq("user_id", user_id)
        
        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data
    
    # Message Management
    
    async def add_message(self, conversation_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Add a message to a conversation"""
        data = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        
        result = self.client.table("messages").insert(data).execute()
        return result.data[0] if result.data else None
    
    async def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a conversation"""
        result = self.client.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at").execute()
        return result.data
    
    # File Storage Management
    
    async def upload_file(self, file_content: bytes, file_name: str, conversation_id: str, file_type: str = "application/pdf") -> Dict[str, Any]:
        """Upload a file to Supabase Storage"""
        # Create unique path
        file_id = str(uuid.uuid4())
        storage_path = f"{conversation_id}/{file_id}/{file_name}"
        
        # Upload to storage
        result = self.client.storage.from_(self.storage_bucket).upload(
            path=storage_path,
            file=file_content,
            file_options={"content-type": file_type}
        )
        
        if result.error:
            raise Exception(f"Failed to upload file: {result.error}")
        
        # Save file metadata
        file_data = {
            "conversation_id": conversation_id,
            "file_name": file_name,
            "file_type": file_type,
            "storage_path": storage_path,
            "metadata": {
                "size": len(file_content),
                "upload_date": datetime.now().isoformat()
            }
        }
        
        db_result = self.client.table("processed_files").insert(file_data).execute()
        return db_result.data[0] if db_result.data else None
    
    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Get a signed URL for file access"""
        result = self.client.storage.from_(self.storage_bucket).create_signed_url(
            path=storage_path,
            expires_in=expires_in
        )
        return result["signedURL"] if result else None
    
    async def list_files(self, conversation_id: str) -> List[Dict[str, Any]]:
        """List all files in a conversation"""
        result = self.client.table("processed_files").select("*").eq("conversation_id", conversation_id).execute()
        return result.data
    
    # Analysis Storage
    
    async def save_analysis(self, conversation_id: str, query: str, insights: List[str], context_sources: List[Dict]) -> Dict[str, Any]:
        """Save an analysis result"""
        data = {
            "conversation_id": conversation_id,
            "query": query,
            "insights": {"items": insights},
            "context_sources": context_sources
        }
        
        result = self.client.table("saved_analyses").insert(data).execute()
        return result.data[0] if result.data else None
    
    async def get_analyses(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all analyses for a conversation"""
        result = self.client.table("saved_analyses").select("*").eq("conversation_id", conversation_id).order("created_at", desc=True).execute()
        return result.data
    
    # Utility Methods
    
    async def update_file_embeddings_status(self, file_id: str, status: bool = True) -> bool:
        """Update embeddings created status for a file"""
        result = self.client.table("processed_files").update({"embeddings_created": status}).eq("id", file_id).execute()
        return bool(result.data)
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all related data (cascades)"""
        result = self.client.table("conversations").delete().eq("id", conversation_id).execute()
        return bool(result.data)
    
    def test_connection(self) -> bool:
        """Test Supabase connection"""
        try:
            # Try to query the conversations table
            result = self.client.table("conversations").select("id").limit(1).execute()
            return True
        except Exception as e:
            print(f"Supabase connection test failed: {e}")
            return False


# Singleton instance
supabase_manager = SupabaseManager()