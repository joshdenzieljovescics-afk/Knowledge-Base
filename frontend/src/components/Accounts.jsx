import React, { useState } from 'react';
import { Search, Upload, Settings, Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import '../css/Accounts.css'; 

const initialAccounts = [
  { id: 'acc-001', name: 'Maria Clara Ibarra', email: 'mariaclara.ibarra@example.com', role: 'User', status: 'Active', memberId: '123456789012' },
  { id: 'acc-002', name: 'Juan Dela Cruz', email: 'juan.delacruz@example.com', role: 'Admin', status: 'Inactive', memberId: '987654321098' },
  { id: 'acc-003', name: 'Ana Santos', email: 'ana.santos@example.com', role: 'User', status: 'Active', memberId: '111222333444' },
  { id: 'acc-004', name: 'Carlos Reyes', email: 'carlos.reyes@example.com', role: 'User', status: 'Active', memberId: '555666777888' },
  { id: 'acc-005', name: 'Liza Gomez', email: 'liza.gomez@example.com', role: 'Admin', status: 'Active', memberId: '999888777666' },
  { id: 'acc-006', name: 'Mark Lee', email: 'mark.lee@example.com', role: 'User', status: 'Inactive', memberId: '444333222111' },
  { id: 'acc-007', name: 'Sofia Cruz', email: 'sofia.cruz@example.com', role: 'User', status: 'Active', memberId: '222333444555' },
  { id: 'acc-008', name: 'Miguel Ramos', email: 'miguel.ramos@example.com', role: 'Admin', status: 'Active', memberId: '333444555666' },
  { id: 'acc-009', name: 'Paula Lim', email: 'paula.lim@example.com', role: 'User', status: 'Inactive', memberId: '666555444333' },
  { id: 'acc-010', name: 'Rico Tan', email: 'rico.tan@example.com', role: 'User', status: 'Active', memberId: '777888999000' },
  { id: 'acc-011', name: 'Grace Yu', email: 'grace.yu@example.com', role: 'Admin', status: 'Active', memberId: '888999000111' },
  { id: 'acc-012', name: 'Ben Torres', email: 'ben.torres@example.com', role: 'User', status: 'Inactive', memberId: '999000111222' },
  { id: 'acc-013', name: 'Kim dela Vega', email: 'kim.delavega@example.com', role: 'User', status: 'Active', memberId: '000111222333' },
];

const ActionButton = ({ icon: Icon, children, className = '', ...props }) => (
  <button className={`action-button ${className}`} {...props}>
    <Icon size={16} />
    <span>{children}</span>
  </button>
);

const StatusBadge = ({ status }) => {
  const statusClass = status === 'Active' ? 'status-badge-active' : 'status-badge-inactive';
  return <span className={`status-badge ${statusClass}`}>{status}</span>;
};


function Accounts() {
  const [accounts, setAccounts] = useState(initialAccounts);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredAccounts = accounts.filter(account =>
    account.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    account.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    account.role.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="accounts-page">
      <div className="container">
        
        <header className="page-header">
          <div>
            <h1 className="header-title">Accounts</h1>
            <p className="header-subtitle">Manage all user accounts in the system.</p>
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
                placeholder="Search by name, email, or role..."
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
                  <th>Status</th>
                  <th>Role</th>
                  <th>Member ID</th>
                  <th className='actions'>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAccounts.length === 0 ? (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', color: '#64748b', fontStyle: 'italic', padding: '2rem' }}>
                      No Account/s found.
                    </td>
                  </tr>
                ) : (
                  filteredAccounts.map((account) => (
                    <tr key={account.id}>
                      <td data-label="Name">
                        <div className="table-cell-primary">{account.name}</div>
                        <div className="table-cell-secondary">{account.email}</div>
                      </td>
                      <td data-label="Status">
                        <StatusBadge status={account.status} />
                      </td>
                      <td data-label="Role" className="table-cell-role">{account.role}</td>
                      <td data-label="Member ID" className="table-cell-member-id">{account.memberId}</td>
                      <td data-label="Actions" className="text-center">
                        <div className="table-actions">
                          <button className="action-icon-button" aria-label="Edit">
                            <Pencil size={16} />
                          </button>
                          <button className="action-icon-button action-icon-delete" aria-label="Delete">
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          
          <footer className="card-footer">
            <div>
              Showing <span className="font-medium">1</span> to <span className="font-medium">{filteredAccounts.length}</span> of <span className="font-medium">{accounts.length}</span> results
            </div>
            <div className="pagination">
              <button className="pagination-button" disabled>
                <ChevronLeft size={16} />
              </button>
              <span className="pagination-text">Page 1 of 1</span>
              <button className="pagination-button" disabled>
                <ChevronRight size={16} />
              </button>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}

export default Accounts;