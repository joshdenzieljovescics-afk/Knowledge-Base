import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Login from './components/Login'; // Make sure the path to Login.jsx is correct
import Dashboard from './components/Dashboard';
import AuditLogs from './components/AuditLogs';
import Accounts from './components/Accounts.jsx';
import AIChat from './components/AIChat';
import ChatInterface from './components/ChatInterface';
import TaskApproval from './components/TaskApproval';
import ReportAnalysis from './components/ReportAnalysis.jsx';
import DocumentExtraction from './components/DocumentExtraction.jsx';
import './css/App.css';

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false); // 1. Add login state

  // 2. Create a function to handle successful login
  const handleLogin = () => {
    setIsLoggedIn(true);
  };

  return (
    <Router>
      {/* 3. Conditionally render content based on login status */}
      {!isLoggedIn ? (
        // If not logged in, show the Login component
        <Routes>
          <Route path="/login" element={<Login onLogin={handleLogin} />} />
          {/* Redirect any other path to /login */}
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      ) : (
        // If logged in, show the main app layout
        <div className="app-container">
          <Sidebar isOpen={isSidebarOpen} toggleSidebar={() => setIsSidebarOpen(prev => !prev)} />
          <div className="main-content">
            <Routes>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/audit-logs" element={<AuditLogs />} />
              <Route path="/accounts" element={<Accounts />} />
              <Route path="/ai-chat" element={<AIChat />} />
              <Route path="/kb-chat" element={<ChatInterface />} />
              <Route path="/task-approval" element={<TaskApproval />} />
              <Route path="/report-analysis" element={<ReportAnalysis />} />
              <Route path="/document-extraction" element={<DocumentExtraction />} />
              {/* Redirect from root path to dashboard after login */}
              <Route path="*" element={<Navigate to="/dashboard" />} />
            </Routes>
          </div>
        </div>
      )}
    </Router>
  );
}

export default App;




