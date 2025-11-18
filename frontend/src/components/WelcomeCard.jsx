import React from 'react';

function WelcomeCard({ userName, logo }) {
    return (
        <div className="card welcome-card">
            <div className="welcome-content">
                <div className="welcome-text-group">
                    <div>
                        <h2 className="welcome-title">Welcome</h2>
                        <p className="welcome-name">{userName}</p>
                    </div>
                </div>
                <p className="welcome-description">
                    Here's your personal space to manage projects, track progress, and collaborate effectively. Let's get started!
                </p>
            </div>
            <img src={logo} alt="SFX Logo" className="welcome-logo" />
        </div>
    );
}

export default WelcomeCard;