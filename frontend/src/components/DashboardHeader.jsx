import React from 'react';
import '../css/DashboardHeader.css';

function DashboardHeader({ userName, lastLogin }) {
    return (
        <header className="dashboard-header">
            <div>
                <h1 className="header-title">Development Dashboard</h1>
                <p className="header-subtitle">Welcome back, {userName}.</p>
            </div>
            <div className="header-info">
                Last Login: {lastLogin}
            </div>
        </header>
    );
}

export default DashboardHeader;