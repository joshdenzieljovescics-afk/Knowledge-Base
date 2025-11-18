import React, { useState } from 'react';
import { FiUsers, FiCheckSquare, FiFileText, FiTag, FiUploadCloud, FiX, FiInbox } from 'react-icons/fi';

// Component Imports
import DashboardHeader from '../components/DashboardHeader';
import WelcomeCard from '../components/WelcomeCard';
import StatCard from '../components/StatCard';
import ActionCard from '../components/ActionCard';
import UploadModal from '../components/UploadModal';

import sfxLogo from '../assets/sfxLogo.png';
import handImg from '../assets/Hand.png';
import '../css/Dashboard1.css';

function Dashboard() {
    const [isUploadModalOpen, setUploadModalOpen] = useState(false);
    const [isFilesModalOpen, setFilesModalOpen] = useState(false);

    const userInfo = {
        name: 'Maria Clara',
        lastLogin: 'July 17, 5:09 PM',
    };

    const uploadedFiles = [
        { name: 'Project_Plan_v2.pdf', type: 'pdf' },
        { name: 'UI_Mockups_Final.png', type: 'image' },
        { name: 'Sprint-Retrospective-Notes.docx', type: 'doc' },
    ];

    const fileTasks = [
        'Review project brief',
        'Finalize UI/UX mockups',
        'Submit weekly progress report'
    ];

    const metadataTasks = [
        'Tag all new assets from Q2',
        'Update legacy metadata schema',
        'Organize files by project phase'
    ];

    return (
      <div className="dashboard-page">
        <div className="dashboard-container">
            <DashboardHeader userName={userInfo.name} lastLogin={userInfo.lastLogin} />
            
            <main className="dashboard-grid">
                <WelcomeCard 
                    userName={userInfo.name} 
                    logo={sfxLogo} 
                />

                <div className="stat-cards-group">
                    <StatCard 
                        icon={<FiUsers size={28} className="text-blue-500" />}
                        title="Total Accounts"
                        value="200"
                        description="Active user accounts across all platforms."
                    />
                    <StatCard 
                        icon={<FiCheckSquare size={28} className="text-green-500" />}
                        title="Tasks Approved"
                        value="60"
                        description="Tasks completed and approved this cycle."
                    />
                </div>

                <ActionCard
                    icon={<FiFileText size={24} />}
                    title="File Management"
                    subtitle="Central Repository"
                    description="Upload, organize, and manage all your project-related documents."
                    tasks={fileTasks}
                    buttonText="Upload File"
                    onButtonClick={() => setUploadModalOpen(true)}
                />

                <ActionCard
                    icon={<FiTag size={24} />}
                    title="Metadata Tagging"
                    subtitle="Content Organization"
                    description="Efficiently tag and categorize files for improved search and retrieval."
                    tasks={metadataTasks}
                    buttonText="Add New Tags"
                    onButtonClick={() => alert('Navigate to tagging page')}
                />
            </main>

            {isUploadModalOpen && (
                <UploadModal 
                    onClose={() => setUploadModalOpen(false)}
                    onShowFiles={() => {
                        setUploadModalOpen(false);
                        setFilesModalOpen(true);
                    }}
                />
            )}
            
            {isFilesModalOpen && (
                 <div className="modal-overlay" onClick={() => setFilesModalOpen(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3 className="modal-title">Uploaded Files</h3>
                            <button onClick={() => setFilesModalOpen(false)} className="modal-close-btn">
                                <FiX size={24} />
                            </button>
                        </div>
                        <ul className="files-list">
                            {uploadedFiles.map((file, index) => (
                                <li key={index} className="file-item">{file.name}</li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}

        </div>
        </div>
    );
}

export default Dashboard;