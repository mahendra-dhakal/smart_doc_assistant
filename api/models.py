from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class ChatMessage(BaseModel):
    """Model for chat messages"""
    message: str = Field(..., description="User message", min_length=1)
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")


class ChatResponse(BaseModel):
    """Model for chat responses"""
    response: str = Field(..., description="Bot response")
    source: str = Field(..., description="Source of response (document_processor, appointment_agent, etc.)")
    session_id: str = Field(..., description="Session ID")
    form_active: Optional[bool] = Field(False, description="Whether appointment form is active")
    appointment_booked: Optional[bool] = Field(False, description="Whether appointment was booked")
    documents_found: Optional[bool] = Field(None, description="Whether relevant documents were found")
    source_files: Optional[List[str]] = Field(None, description="Source files referenced")


class AppointmentStatus(BaseModel):
    """Model for appointment form status"""
    active: bool = Field(..., description="Whether form is active")
    completed: bool = Field(..., description="Whether form is completed")
    state: str = Field(..., description="Current form state")
    collected_info: Dict[str, Any] = Field(..., description="Currently collected information")


class DocumentUploadResponse(BaseModel):
    """Model for document upload response"""
    message: str = Field(..., description="Upload status message")
    uploaded_files: List[str] = Field(..., description="List of uploaded file names")
    success: bool = Field(..., description="Whether upload was successful")


class HealthCheck(BaseModel):
    """Model for health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    timestamp: str = Field(..., description="Current timestamp")


class ErrorResponse(BaseModel):
    """Model for error responses"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    status_code: int = Field(..., description="HTTP status code")


class SessionInfo(BaseModel):
    """Model for session information"""
    session_id: str = Field(..., description="Session ID")
    created_at: str = Field(..., description="Session creation timestamp")
    last_activity: str = Field(..., description="Last activity timestamp")
    message_count: int = Field(..., description="Number of messages in session")
    form_active: bool = Field(..., description="Whether appointment form is active")