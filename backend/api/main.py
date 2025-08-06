from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, AsyncGenerator, Any
import os
import json
import asyncio
from dotenv import load_dotenv
import sys
import uuid
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import LLMResult
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.analytics_agent import AnalyticsAgent
from db.supabase_client import supabase_manager

# Load environment variables
load_dotenv()

app = FastAPI(title="BrandBastion Analytics API")

# Initialize the analytics agent
analytics_agent = AnalyticsAgent()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Streaming callback handler
class StreamingCallbackHandler(AsyncCallbackHandler):
    """Callback handler for streaming LLM responses"""
    
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        self.text_id = str(uuid.uuid4())
        
    async def on_llm_start(self, serialized: dict, prompts: List[str], **kwargs) -> None:
        """Run when LLM starts"""
        await self.queue.put(json.dumps({'type': 'start'}))
        
    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Run on new LLM token"""
        await self.queue.put(json.dumps({
            'type': 'text', 
            'text': token,
            'id': self.text_id
        }))
        
    async def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Run when LLM ends"""
        # Signal end of text streaming
        await self.queue.put(None)

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    charts: Optional[List[str]] = None  # Changed from chart_urls
    comments: Optional[List[str]] = None
    model: Optional[str] = None  # Model to use for the chat (e.g., gpt-3.5-turbo, gpt-4)

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    insights: Optional[List[str]] = None
    requires_clarification: bool = False
    suggested_questions: Optional[List[str]] = None
    context_sources_count: Optional[int] = None

@app.get("/")
def read_root():
    return {"message": "BrandBastion Analytics API"}

@app.post("/api/chat")
async def chat_endpoint(chat_message: ChatMessage):
    try:
        print(f"[CHAT] Received message: {chat_message.message}")
        print(f"[CHAT] Model: {chat_message.model or 'default (gpt-3.5-turbo)'}")
        print(f"[CHAT] Charts: {len(chat_message.charts) if chat_message.charts else 0}")
        print(f"[CHAT] Comments: {len(chat_message.comments) if chat_message.comments else 0}")
        
        # Create or get conversation
        if chat_message.conversation_id:
            conversation = await supabase_manager.get_conversation(chat_message.conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            conversation_id = chat_message.conversation_id
        else:
            # Create new conversation
            conversation = await supabase_manager.create_conversation(
                title=f"Analytics Session - {chat_message.message[:50]}..."
            )
            conversation_id = conversation['id']
        
        print(f"[CHAT] Using conversation ID: {conversation_id}")
        
        # Save user message
        await supabase_manager.add_message(
            conversation_id=conversation_id,
            role="user",
            content=chat_message.message,
            metadata={
                "charts_count": len(chat_message.charts) if chat_message.charts else 0,
                "comments_count": len(chat_message.comments) if chat_message.comments else 0
            }
        )
        
        print(f"[CHAT] Saved user message to database")
        
        # Process charts and comments if provided
        if chat_message.charts or chat_message.comments:
            # Create indices from the data
            print(f"[CHAT] Creating indices from data...")
            analytics_agent.create_indices_from_data(
                charts=chat_message.charts,
                comments=chat_message.comments
            )
        
        print(f"[CHAT] About to create streaming function...")
        
        # Create SSE stream generator with LangChain streaming
        async def generate_stream():
            print(f"[STREAM] generate_stream() function called!")
            queue = asyncio.Queue()
            callback_handler = StreamingCallbackHandler(queue)
            
            # Run agent with streaming in background
            print(f"[STREAM] Creating task for analytics agent...")
            task = asyncio.create_task(
                analytics_agent.arun_with_streaming(
                    query=chat_message.message,
                    charts=chat_message.charts,
                    comments=chat_message.comments,
                    callback_handler=callback_handler,
                    model=chat_message.model
                )
            )
            print(f"[STREAM] Task created successfully")
            
            # Stream tokens as they arrive
            print(f"[STREAM] Starting token streaming loop...")
            while True:
                try:
                    # Wait for next event with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=0.5)
                    
                    if event is None:  # End of streaming
                        print(f"[STREAM] Received end of streaming signal")
                        break
                        
                    yield f"data: {event}\n\n"
                    
                except asyncio.TimeoutError:
                    # Check if task is done
                    if task.done():
                        break
                    continue
                except Exception as e:
                    print(f"[STREAM ERROR] {e}")
                    break
            
            # Wait for task to complete and get result
            try:
                result = await task
                print(f"[STREAM] Task completed, result keys: {list(result.keys()) if result else 'None'}")
                print(f"[STREAM] Suggested questions: {result.get('suggested_questions', [])}")
                
                # Save assistant response to database
                await supabase_manager.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=result.get("response", ""),
                    metadata={
                        "insights": result.get("insights", []),
                        "suggested_questions": result.get("suggested_questions", []),
                        "requires_clarification": result.get("requires_clarification", False),
                        "context_sources": len(result.get("context_sources", []))
                    }
                )
                
                # Save analysis if insights were generated
                if result.get("insights"):
                    await supabase_manager.save_analysis(
                        conversation_id=conversation_id,
                        query=chat_message.message,
                        insights=result.get("insights", []),
                        context_sources=result.get("context_sources", [])
                    )
                
                print(f"[CHAT] Agent result: {result}")
                
                # Send metadata after streaming is complete
                metadata = {
                    'type': 'data',
                    'data': {
                        'conversationId': conversation_id,
                        'insights': result.get("insights", []),
                        'requires_clarification': result.get("requires_clarification", False),
                        'suggested_questions': result.get("suggested_questions", []),
                        'context_sources_count': len(result.get("context_sources", []))
                    }
                }
                print(f"[STREAM] Sending metadata: {metadata}")
                yield f"data: {json.dumps(metadata)}\n\n"
                
            except Exception as e:
                print(f"[STREAM ERROR] Failed to get result: {e}")
                import traceback
                print(f"[STREAM ERROR] Traceback: {traceback.format_exc()}")
            
            # Send finish event
            yield f"data: {json.dumps({'type': 'finish'})}\n\n"
        
        print(f"[CHAT] About to return StreamingResponse...")
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    except HTTPException as he:
        print(f"[CHAT ERROR] HTTP Exception: {he.detail}")
        raise
    except Exception as e:
        print(f"[CHAT ERROR] Unexpected error: {e}")
        print(f"[CHAT ERROR] Error type: {type(e).__name__}")
        import traceback
        print(f"[CHAT ERROR] Traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations")
async def list_conversations(limit: int = 10):
    """List recent conversations"""
    try:
        conversations = await supabase_manager.list_conversations(limit=limit)
        return {"conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation details with messages"""
    try:
        conversation = await supabase_manager.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = await supabase_manager.get_messages(conversation_id)
        analyses = await supabase_manager.get_analyses(conversation_id)
        
        return {
            "conversation": conversation,
            "messages": messages,
            "analyses": analyses
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    try:
        deleted = await supabase_manager.delete_conversation(conversation_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    """Health check endpoint"""
    supabase_connected = False
    try:
        supabase_connected = supabase_manager.test_connection()
    except:
        pass
    
    return {
        "status": "healthy",
        "supabase_connected": supabase_connected
    }