# api/chat_routes.py
from flask import Blueprint, request, jsonify
from services.chat_service import ChatService

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')
chat_service = ChatService()

@chat_bp.route('/session/new', methods=['POST'])
def create_session():
    """Create a new chat session"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default-user')
        title = data.get('title')
        initial_message = data.get('initial_message')
        
        # Create session
        session = chat_service.create_session(user_id, title)
        
        # Process initial message if provided
        if initial_message:
            chat_service.process_message(
                session_id=session['session_id'],
                user_message=initial_message,
                options=data.get('options', {})
            )
        
        return jsonify({
            'success': True,
            'session_id': session['session_id'],
            'created_at': session['created_at'],
            'message': 'Session created successfully'
        }), 200
        
    except Exception as e:
        print(f"Error creating session: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/message', methods=['POST'])
def send_message():
    """Send a message in a chat session"""
    try:
        data = request.get_json()
        
        session_id = data.get('session_id')
        message = data.get('message')
        options = data.get('options', {})
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id is required'
            }), 400
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'message is required'
            }), 400
        
        # Process message
        response = chat_service.process_message(
            session_id=session_id,
            user_message=message,
            options=options
        )
        
        return jsonify({
            'success': True,
            **response
        }), 200
        
    except Exception as e:
        print(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/session/<session_id>/history', methods=['GET'])
def get_session_history(session_id):
    """Get session history with messages"""
    try:
        limit = request.args.get('limit', type=int)
        
        result = chat_service.get_session_history(session_id, limit)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'session': result['session'],
            'messages': result['messages'],
            'total_messages': len(result['messages'])
        }), 200
        
    except Exception as e:
        print(f"Error getting session history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/sessions', methods=['GET'])
def get_user_sessions():
    """Get all sessions for a user"""
    try:
        user_id = request.args.get('user_id', 'default-user')
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        result = chat_service.get_user_sessions(user_id, limit, offset)
        
        return jsonify({
            'success': True,
            **result
        }), 200
        
    except Exception as e:
        print(f"Error getting user sessions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session details"""
    try:
        result = chat_service.get_session_history(session_id, limit=0)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        return jsonify({
            'success': True,
            **result['session']
        }), 200
        
    except Exception as e:
        print(f"Error getting session: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session"""
    try:
        success = chat_service.delete_session(session_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Session not found or already deleted'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Session deleted successfully'
        }), 200
        
    except Exception as e:
        print(f"Error deleting session: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
