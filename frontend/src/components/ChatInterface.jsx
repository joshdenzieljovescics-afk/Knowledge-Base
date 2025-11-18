import React, { useState, useEffect, useRef } from 'react';
import '../css/ChatInterface.css';

function ChatInterface() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [error, setError] = useState('');
  
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const userId = 'user-123'; // TODO: Replace with actual user ID from auth

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [input]);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const res = await fetch(`http://localhost:8009/chat/sessions?user_id=${userId}`);
      const data = await res.json();
      if (data.success) {
        setSessions(data.sessions || []);
      }
    } catch (err) {
      console.error('Error loading sessions:', err);
      setError('Failed to load chat sessions');
    }
  };

  const createNewSession = async () => {
    try {
      const res = await fetch('http://localhost:8009/chat/session/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });
      const data = await res.json();
      
      if (data.success) {
        setCurrentSessionId(data.session_id);
        setMessages([]);
        setError('');
        await loadSessions();
      }
    } catch (err) {
      console.error('Error creating session:', err);
      setError('Failed to create new session');
    }
  };

  const loadSession = async (sessionId) => {
    try {
      const res = await fetch(`http://localhost:8009/chat/session/${sessionId}/history`);
      const data = await res.json();
      
      if (data.success) {
        setCurrentSessionId(sessionId);
        setMessages(data.messages || []);
        setError('');
      }
    } catch (err) {
      console.error('Error loading session:', err);
      setError('Failed to load session');
    }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    
    // Create session if none exists
    if (!currentSessionId) {
      await createNewSession();
      // After creating, the input will still be there, so we'll send it
      setTimeout(() => sendMessage(), 100);
      return;
    }

    const userMessage = { role: 'user', content: input, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError('');

    try {
      const res = await fetch('http://localhost:8009/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSessionId,
          message: input,
          options: {
            max_sources: 5,
            include_context: true
          }
        })
      });

      const data = await res.json();
      
      if (data.success) {
        setMessages((prev) => [...prev, {
          role: 'assistant',
          content: data.content,
          sources: data.sources || [],
          timestamp: data.timestamp,
          metadata: data.metadata || {}
        }]);
        
        // Refresh sessions to update titles
        await loadSessions();
      } else {
        throw new Error(data.error || 'Unknown error');
      }
    } catch (err) {
      console.error('Error sending message:', err);
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: '⚠️ Error: Could not get response. Please try again.',
        timestamp: new Date().toISOString()
      }]);
      setError('Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const deleteSession = async (sessionId, e) => {
    e.stopPropagation();
    
    if (!window.confirm('Are you sure you want to delete this chat?')) {
      return;
    }

    try {
      const res = await fetch(`http://localhost:8009/chat/session/${sessionId}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      
      if (data.success) {
        if (currentSessionId === sessionId) {
          setCurrentSessionId(null);
          setMessages([]);
        }
        await loadSessions();
      }
    } catch (err) {
      console.error('Error deleting session:', err);
      setError('Failed to delete session');
    }
  };

  return (
    <div className="chat-interface">
      {/* Sidebar with sessions */}
      <div className="chat-sidebar">
        <div className="sidebar-header">
          <h2>Knowledge Base Chat</h2>
          <button onClick={createNewSession} className="new-chat-btn">
            + New Chat
          </button>
        </div>
        
        <div className="sessions-list">
          {sessions.length === 0 ? (
            <div className="no-sessions">No chats yet. Start a new one!</div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.session_id}
                className={`session-item ${currentSessionId === session.session_id ? 'active' : ''}`}
                onClick={() => loadSession(session.session_id)}
              >
                <div className="session-title">{session.title}</div>
                <div className="session-footer">
                  <span className="session-time">
                    {new Date(session.updated_at).toLocaleDateString()}
                  </span>
                  <button
                    className="delete-session-btn"
                    onClick={(e) => deleteSession(session.session_id, e)}
                    title="Delete chat"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="sidebar-footer">
          <button onClick={() => setUploadModalOpen(true)} className="upload-docs-btn">
            📄 Upload Documents
          </button>
        </div>
      </div>

      {/* Main chat area */}
      <div className="chat-main">
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={() => setError('')}>×</button>
          </div>
        )}

        {!currentSessionId ? (
          <div className="chat-welcome">
            <h1>💬 Knowledge Base Chat</h1>
            <p>Ask questions about your uploaded documents</p>
            <p className="chat-subtitle">
              Your documents are indexed in the knowledge base. Start chatting to query them using natural language.
            </p>
            <button onClick={createNewSession} className="start-chat-btn">
              Start New Chat
            </button>
          </div>
        ) : (
          <>
            <div className="chat-messages">
              {messages.length === 0 && (
                <div className="empty-chat">
                  <p>👋 Hello! Ask me anything about your documents.</p>
                </div>
              )}

              {messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role}`}>
                  <div className="message-avatar">
                    {msg.role === 'user' ? '👤' : '🤖'}
                  </div>
                  <div className="message-body">
                    <div className="message-content">
                      {msg.content}
                    </div>
                    
                    {/* Show sources for assistant messages */}
                    {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                      <div className="message-sources">
                        <div className="sources-label">📚 Sources:</div>
                        <div className="sources-list">
                          {msg.sources.map((source, sidx) => (
                            <div key={sidx} className="source-item">
                              <div className="source-header">
                                <span className="source-doc">{source.document_name}</span>
                                <span className="source-page">Page {source.page}</span>
                              </div>
                              <div className="source-score">
                                Relevance: {(source.relevance_score * 100).toFixed(0)}%
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="message-time">
                      {new Date(msg.timestamp).toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </div>
                  </div>
                </div>
              ))}
              
              {loading && (
                <div className="message assistant">
                  <div className="message-avatar">🤖</div>
                  <div className="message-body">
                    <div className="message-content loading">
                      <span className="dot"></span>
                      <span className="dot"></span>
                      <span className="dot"></span>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="chat-input-container">
              <div className="chat-input-wrapper">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask a question about your documents..."
                  rows={1}
                  className="chat-input"
                  disabled={loading}
                />
                <button
                  onClick={sendMessage}
                  disabled={loading || !input.trim()}
                  className="send-btn"
                  title="Send message"
                >
                  {loading ? '⏳' : '📤'}
                </button>
              </div>
              <div className="input-hint">
                Press Enter to send, Shift+Enter for new line
              </div>
            </div>
          </>
        )}
      </div>

      {/* Upload Modal - placeholder for now */}
      {uploadModalOpen && (
        <div className="modal-backdrop" onClick={() => setUploadModalOpen(false)}>
          <div className="upload-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Upload Documents</h2>
              <button onClick={() => setUploadModalOpen(false)} className="close-btn">×</button>
            </div>
            <div className="modal-body">
              <p>Document upload functionality will use the existing PDF upload feature.</p>
              <p>For now, please use the Document Extraction page to upload PDFs.</p>
            </div>
            <div className="modal-footer">
              <button onClick={() => setUploadModalOpen(false)} className="btn-secondary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ChatInterface;
