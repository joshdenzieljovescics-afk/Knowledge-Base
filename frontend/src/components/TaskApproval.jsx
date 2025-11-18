import React from 'react';
import '../css/TaskApproval.css'; 

function TaskApproval() {
  const pendingTasks = [
    {
      id: 1,
      title: 'Deploy New Homepage to Production',
      submittedBy: 'Maria Clara Ibarra',
      date: '2025-08-04',
    },
    {
      id: 2,
      title: 'Update User Authentication Logic',
      submittedBy: 'Juan Dela Cruz',
      date: '2025-08-03',
    },
    {
      id: 3,
      title: 'Refresh Staging Database from Backup',
      submittedBy: 'Ana Santos',
      date: '2025-08-02',
    },
  ];

  return (
    <div className="task-approval-page">
      <div className="container">

        <header className="page-header">
          <div>
            <h1 className="header-title">Task Approval</h1>
            <p className="header-subtitle">Review and act on pending tasks submitted by your team.</p>
          </div>
        </header>

        <main className="content-card">
          <div className="task-list">
            {pendingTasks.map((task) => (
              <div className="task-card" key={task.id}>
                <div className="card-header">
                  <h3 className="card-title">{task.title}</h3>
                  <span className="status pending">Pending</span>
                </div>
                <div className="card-body">
                  <p><strong>Submitted by:</strong> {task.submittedBy}</p>
                  <p><strong>Date Submitted:</strong> {task.date}</p>
                </div>
                <div className="card-footer">
                  <button className="btn btn-reject">Reject</button>
                  <button className="btn btn-approve">Approve</button>
                </div>
              </div>
            ))}
            {pendingTasks.length === 0 && (
                <div className="no-tasks-message">
                    There are no pending tasks at the moment.
                </div>
            )}
          </div>
        </main>

      </div>
    </div>
  );
}

export default TaskApproval;