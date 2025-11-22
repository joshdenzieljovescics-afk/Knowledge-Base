# api/chat_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from services.chat_service import ChatService
from middleware.jwt_middleware import get_current_user
from middleware.security_middleware import (
    validate_string_length,
    MAX_MESSAGE_LENGTH,
    MAX_SESSION_TITLE_LENGTH
)

chat_router = APIRouter(prefix='/chat', tags=['chat'])
chat_service = ChatService()

# Request models with validation
class CreateSessionRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=MAX_SESSION_TITLE_LENGTH)
    initial_message: Optional[str] = Field(None, max_length=MAX_MESSAGE_LENGTH)
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None and v.strip():
            return validate_string_length(v.strip(), MAX_SESSION_TITLE_LENGTH, "title")
        return v
    
    @field_validator('initial_message')
    @classmethod
    def validate_message(cls, v):
        if v is not None and v.strip():
            return validate_string_length(v.strip(), MAX_MESSAGE_LENGTH, "message")
        return v

class SendMessageRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return validate_string_length(v.strip(), MAX_MESSAGE_LENGTH, "message")
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Session ID cannot be empty")
        return v.strip()

@chat_router.post('/session/new')
async def create_session(
    request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new chat session"""
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        # Create session
        session = chat_service.create_session(user_id, request.title)
        
        # Process initial message if provided
        if request.initial_message:
            chat_service.process_message(
                session_id=session['session_id'],
                user_message=request.initial_message,
                options=request.options or {},
                user_id=user_id
            )
        
        return {
            'success': True,
            'session_id': session['session_id'],
            'created_at': session['created_at'],
            'message': 'Session created successfully'
        }
        
    except Exception as e:
        print(f"Error creating session: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@chat_router.post('/message')
async def send_message(
    request: SendMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a message in a chat session"""
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        if not request.session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='session_id is required'
            )
        
        if not request.message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='message is required'
            )
        
        # Process message
        response = chat_service.process_message(
            session_id=request.session_id,
            user_message=request.message,
            options=request.options or {},
            user_id=user_id
        )
        
        return {
            'success': True,
            **response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@chat_router.get('/session/{session_id}/history')
async def get_session_history(
    session_id: str,
    limit: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get session history with messages"""
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        result = chat_service.get_session_history(session_id, limit, user_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Session not found or access denied'
            )
        
        return {
            'success': True,
            'session_id': session_id,
            'session': result['session'],
            'messages': result['messages'],
            'total_messages': len(result['messages'])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting session history: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@chat_router.get('/sessions')
async def get_user_sessions(
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get all sessions for a user"""
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        result = chat_service.get_user_sessions(user_id, limit, offset)
        
        return {
            'success': True,
            **result
        }
        
    except Exception as e:
        print(f"Error getting user sessions: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@chat_router.get('/session/{session_id}')
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get session details"""
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        result = chat_service.get_session_history(session_id, limit=0, user_id=user_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Session not found or access denied'
            )
        
        return {
            'success': True,
            **result['session']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@chat_router.delete('/session/{session_id}')
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a session"""
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        success = chat_service.delete_session(session_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Session not found, already deleted, or access denied'
            )
        
        return {
            'success': True,
            'message': 'Session deleted successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@chat_router.get('/session/{session_id}/tokens')
async def get_session_tokens(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get token usage for a specific session"""
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        # Validate ownership
        session = chat_service.chat_db.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        if session.get('user_id') != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        token_data = chat_service.chat_db.get_session_token_usage(session_id)
        
        return {
            'success': True,
            'session_id': session_id,
            **token_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting session tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@chat_router.get('/user/tokens')
async def get_user_tokens(
    current_user: dict = Depends(get_current_user)
):
    """Get total token usage for the current user"""
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        token_data = chat_service.chat_db.get_user_total_tokens(user_id)
        
        return {
            'success': True,
            'user_id': user_id,
            **token_data
        }
        
    except Exception as e:
        print(f"Error getting user tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

