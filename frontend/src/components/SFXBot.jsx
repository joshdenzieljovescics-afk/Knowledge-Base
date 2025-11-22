import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { 
  Send, 
  Sparkles, 
  User,
  Bot,
  X
} from "lucide-react";
import { ACCESS_TOKEN } from "../token";
import DeleteConfirmationModal from "./DeleteConfirmationModal";
import "../css/DynamicMappingChat.css";

const API_BASE_URL = "http://localhost:8009";

function SFXBot() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [threadToDelete, setThreadToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [tokenUsage, setTokenUsage] = useState({
    session_tokens: 0,
    session_cost: 0,
    total_tokens: 0,
    total_cost: 0
  });
  
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const lastFetchRef = useRef(0);
  const fetchTimeoutRef = useRef(null);
  const loadTokenTimeoutRef = useRef(null);

  const suggestions = [
    "What are the company policies on remote work?",
    "How do I submit a leave request?",
    "Explain the expense reimbursement process",
    "What documents do I need for onboarding?"
  ];

  // Fetch user sessions on mount
  useEffect(() => {
    fetchUserSessions();
  }, []);

  // Load token usage when active thread changes
  useEffect(() => {
    if (activeThreadId) {
      // Debounce token loading to avoid 429 errors when rapidly switching threads
      if (loadTokenTimeoutRef.current) {
        clearTimeout(loadTokenTimeoutRef.current);
      }
      loadTokenTimeoutRef.current = setTimeout(() => {
        loadTokenUsage();
      }, 500);
    }
    
    return () => {
      if (loadTokenTimeoutRef.current) {
        clearTimeout(loadTokenTimeoutRef.current);
      }
    };
  }, [activeThreadId]);

  const loadTokenUsage = async () => {
    if (!activeThreadId) return;
    
    try {
      const [sessionRes, userRes] = await Promise.all([
        fetch(`${API_BASE_URL}/chat/session/${activeThreadId}/tokens`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem(ACCESS_TOKEN)}`
          }
        }),
        fetch(`${API_BASE_URL}/chat/user/tokens`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem(ACCESS_TOKEN)}`
          }
        })
      ]);
      
      const sessionData = await sessionRes.json();
      const userData = await userRes.json();
      
      if (sessionData.success && userData.success) {
        setTokenUsage({
          session_tokens: sessionData.total_tokens || 0,
          session_cost: sessionData.total_cost_usd || 0,
          total_tokens: userData.total_tokens || 0,
          total_cost: userData.total_cost_usd || 0
        });
      }
    } catch (err) {
      console.error('Error loading token usage:', err);
    }
  };

  const fetchUserSessions = async () => {
    // Debounce: Don't fetch if called within last 2 seconds
    const now = Date.now();
    if (now - lastFetchRef.current < 2000) {
      console.log('Skipping fetchUserSessions - too soon after last fetch');
      return;
    }
    lastFetchRef.current = now;
    
    try {
      const response = await fetch(`${API_BASE_URL}/chat/sessions`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem(ACCESS_TOKEN)}`
        }
      });
      
      if (response.status === 429) {
        console.warn("Too many requests. Please wait before retrying.");
        return;
      }
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setThreads(data.sessions || []);
        }
      } else {
        console.error("Failed to fetch sessions:", response.status);
      }
    } catch (error) {
      console.error("Error fetching sessions:", error);
    }
  };

  const createNewThread = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat/session/new`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem(ACCESS_TOKEN)}`
        },
        body: JSON.stringify({
          title: `Chat ${threads.length + 1}`
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
    const newThread = {
            session_id: data.session_id,
            title: data.session?.title || `Chat ${threads.length + 1}`,
            created_at: data.session?.created_at || new Date().toISOString(),
            message_count: 0
    };
          setThreads(prev => [newThread, ...prev]);
          setActiveThreadId(data.session_id);
    setMessages([]);
        }
      }
    } catch (error) {
      console.error("Error creating thread:", error);
    }
  };

  const switchThread = async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat/session/${sessionId}/history`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem(ACCESS_TOKEN)}`
        }
      });

      if (response.status === 429) {
        console.warn("Too many requests when switching threads. Please wait a moment.");
        return;
      }

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setActiveThreadId(sessionId);
          setMessages(data.messages || []);
        }
      } else {
        console.error("Failed to switch thread:", response.status);
      }
    } catch (error) {
      console.error("Error switching thread:", error);
    }
  };

  const deleteThread = async (sessionId) => {
    setIsDeleting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/chat/session/${sessionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem(ACCESS_TOKEN)}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setThreads(prev => prev.filter(t => t.session_id !== sessionId));
          if (activeThreadId === sessionId) {
            setActiveThreadId(null);
            setMessages([]);
          }
          setDeleteModalOpen(false);
          setThreadToDelete(null);
        }
      } else {
        console.error("Failed to delete thread:", response.status);
      }
    } catch (error) {
      console.error("Error deleting thread:", error);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteClick = (e, thread) => {
    e.stopPropagation();
    setThreadToDelete(thread);
    setDeleteModalOpen(true);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
    }
  }, [input]);

  const handleSuggestionClick = (suggestion) => {
    setInput(suggestion);
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    // Create session if needed
    if (!activeThreadId) {
      await createNewThread();
      // Wait for session to be created
      await new Promise(resolve => setTimeout(resolve, 500));
    }

    if (!activeThreadId) {
      console.error("No active session");
      return;
    }

    const userMessage = {
      message_id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsStreaming(true);

    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage = {
      message_id: assistantMessageId,
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString()
    };
    setMessages((prev) => [...prev, assistantMessage]);

    try {
      const response = await fetch(`${API_BASE_URL}/chat/message`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem(ACCESS_TOKEN)}`,
        },
        body: JSON.stringify({
          session_id: activeThreadId,
          message: userMessage.content,
          options: {
            max_sources: 5,
            include_context: true
          }
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success) {
        // Update with full response
                setMessages((prev) =>
                  prev.map((msg) =>
            msg.message_id === assistantMessageId
              ? { 
                  ...msg, 
                  content: data.content,
                  sources: data.sources || [],
                  metadata: data.metadata || {}
                }
                      : msg
                  )
                );

        // Update thread list and reload token usage
        // Use setTimeout to debounce and avoid rate limiting
        if (fetchTimeoutRef.current) {
          clearTimeout(fetchTimeoutRef.current);
        }
        fetchTimeoutRef.current = setTimeout(() => {
          Promise.all([fetchUserSessions(), loadTokenUsage()]).catch(err => {
            console.error('Error reloading data:', err);
          });
        }, 1000);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.message_id === assistantMessageId
            ? {
                ...msg,
                content: "Sorry, I encountered an error. Please try again.",
                error: true,
              }
            : msg
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="dm-chat-page">
      <div className="dm-chat-container">
        <div className="dm-chat-header-row">
          <div>
            <h1 className="dm-chat-header-title">SFX Bot</h1>
            <div className="dm-chat-header-subtitle">
              AI-powered assistant for your queries
            </div>
          </div>
        </div>

        <div className="dm-chat-content">
          {/* Chat Threads Sidebar */}
          <div className="chat-threads-sidebar">
            <div className="threads-header">
              <h3>Chat Threads</h3>
              <button className="new-chat-btn" onClick={createNewThread}>
                <Sparkles size={16} />
                New Chat
              </button>
            </div>
            {activeThreadId && (
              <div className="token-stats">
                <div className="token-stat-row">
                  <span className="token-label">Session:</span>
                  <span className="token-value">{tokenUsage.session_tokens.toLocaleString()} tokens</span>
                  <span className="token-cost">${tokenUsage.session_cost.toFixed(4)}</span>
                </div>
                <div className="token-stat-row">
                  <span className="token-label">Total:</span>
                  <span className="token-value">{tokenUsage.total_tokens.toLocaleString()} tokens</span>
                  <span className="token-cost">${tokenUsage.total_cost.toFixed(2)}</span>
                </div>
              </div>
            )}
            <div className="threads-list">
              {threads.length === 0 ? (
                <div className="threads-empty">
                  No chat threads yet
                </div>
              ) : (
                threads.map((thread) => (
                  <div
                    key={thread.session_id}
                    className={`thread-item ${activeThreadId === thread.session_id ? 'active' : ''}`}
                    onClick={() => switchThread(thread.session_id)}
                  >
                    <div className="thread-info">
                      <div className="thread-title">{thread.title}</div>
                      <div className="thread-date">
                        {new Date(thread.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <button
                      className="thread-delete-btn"
                      onClick={(e) => handleDeleteClick(e, thread)}
                    >
                      <X size={16} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Chat Area */}
          <main className="chat-main">
            <div className="chat-messages">
              {messages.length === 0 ? (
                <div className="chat-welcome">
                  <div className="welcome-icon">
                    <Bot size={64} />
                  </div>
                  <h2>How can I help you find information?</h2>
                  <p>Ask me about company policies, procedures, or documentation</p>

                  <div className="chat-suggestions">
                    {suggestions.map((suggestion, i) => (
                      <button
                        key={i}
                        onClick={() => handleSuggestionClick(suggestion)}
                        className="chat-suggestion"
                      >
                        <span className="suggestion-icon">💡</span>
                        <span>{suggestion}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <>
                  {messages.map((msg) => (
                    <div
                      key={msg.message_id}
                      className={`message ${msg.role === "user" ? "user" : "assistant"}`}
                    >
                      <div className="message-avatar">
                        {msg.role === "user" ? (
                          <User size={20} />
                        ) : (
                          <Bot size={20} />
                        )}
                      </div>
                      <div className="message-content">
                        <div className="message-text">{msg.content}</div>
                        {msg.sources && msg.sources.length > 0 && (
                          <div className="message-sources">
                            <strong>Sources:</strong>
                            <ul>
                              {msg.sources.map((source, idx) => (
                                <li key={idx}>
                                  <div className="source-header">
                                    <strong>{source.document_name}</strong> (Page {source.page})
                                    {source.relevance_score && (
                                      <span style={{ marginLeft: '8px', color: '#666', fontSize: '0.9em' }}>
                                        - Relevance: {(source.relevance_score * 100).toFixed(0)}%
                                      </span>
                                    )}
                                  </div>
                                  {source.chunk_type && source.chunk_type !== 'text' && source.chunk_type !== 'paragraph' && (
                                    <div className="source-type">
                                      {source.chunk_type === 'heading' && '📌'}
                                      {source.chunk_type === 'list' && '📋'}
                                      {source.chunk_type === 'table' && '📊'}
                                      {source.chunk_type === 'image' && '🖼️'}
                                      {!['heading', 'list', 'table', 'image'].includes(source.chunk_type) && '📄'}
                                      {' '}Type: {source.chunk_type}
                                    </div>
                                  )}
                                  {source.section && (
                                    <div className="source-section">
                                      📑 Section: {source.section}
                                    </div>
                                  )}
                                  {source.context && (
                                    <div className="source-context">
                                      ℹ️ {source.context}
                                    </div>
                                  )}
                                  {source.tags && source.tags.length > 0 && (
                                    <div className="source-tags">
                                      🏷️ {source.tags.join(', ')}
                                    </div>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            <div className="chat-input-container">
              <form onSubmit={handleSubmit} className="chat-form">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Ask a question..."
                  className="chat-textarea"
                  rows={1}
                  disabled={isStreaming}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isStreaming}
                  className="chat-send-btn"
                >
                  <Send size={20} />
                </button>
              </form>
            </div>
          </main>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmationModal
        isOpen={deleteModalOpen}
        onClose={() => {
          if (!isDeleting) {
            setDeleteModalOpen(false);
            setThreadToDelete(null);
          }
        }}
        onConfirm={() => threadToDelete && deleteThread(threadToDelete.session_id)}
        documentName={threadToDelete ? `"${threadToDelete.title}"` : ''}
        isDeleting={isDeleting}
      />
    </div>
  );
}

export default SFXBot;
