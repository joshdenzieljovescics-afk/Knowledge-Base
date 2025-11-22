import React, { useState } from 'react';
import '../css/Login.css'; // Import your CSS for styling
import truckImage from '../assets/truckImage.png';

const API_BASE_URL = 'http://localhost:8009';
const ACCESS_TOKEN = 'access_token';

const Login = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Store the access token in localStorage
        localStorage.setItem(ACCESS_TOKEN, data.access_token);
        console.log('Login successful, token stored');
        onLogin();
      } else {
        setError(data.error || 'Login failed');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  return (
    // MODIFIED: Changed fragment to a div wrapper for centering
    <div className="login-page-wrapper"> 
      <div className="login-container">


        <div className="form-section">
          <div className="form-content">
            <div className="logo-container">
              <div className="logo-placeholder">
                <span>5X</span>
              </div>
            </div>
            <h2 className="title">Login</h2>
            {error && <div className="error-message">{error}</div>}
            <form onSubmit={handleSubmit} className="login-form">
              <div className="input-group">
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className="input-group">
                <label htmlFor="password">Password</label>
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              <button type="submit" className="login-button" disabled={loading}>
                {loading ? 'Logging in...' : 'Login'}
              </button>
            </form>
            <div className="divider">
              <span className="divider-text">or</span>
            </div>
            <button className="google-login-button">
              <div className="google-icon-container">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24" className="google-icon">
                  <path d="M23.992 12.27c0-.783-.069-1.535-.194-2.273h-11.792v4.298h6.634c-.287 1.492-1.12 2.766-2.316 3.63v2.81h3.626c2.128-1.954 3.356-4.833 3.356-8.465z" fill="#4285F4"/>
                  <path d="M11.996 23.996c3.24 0 5.94-.88 7.92-2.392l-3.626-2.81c-1.004.675-2.28 1.077-4.294 1.077-3.31 0-6.12-2.24-7.12-5.228H1.28v2.905c2.012 3.987 6.13 6.748 10.716 6.748z" fill="#34A853"/>
                  <path d="M4.876 14.238c-.24-.67-.376-1.38-.376-2.238 0-.858.136-1.568.376-2.238V6.895H1.28c-.808 1.61-.92 3.424-.92 5.105 0 1.68.112 3.496.92 5.105L4.876 14.238z" fill="#FBBC05"/>
                  <path d="M11.996 4.772c1.776 0 3.354.618 4.606 1.798l3.226-3.136C17.932.924 15.23.004 11.996.004c-4.586 0-8.704 2.76-10.716 6.747l3.596 2.755c.996-2.988 3.804-5.228 7.12-5.228z" fill="#EA4335"/>
                </svg>
              </div>
              <span>Login account with Google</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;