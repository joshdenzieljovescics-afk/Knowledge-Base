import React, { useState } from 'react';
import { Upload, Settings, Search } from 'lucide-react';
import '../css/AuditLogs.css';

const initialLogs = [
  { name: 'Juan Miguel Dela Cruz', email: 'juanmigueldelacruz@example.com', action: '1xxx', details: '1xxx', date: '2025-08-01', timestamp: '1xx:xx AM' },
  { name: 'Maria Clara Ibarra', email: 'mariaclaraibarra@example.com', action: '2xxx', details: '2xxx', date: '2025-08-01', timestamp: '2xx:xx AM' },
  { name: 'Ana Santos', email: 'anasantos@example.com', action: '3xxx', details: '3xxx', date: '2025-08-02', timestamp: '3xx:xx AM' },
  { name: 'Carlos Reyes', email: 'carlosreyes@example.com', action: '4xxx', details: '4xxx', date: '2025-08-02', timestamp: '4xx:xx AM' },
  { name: 'Liza Gomez', email: 'lizagomez@example.com', action: '5xxx', details: '5xxx', date: '2025-08-03', timestamp: '5xx:xx AM' },
  { name: 'Mark Lee', email: 'marklee@example.com', action: '6xxx', details: '6xxx', date: '2025-08-03', timestamp: '6xx:xx AM' },
  { name: 'Sofia Cruz', email: 'sofiacruz@example.com', action: '7xxx', details: '7xxx', date: '2025-08-04', timestamp: '7xx:xx AM' },
  { name: 'Miguel Ramos', email: 'miguelramos@example.com', action: '8xxx', details: '8xxx', date: '2025-08-04', timestamp: '8xx:xx AM' },
  { name: 'Paula Lim', email: 'paulalim@example.com', action: '9xxx', details: '9xxx', date: '2025-08-05', timestamp: '9xx:xx AM' },
  { name: 'Rico Tan', email: 'ricotan@example.com', action: '10xxx', details: '10xxx', date: '2025-08-05', timestamp: '10xx:xx AM' },
  { name: 'Grace Yu', email: 'graceyu@example.com', action: '11xxx', details: '11xxx', date: '2025-08-05', timestamp: '11xx:xx AM' },
  { name: 'Ben Torres', email: 'bentorres@example.com', action: '12xxx', details: '12xxx', date: '2025-08-05', timestamp: '12xx:xx AM' },
  { name: 'Kim dela Vega', email: 'kimdelavega@example.com', action: '13xxx', details: '13xxx', date: '2025-08-05', timestamp: '13xx:xx AM' },
];

const ActionButton = ({ icon: Icon, children, className = '', ...props }) => (
  <button className={`action-button ${className}`} {...props}>
    <Icon size={16} />
    <span>{children}</span>
  </button>
);

function AuditLogs() {
  const [logs] = useState(initialLogs);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredLogs = logs.filter(log =>
    log.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
    log.details.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="accounts-page">
      <div className="container">
        <header className="page-header">
          <div>
            <h1 className="header-title">Audit Logs</h1>
            <p className="header-subtitle">Track all system actions and changes.</p>
          </div>
          <div className="header-actions">
            <ActionButton icon={Upload} className="action-button-export">
              Export
            </ActionButton>
            <ActionButton icon={Settings} className="action-button-settings">
              Settings
            </ActionButton>
          </div>
        </header>

        <main className="content-card">
          <div className="card-header">
            <div className="search-container">
              <Search size={20} className="search-icon" style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', pointerEvents: 'none' }} />
              <input
                type="text"
                placeholder="Search by email, action, or details..."
                className="search-input"
                style={{ paddingLeft: '2.5rem' }}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          <div className="table-wrapper">
            <table className="accounts-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Action</th>
                  <th>Details</th>
                  <th>Date</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log, idx) => (
                  <tr key={idx}>
                    <td data-label="Name">
                      <div className="table-cell-primary">{log.name}</div>
                      <div className="table-cell-secondary">{log.email}</div>
                    </td>
                    <td data-label="Action">{log.action}</td>
                    <td data-label="Details">{log.details}</td>
                    <td data-label="Date">{log.date}</td>
                    <td data-label="Timestamp" className="table-cell-member-id">{log.timestamp}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <footer className="card-footer">
            <div>
              Showing <span className="font-medium">1</span> to <span className="font-medium">{filteredLogs.length}</span> of <span className="font-medium">{logs.length}</span> results
            </div>
            <div className="pagination">
              <button className="pagination-button" disabled>
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
              </button>
              <span className="pagination-text">Page 1 of 1</span>
              <button className="pagination-button" disabled>
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
              </button>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}

export default AuditLogs;