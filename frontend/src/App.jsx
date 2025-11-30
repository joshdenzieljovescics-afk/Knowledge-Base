import React, { useState, useEffect } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { KeepAlive, AliveScope } from "react-activation";
import { GoogleOAuthProvider } from "@react-oauth/google";
import Sidebar from "./components/Sidebar";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";
import AuditLogs from "./components/AuditLogs";
import UserActivityDetails from "./components/UserActivityDetails.jsx";
import Accounts from "./components/Accounts.jsx";
import AIChatNew from "./components/AIChatNew.jsx";
import TaskApproval from "./components/TaskApproval";
import DocumentExtraction from "./components/DocumentExtraction.jsx";
import DynamicMapping from "./components/DynamicMapping.jsx";
import SFXBot from "./components/SFXBot.jsx";
import AnalysisReport from "./components/AnalysisReport.jsx";
import ABCAnalysisPage from "./components/ABCAnalysisPage.jsx";
import ABCAnalysisHistory from "./components/ABCAnalysisHistory.jsx";
import OnePageReportPage from "./components/OnePageReportPage.jsx";
import OPRHistory from "./components/OPRHistory.jsx";
import WorkloadAnalysisPage from "./components/WorkloadAnalysisPage.jsx";
import ProfilePage from "./components/ProfilePage.jsx";
import EditAccount from "./components/EditAccount.jsx";
import ErrorModal from "./components/ErrorModal.jsx";
import { ErrorProvider, useError } from "./utils/ErrorContext.jsx";
import "./css/App.css";
import { ACCESS_TOKEN, clearDocumentStorage } from "./token";
import { isTokenExpired } from "./utils/tokenManager";

const GOOGLE_CLIENT_ID =
  "1005946026213-f25l34dtrk4us58832ek9ap5v62vrj5f.apps.googleusercontent.com";

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    const token = localStorage.getItem(ACCESS_TOKEN);
    return !!token;
  });
  const [error, setError] = useState(null);
  const [showErrorModal, setShowErrorModal] = useState(false);

  // Global error handler function
  const handleError = React.useCallback((errorData) => {
    setError(errorData);
    setShowErrorModal(true);
  }, []);

  const handleLogin = React.useCallback(() => {
    const token = localStorage.getItem(ACCESS_TOKEN);
    if (token) {
      setIsLoggedIn(true);
    }
  }, []);

  const handleLogout = React.useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN);
    localStorage.removeItem("user");
    localStorage.removeItem("refresh");
    clearDocumentStorage(); // Clear any parsed document data
    setIsLoggedIn(false);
  }, []);

  const toggleSidebar = React.useCallback(() => {
    setIsSidebarOpen((prev) => !prev);
  }, []);

  // Set up periodic token check only once on mount
  useEffect(() => {
    // Check every 5 minutes
    const interval = setInterval(() => {
      const token = localStorage.getItem(ACCESS_TOKEN);
      
      if (!token) {
        setIsLoggedIn(false);
      } else {
        try {
          if (isTokenExpired()) {
            handleLogout();
          }
        } catch (error) {
          console.error("Error checking token expiry:", error);
        }
      }
    }, 5 * 60 * 1000); // 5 minutes

    return () => clearInterval(interval);
  }, []); // Empty dependency array - run only once on mount

  // Global error handler for uncaught errors
  useEffect(() => {
    const handleGlobalError = (event) => {
      console.error('Global error caught:', event.error);
      handleError({
        title: 'Application Error',
        message: event.error?.message || 'An unexpected error occurred',
        severity: 'critical',
        details: event.error?.stack,
        timestamp: new Date().toISOString(),
      });
    };

    const handleUnhandledRejection = (event) => {
      console.error('Unhandled promise rejection:', event.reason);
      handleError({
        title: 'Promise Rejection',
        message: event.reason?.message || 'An async operation failed',
        severity: 'warning',
        details: event.reason?.stack || String(event.reason),
        timestamp: new Date().toISOString(),
      });
    };

    window.addEventListener('error', handleGlobalError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleGlobalError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [handleError]);

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <ErrorProvider>
        <Router>
          {!isLoggedIn ? (
          <Routes>
            <Route path="/login" element={<Login onLogin={handleLogin} />} />
            <Route
              path="/login/callback"
              element={<Login onLogin={handleLogin} />}
            />
            <Route path="*" element={<Navigate to="/login" />} />
          </Routes>
        ) : (
          <div className="app-container">
            <Sidebar
              isOpen={isSidebarOpen}
              toggleSidebar={toggleSidebar}
              onLogout={handleLogout}
            />
            <div className="main-content">
              <AliveScope>
                <Routes>
                  <Route
                    path="/dashboard"
                    element={
                      <KeepAlive id="dashboard">
                        <Dashboard />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/audit-logs"
                    element={
                      <KeepAlive id="audit-logs">
                        <AuditLogs />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/audit-logs/user/:userEmail"
                    element={
                      <KeepAlive id="user-activity">
                        <UserActivityDetails />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/accounts"
                    element={
                      <KeepAlive id="accounts">
                        <Accounts />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/ai-chat-new"
                    element={
                      <KeepAlive id="ai-chat-new">
                        <AIChatNew />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/task-approval"
                    element={
                      <KeepAlive id="task-approval">
                        <TaskApproval />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/document-extraction"
                    element={
                      <KeepAlive id="document-extraction">
                        <DocumentExtraction />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/dynamic-mapping"
                    element={
                      <KeepAlive id="dynamic-mapping">
                        <DynamicMapping />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/sfx-bot"
                    element={
                      <KeepAlive id="sfx-bot">
                        <SFXBot />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/analysis-report"
                    element={
                      <KeepAlive id="analysis-report">
                        <AnalysisReport />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/analysis-abc"
                    element={
                      <KeepAlive id="analysis-abc">
                        <ABCAnalysisPage />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/analysis-abc-history"
                    element={
                      <KeepAlive id="analysis-abc-history">
                        <ABCAnalysisHistory />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/analysis-one-page"
                    element={
                      <KeepAlive id="analysis-one-page">
                        <OnePageReportPage />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/opr-history"
                    element={
                      <KeepAlive id="opr-history">
                        <OPRHistory />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/analysis-workload"
                    element={
                      <KeepAlive id="analysis-workload">
                        <WorkloadAnalysisPage />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/profile"
                    element={
                      <KeepAlive id="profile">
                        <ProfilePage />
                      </KeepAlive>
                    }
                  />
                  <Route
                    path="/edit-account"
                    element={
                      <KeepAlive id="edit-account">
                        <EditAccount />
                      </KeepAlive>
                    }
                  />
                  <Route path="*" element={<Navigate to="/dashboard" />} />
                </Routes>
              </AliveScope>
            </div>
          </div>
        )}
        
          {/* Global Error Modal */}
          <ErrorModal 
            isOpen={showErrorModal}
            onClose={() => {
              setShowErrorModal(false);
              setError(null);
            }}
            error={error}
          />
        </Router>
      </ErrorProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
