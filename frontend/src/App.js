// App.js
import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./AuthContext";
import PDFProcessor from "./PDFProcessor";
import ReviewQueue from "./ReviewQueue";
import Login from "./Login";
import Register from "./Register";
import "./App.css";

// User menu component
const UserMenu = () => {
  const { user, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  if (!user) return null;

  const userInitial = user.username.charAt(0).toUpperCase();

  return (
    <div className="user-menu">
      <button
        className="user-menu-button"
        onClick={() => setDropdownOpen(!dropdownOpen)}
      >
        <div className="user-avatar">{userInitial}</div>
        <div className="user-info">
          <span className="user-name">{user.username}</span>
          <span className="user-role">{user.role}</span>
        </div>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {dropdownOpen && (
        <>
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 999
            }}
            onClick={() => setDropdownOpen(false)}
          />
          <div className="user-dropdown">
            <button className="user-dropdown-item">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              Profile
            </button>
            <button className="user-dropdown-item logout" onClick={logout}>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              Logout
            </button>
          </div>
        </>
      )}
    </div>
  );
};

// Main app component (protected content)
const MainApp = () => {
  const [activeTab, setActiveTab] = useState('processor');
  const [reviewQueueCount, setReviewQueueCount] = useState(0);

  // Fetch review queue count for badge
  const fetchReviewQueueCount = async () => {
    try {
      const response = await fetch('http://localhost:8000/review-queue/stats');
      if (response.ok) {
        const data = await response.json();
        setReviewQueueCount(data.total_needs_review || 0);
      }
    } catch (error) {
      console.error('Error fetching review queue count:', error);
    }
  };

  // Fetch count on mount and every 30 seconds
  useEffect(() => {
    fetchReviewQueueCount();
    const interval = setInterval(fetchReviewQueueCount, 30000);
    return () => clearInterval(interval);
  }, []);

  // Refresh count when switching to processor tab
  useEffect(() => {
    if (activeTab === 'processor') {
      const timeout = setTimeout(fetchReviewQueueCount, 2000);
      return () => clearTimeout(timeout);
    }
  }, [activeTab]);

  return (
    <div className="App">
      <div className="app-header">
        <div className="app-header-content">
          <h1>Categorization Bot</h1>
          <UserMenu />
        </div>
        <nav className="app-nav">
          <button
            className={`nav-tab ${activeTab === 'processor' ? 'active' : ''}`}
            onClick={() => setActiveTab('processor')}
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            Document Processing
          </button>
          <button
            className={`nav-tab ${activeTab === 'review' ? 'active' : ''}`}
            onClick={() => setActiveTab('review')}
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
            Review Queue
            {reviewQueueCount > 0 && (
              <span className="review-badge">{reviewQueueCount}</span>
            )}
          </button>
        </nav>
      </div>

      <div className="app-content">
        {activeTab === 'processor' ? <PDFProcessor /> : <ReviewQueue />}
      </div>
    </div>
  );
};

// Auth wrapper component
const AppContent = () => {
  const { isAuthenticated, loading } = useAuth();
  const [authView, setAuthView] = useState('login'); // 'login' or 'register'

  if (loading) {
    return (
      <div className="auth-container">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return authView === 'login' ? (
      <Login onSwitchToRegister={() => setAuthView('register')} />
    ) : (
      <Register onSwitchToLogin={() => setAuthView('login')} />
    );
  }

  return <MainApp />;
};

// Root App with AuthProvider
function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
