import React from 'react';
import { Link, useLocation } from 'react-router-dom';

// Using a consistent icon library (lucide-react) for a professional look
import {
  LayoutDashboard,
  ScrollText,
  Users,
  Bot,
  MessageSquare, // Icon for KB Chat
  FileScan, // ✅ ADDED: Icon for Document Extraction
  CheckSquare,
  BarChart3,
  LogOut,
  MoreVertical,
} from 'lucide-react';

import safexpressLogo from '../assets/sfxLogo.png';
import userAvatar from '../assets/accountLogo.png'; // Assuming this is the user's avatar
import '../css/Sidebar.css';

// Navigation items are now more maintainable with component icons
const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
  { label: 'Audit Logs', icon: ScrollText, path: '/audit-logs' },
  { label: 'Accounts', icon: Users, path: '/accounts' },
  { label: 'AI Chat', icon: Bot, path: '/ai-chat' },
  { label: 'KB Chat', icon: MessageSquare, path: '/kb-chat' },
  { label: 'Task Approval', icon: CheckSquare, path: '/task-approval'},
  { label: 'Report & Analysis', icon: BarChart3, path: '/report-analysis' },
  { label: 'Document Extraction', icon: FileScan, path: '/document-extraction' },
];

// Sub-component for individual navigation items for cleaner code
const NavItem = ({ item, isActive }) => (
  <li>
    <Link to={item.path} className={`nav-item ${isActive ? 'active' : ''}`}>
      <item.icon className="nav-icon" size={20} strokeWidth={2} />
      <span className="nav-label">{item.label}</span>
      {item.notification && <span className="notification-dot" />}
    </Link>
  </li>
);

// Sub-component for the user profile section with hoverable logout dropdown
import { useState } from 'react';
const UserProfile = ({ user, onLogout }) => {
  const [showLogout, setShowLogout] = useState(false);
  return (
    <div className="user-profile">
      <img src={user.avatar} alt="User Avatar" className="user-avatar" />
      <div className="user-details">
        <span className="user-name">{user.name}</span>
        <span className="user-email">{user.email}</span>
      </div>
      <div
        className="more-menu-wrapper"
        onMouseEnter={() => setShowLogout(true)}
        onMouseLeave={() => setShowLogout(false)}
        style={{ position: 'relative' }}
      >
        <button className="logout-button" title="More options" tabIndex={0}>
          <MoreVertical size={20} />
        </button>
        {showLogout && (
          <div className="logout-dropdown logout-dropdown-up" style={{ position: 'absolute', right: 0, bottom: '110%', zIndex: 10 }}>
            <button className="logout-dropdown-btn" onClick={onLogout}>
              <LogOut size={16} style={{ marginRight: 6 }} /> Logout
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

function Sidebar() {
  // useLocation is more reliable for determining the active path
  const { pathname } = useLocation();

  // Dummy user data - in a real app, this would come from context or props
  const user = {
    name: 'Maria Clara',
    email: 'm.clara@example.com',
    avatar: userAvatar,
  };

  const handleLogout = () => {
    // Implement your logout logic here
    console.log('Logging out...');
    // e.g., navigate('/login');
  };

  return (
    <nav className="sidebar">
      <div className="sidebar-header">
        <img src={safexpressLogo} alt="Safexpress Logo" className="logo" />
      </div>

      <ul className="nav-list">
        {navItems.map((item) => (
          <NavItem
            key={item.label}
            item={item}
            isActive={pathname === item.path}
          />
        ))}
      </ul>

      {/* The UserProfile component is pushed to the bottom using flexbox `margin-top: auto` */}
      <UserProfile user={user} onLogout={handleLogout} />
    </nav>
  );
}

export default Sidebar;