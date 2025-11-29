import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { User, Mail, Shield, IdCard, Save, X, ArrowLeft } from 'lucide-react';
import '../css/EditAccount.css';

function EditAccount() {
  const navigate = useNavigate();
  const location = useLocation();
  const accountData = location.state?.account;

  const [formData, setFormData] = useState({
    id: '',
    name: '',
    email: '',
    role: 'User',
    status: 'Active',
    memberId: ''
  });

  const [errors, setErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (accountData) {
      setFormData(accountData);
    } else {
      // If no account data, redirect back to accounts page
      navigate('/accounts');
    }
  }, [accountData, navigate]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email format';
    }

    if (!formData.memberId.trim()) {
      newErrors.memberId = 'Member ID is required';
    } else if (!/^\d{12}$/.test(formData.memberId)) {
      newErrors.memberId = 'Member ID must be exactly 12 digits';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field, value) => {
    setFormData({
      ...formData,
      [field]: value
    });
    
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors({
        ...errors,
        [field]: ''
      });
    }
  };

  const handleSave = async () => {
    if (!validateForm()) {
      return;
    }

    setIsSaving(true);

    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Navigate back to accounts page with updated data
      navigate('/accounts', { 
        state: { 
          updatedAccount: formData,
          message: 'Account updated successfully!'
        } 
      });
    } catch (error) {
      console.error('Error saving account:', error);
      alert('Failed to save account. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    if (window.confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
      navigate('/accounts');
    }
  };

  return (
    <div className="edit-account-page">
      <div className="edit-account-container">
        {/* Header */}
        <div className="edit-account-header">
          <div className="header-left">
            <button className="back-button" onClick={() => navigate('/accounts')}>
              <ArrowLeft size={20} />
            </button>
            <div>
              <h1 className="edit-account-title">Edit Account</h1>
              <p className="edit-account-subtitle">Update account information and settings</p>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="edit-account-content">
          {/* Account Information Card */}
          <div className="edit-account-card">
            <div className="edit-account-card-header">
              <h3 className="card-title">Account Information</h3>
              <span className={`status-indicator ${formData.status.toLowerCase()}`}>
                {formData.status}
              </span>
            </div>
            <div className="edit-account-card-body">
              <div className="form-grid">
                {/* Name */}
                <div className="form-group">
                  <label className="form-label">
                    <User size={18} />
                    <span>Full Name</span>
                  </label>
                  <input
                    type="text"
                    className={`form-input ${errors.name ? 'error' : ''}`}
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    placeholder="Enter full name"
                  />
                  {errors.name && <span className="error-message">{errors.name}</span>}
                </div>

                {/* Email */}
                <div className="form-group">
                  <label className="form-label">
                    <Mail size={18} />
                    <span>Email Address</span>
                  </label>
                  <input
                    type="email"
                    className={`form-input ${errors.email ? 'error' : ''}`}
                    value={formData.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    placeholder="Enter email address"
                  />
                  {errors.email && <span className="error-message">{errors.email}</span>}
                </div>

                {/* Member ID */}
                <div className="form-group">
                  <label className="form-label">
                    <IdCard size={18} />
                    <span>Member ID</span>
                  </label>
                  <input
                    type="text"
                    className={`form-input ${errors.memberId ? 'error' : ''}`}
                    value={formData.memberId}
                    onChange={(e) => handleInputChange('memberId', e.target.value)}
                    placeholder="Enter 12-digit member ID"
                    maxLength={12}
                  />
                  {errors.memberId && <span className="error-message">{errors.memberId}</span>}
                </div>

                {/* Role */}
                <div className="form-group">
                  <label className="form-label">
                    <Shield size={18} />
                    <span>Role</span>
                  </label>
                  <select
                    className="form-select"
                    value={formData.role}
                    onChange={(e) => handleInputChange('role', e.target.value)}
                  >
                    <option value="User">User</option>
                    <option value="Admin">Admin</option>
                  </select>
                </div>

                {/* Status */}
                <div className="form-group">
                  <label className="form-label">
                    <Shield size={18} />
                    <span>Account Status</span>
                  </label>
                  <select
                    className="form-select"
                    value={formData.status}
                    onChange={(e) => handleInputChange('status', e.target.value)}
                  >
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                  </select>
                </div>

                {/* Account ID (Read-only) */}
                <div className="form-group">
                  <label className="form-label">
                    <IdCard size={18} />
                    <span>Account ID</span>
                  </label>
                  <input
                    type="text"
                    className="form-input readonly"
                    value={formData.id}
                    readOnly
                    disabled
                  />
                  <span className="helper-text">Account ID cannot be modified</span>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button 
              className="cancel-button" 
              onClick={handleCancel}
              disabled={isSaving}
            >
              <X size={20} />
              <span>Cancel</span>
            </button>
            <button 
              className="save-button" 
              onClick={handleSave}
              disabled={isSaving}
            >
              <Save size={20} />
              <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
            </button>
          </div>

          {/* Information Notice */}
          <div className="info-notice">
            <Shield size={24} className="notice-icon" />
            <div>
              <h4>Important Information</h4>
              <ul>
                <li>Changes to the account role will take effect immediately</li>
                <li>Email changes may require the user to verify their new email address</li>
                <li>Account ID is permanent and cannot be modified</li>
                <li>Member ID must be exactly 12 digits</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default EditAccount;
