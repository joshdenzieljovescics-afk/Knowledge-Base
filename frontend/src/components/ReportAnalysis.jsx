import React, { useState } from 'react';
import { FileText, Filter, Download, BrainCircuit, Link as LinkIcon, Search } from 'lucide-react';
import '../css/ReportAnalysis.css'; 

// Sample Data
const initialReports = [
  { 
    id: 'rep-001', 
    title: 'One Page Report of VFP 2025', 
    link: 'https://docs.google.com/spreadsheets/d/ASKJDKASJfasdfasf', 
    category: 'Financial',
    date: '2025-08-01'
  },
  { 
    id: 'rep-002', 
    title: 'Q2 User Engagement Metrics', 
    link: 'https://docs.google.com/spreadsheets/d/XCVBNSDGsdfgsdfg', 
    category: 'Marketing',
    date: '2025-07-28'
  },
  { 
    id: 'rep-003', 
    title: 'Monthly Churn and Retention Analysis', 
    link: 'https://docs.google.com/spreadsheets/d/HERHERHerhherher', 
    category: 'User Data',
    date: '2025-07-15'
  },
    { 
    id: 'rep-004', 
    title: 'Annual Performance Review Data', 
    link: 'https://docs.google.com/spreadsheets/d/QWEQWEqweqweqew', 
    category: 'Internal',
    date: '2025-07-05'
  },
];

function ReportAnalysis() {
  const [reports, setReports] = useState(initialReports);

  return (
    <div className="report-page">
      <div className="container">
        
        {/* Page Header */}
        <header className="page-header">
          <div>
            <h1 className="header-title">Report & Analysis</h1>
            <p className="header-subtitle">Access, review, and analyze organizational reports.</p>
          </div>
          <button className="action-button new-report-button">
            <FileText size={16} />
            <span>New Report</span>
          </button>
        </header>

        {/* Filter and Actions Bar */}
        <div className="filter-bar">
          <div className="search-container" style={{ position: 'relative' }}>
            <Search size={20} className="search-icon" style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', pointerEvents: 'none' }} />
            <input
              type="text"
              placeholder="Search by title, link, or category..."
              className="search-input"
              style={{ paddingLeft: '2.5rem' }}
            />
          </div>
          <div className="filter-actions">
            <button className="action-button filter-button">
              <Filter size={16} />
              <span>Filter</span>
            </button>
            <button className="action-button download-button">
              <Download size={16} />
              <span>Download All</span>
            </button>
          </div>
        </div>


        {/* Reports List */}
        <div className="reports-list">
          {reports.map(report => (
            <div key={report.id} className="report-card">
              <div className="report-card-icon">
                <FileText size={24} />
              </div>
              <div className="report-card-details">
                <h3 className="report-card-title">{report.title}</h3>
                <a href={report.link} target="_blank" rel="noopener noreferrer" className="report-card-link">
                  <LinkIcon size={14} />
                  <span>{report.link}</span>
                </a>
                 <div className="report-card-meta">
                    <span className="report-card-badge">{report.category}</span>
                    <span className="report-card-date">Date: {report.date}</span>
                </div>
              </div>
              <button className="action-button analysis-button">
                <BrainCircuit size={16} />
                <span>Perform Analysis</span>
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ReportAnalysis;