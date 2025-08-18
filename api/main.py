import os
import logging
from datetime import datetime
from typing import List, Optional
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from api.models import (
    ChatMessage, ChatResponse, AppointmentStatus, 
    DocumentUploadResponse, HealthCheck, ErrorResponse, SessionInfo
)
from api.session_manager import SessionManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Smart Doc Assistant API",
    description="A smart chatbot API that answers questions from documents and handles appointment booking through conversational forms",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize session manager
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    logger.error("GOOGLE_API_KEY not found in environment variables")
    raise ValueError("GOOGLE_API_KEY is required")

session_manager = SessionManager(api_key)

# Ensure documents directory exists
documents_dir = Path("documents")
documents_dir.mkdir(exist_ok=True)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            status_code=500
        ).dict()
    )

# Background task for session cleanup
async def cleanup_sessions():
    """Background task to cleanup expired sessions"""
    cleaned = session_manager.cleanup_expired_sessions()
    if cleaned > 0:
        logger.info(f"Cleaned up {cleaned} expired sessions")

@app.get("/", response_model=HealthCheck)
async def root():
    """Root endpoint with health check"""
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )

@app.post("/chat/new-session", response_model=dict)
async def create_new_session():
    """Create a new chat session"""
    try:
        session_id = session_manager.create_session()
        logger.info(f"Created new session: {session_id}")
        return {"session_id": session_id, "message": "New session created successfully"}
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(
    message_data: ChatMessage,
    background_tasks: BackgroundTasks
):
    """Main chat endpoint"""
    try:
        # Create session if not provided
        session_id = message_data.session_id
        if not session_id:
            session_id = session_manager.create_session()
            logger.info(f"Created new session for chat: {session_id}")
        
        # Get chatbot for session
        chatbot = session_manager.get_chatbot(session_id)
        if not chatbot:
            # Session might have expired, create new one
            session_id = session_manager.create_session()
            chatbot = session_manager.get_chatbot(session_id)
            logger.info(f"Session expired, created new session: {session_id}")
        
        # Process message
        response_data = chatbot.chat(message_data.message)
        session_manager.increment_message_count(session_id)
        
        # Schedule background cleanup
        background_tasks.add_task(cleanup_sessions)
        
        return ChatResponse(
            response=response_data["response"],
            source=response_data.get("source", "unknown"),
            session_id=session_id,
            form_active=response_data.get("form_active", False),
            appointment_booked=response_data.get("appointment_booked", False),
            documents_found=response_data.get("documents_found"),
            source_files=response_data.get("source_files")
        )
    
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.get("/chat/session/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """Get information about a specific session"""
    session_info = session_manager.get_session_info(session_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionInfo(**session_info)

@app.get("/chat/session/{session_id}/appointment-status", response_model=AppointmentStatus)
async def get_appointment_status(session_id: str):
    """Get appointment form status for a session"""
    chatbot = session_manager.get_chatbot(session_id)
    if not chatbot:
        raise HTTPException(status_code=404, detail="Session not found")
    
    status = chatbot.get_appointment_status()
    return AppointmentStatus(**status)

@app.post("/chat/session/{session_id}/reset-form")
async def reset_appointment_form(session_id: str):
    """Reset appointment form for a session"""
    if not session_manager.reset_session_form(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Appointment form reset successfully"}

@app.post("/chat/session/{session_id}/clear-memory")
async def clear_session_memory(session_id: str):
    """Clear conversation memory for a session"""
    if not session_manager.clear_session_memory(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session memory cleared successfully"}

@app.delete("/chat/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific session"""
    if not session_manager.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted successfully"}

@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload PDF documents to the knowledge base"""
    try:
        uploaded_files = []
        documents_dir = Path("documents")
        documents_dir.mkdir(exist_ok=True)
        
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Only PDF files are allowed. Got: {file.filename}"
                )
            
            # Save file
            file_path = documents_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_files.append(file.filename)
            logger.info(f"Uploaded document: {file.filename}")
        
        # Note: In a production system, you'd want to reprocess the vector store
        # for all existing sessions or implement a more sophisticated document management system
        
        return DocumentUploadResponse(
            message=f"Successfully uploaded {len(uploaded_files)} document(s)",
            uploaded_files=uploaded_files,
            success=True
        )
    
    except Exception as e:
        logger.error(f"Document upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")

@app.get("/documents/list")
async def list_documents():
    """List all uploaded documents"""
    try:
        documents_dir = Path("documents")
        if not documents_dir.exists():
            return {"documents": []}
        
        documents = [f.name for f in documents_dir.glob("*.pdf")]
        return {"documents": documents}
    
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.get("/admin/sessions")
async def get_active_sessions():
    """Get information about all active sessions (admin endpoint)"""
    try:
        session_count = session_manager.get_active_session_count()
        return {
            "active_sessions": session_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get session info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session info: {str(e)}")

@app.post("/admin/cleanup")
async def manual_cleanup():
    """Manually trigger session cleanup (admin endpoint)"""
    try:
        cleaned = session_manager.cleanup_expired_sessions()
        return {
            "message": f"Cleaned up {cleaned} expired sessions",
            "cleaned_count": cleaned
        }
    except Exception as e:
        logger.error(f"Failed to cleanup sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup sessions: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("Starting Smart Doc Assistant API Server...")
    print("API Documentation: http://localhost:8000/docs")
    print("Interactive Testing: http://localhost:8000/redoc") 
    print("Chat endpoint: POST http://localhost:8000/chat")
    print("Upload documents: POST http://localhost:8000/documents/upload")
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )