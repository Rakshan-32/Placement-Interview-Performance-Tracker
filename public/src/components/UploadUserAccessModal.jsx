function UploadUserAccessModal({ isOpen, onClose, onAccessGranted }) {
    if (!isOpen) return null;

    // Active mode tab: 'single' or 'bulk'
    const [grantMode, setGrantMode] = React.useState('single');

    // Single Student Form State
    const [singleGmail, setSingleGmail] = React.useState('');
    const [singleRole, setSingleRole] = React.useState('Student');
    const [singlePassword, setSinglePassword] = React.useState('');

    // Bulk File Form State
    const [selectedRole, setSelectedRole] = React.useState('Student');
    const [file, setFile] = React.useState(null);

    // Common State
    const [loading, setLoading] = React.useState(false);
    const [errorMsg, setErrorMsg] = React.useState('');
    const [successMsg, setSuccessMsg] = React.useState('');
    const [summaryReport, setSummaryReport] = React.useState(null);

    const handleFileChange = (e) => {
        const selected = e.target.files[0];
        if (selected) {
            setFile(selected);
            setErrorMsg('');
        }
    };

    // Single Student Access Submission
    const handleSingleSubmit = async (e) => {
        e.preventDefault();
        setErrorMsg('');
        setSuccessMsg('');
        
        if (!singleGmail || !singleGmail.includes('@')) {
            setErrorMsg('Please enter a valid Gmail address.');
            return;
        }

        setLoading(true);

        try {
            const res = await fetch('/api/users/grant-single-access', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    gmail: singleGmail.trim(),
                    role: singleRole,
                    password: singlePassword.trim() || undefined
                })
            });

            const data = await res.json();

            if (res.ok && data.success) {
                setSuccessMsg(`Access granted to ${singleGmail} (${singleRole} Role). Default Password: ${data.user.password}`);
                setSingleGmail('');
                setSinglePassword('');
                if (onAccessGranted) onAccessGranted(data);
            } else {
                setErrorMsg(data.message || 'Failed to grant user access.');
            }
        } catch (err) {
            setErrorMsg('Network error. Could not connect to backend server.');
        } finally {
            setLoading(false);
        }
    };

    // Bulk Spreadsheet Submission
    const handleBulkSubmit = async (e) => {
        e.preventDefault();
        setErrorMsg('');
        setSummaryReport(null);

        if (!file) {
            setErrorMsg('Please select an Excel (.xlsx) or CSV file to upload.');
            return;
        }

        setLoading(true);

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('default_role', selectedRole);

            const res = await fetch('/api/users/upload-access', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();

            if (res.ok && data.success) {
                setSummaryReport(data);
                if (onAccessGranted) {
                    onAccessGranted(data);
                }
            } else {
                setErrorMsg(data.message || 'Failed to process user access upload.');
            }
        } catch (err) {
            setErrorMsg('Network error. Could not connect to API server.');
        } finally {
            setLoading(false);
        }
    };

    const handleReset = () => {
        setFile(null);
        setSummaryReport(null);
        setErrorMsg('');
        setSuccessMsg('');
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '580px' }}>
                <div className="modal-head">
                    <div>
                        <h3>User Access Management</h3>
                        <p className="modal-sub">Grant platform credentials to single students or upload bulk spreadsheets</p>
                    </div>
                    <button type="button" className="modal-close" onClick={onClose}>&times;</button>
                </div>

                {/* Mode Selector Tabs */}
                <div style={{ display: 'flex', borderBottom: '1px solid #334155', margin: '12px 0 20px 0' }}>
                    <button
                        type="button"
                        onClick={() => { setGrantMode('single'); setErrorMsg(''); setSuccessMsg(''); }}
                        style={{
                            flex: 1,
                            padding: '10px',
                            background: grantMode === 'single' ? '#2563eb' : 'transparent',
                            color: grantMode === 'single' ? '#ffffff' : '#94a3b8',
                            border: 'none',
                            fontWeight: '600',
                            borderRadius: '6px 6px 0 0',
                            cursor: 'pointer'
                        }}
                    >
                        Single User Access
                    </button>
                    <button
                        type="button"
                        onClick={() => { setGrantMode('bulk'); setErrorMsg(''); setSuccessMsg(''); }}
                        style={{
                            flex: 1,
                            padding: '10px',
                            background: grantMode === 'bulk' ? '#2563eb' : 'transparent',
                            color: grantMode === 'bulk' ? '#ffffff' : '#94a3b8',
                            border: 'none',
                            fontWeight: '600',
                            borderRadius: '6px 6px 0 0',
                            cursor: 'pointer'
                        }}
                    >
                        Bulk Excel Upload
                    </button>
                </div>

                {errorMsg && (
                    <div className="form-alert-error" style={{ marginBottom: '16px' }}>
                        {errorMsg}
                    </div>
                )}

                {successMsg && (
                    <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', color: '#34d399', padding: '12px 16px', borderRadius: '6px', marginBottom: '16px', fontSize: '0.9rem' }}>
                        {successMsg}
                    </div>
                )}

                {/* MODE 1: SINGLE USER ACCESS FORM */}
                {grantMode === 'single' && (
                    <form onSubmit={handleSingleSubmit} className="modal-form">
                        <div className="input-field" style={{ marginBottom: '16px' }}>
                            <label style={{ color: '#f8fafc', fontWeight: '500', marginBottom: '6px', display: 'block' }}>Student Gmail Address *</label>
                            <input
                                type="email"
                                placeholder="student.name@gmail.com"
                                value={singleGmail}
                                onChange={(e) => setSingleGmail(e.target.value)}
                                required
                                style={{
                                    width: '100%',
                                    padding: '10px 14px',
                                    borderRadius: '6px',
                                    background: '#0f172a',
                                    border: '1px solid #334155',
                                    color: '#f8fafc'
                                }}
                            />
                        </div>

                        <div className="input-field" style={{ marginBottom: '16px' }}>
                            <label style={{ color: '#f8fafc', fontWeight: '500', marginBottom: '6px', display: 'block' }}>Assignee Role *</label>
                            <select
                                className="form-select"
                                value={singleRole}
                                onChange={(e) => setSingleRole(e.target.value)}
                                required
                                style={{
                                    width: '100%',
                                    padding: '10px 14px',
                                    borderRadius: '6px',
                                    background: '#0f172a',
                                    border: '1px solid #334155',
                                    color: '#f8fafc'
                                }}
                            >
                                <option value="Student">Student</option>
                                <option value="Mentor">Mentor</option>
                                <option value="Department">Department</option>
                                <option value="Recruiter">Recruiter</option>
                                <option value="Coordinator">Coordinator</option>
                            </select>
                        </div>

                        <div className="input-field" style={{ marginBottom: '20px' }}>
                            <label style={{ color: '#f8fafc', fontWeight: '500', marginBottom: '6px', display: 'block' }}>Set Account Password *</label>
                            <input
                                type="text"
                                placeholder="Enter password (e.g. StudentPass123)"
                                value={singlePassword}
                                onChange={(e) => setSinglePassword(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '10px 14px',
                                    borderRadius: '6px',
                                    background: '#0f172a',
                                    border: '1px solid #334155',
                                    color: '#f8fafc'
                                }}
                            />
                            <span style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '4px', display: 'block' }}>
                                Enter a password for this user, or leave blank to assign role default (<strong>{singleRole === 'Student' ? 'student123' : singleRole === 'Mentor' ? 'mentor123' : 'user123'}</strong>).
                            </span>
                        </div>


                        <div className="modal-foot">
                            <button type="button" className="btn-cancel" onClick={onClose} disabled={loading}>
                                Cancel
                            </button>
                            <button type="submit" className="btn-submit" disabled={loading || !singleGmail}>
                                {loading ? 'Granting Access...' : 'Grant Single User Access'}
                            </button>
                        </div>
                    </form>
                )}

                {/* MODE 2: BULK EXCEL UPLOAD FORM */}
                {grantMode === 'bulk' && (
                    summaryReport ? (
                        <div className="upload-summary-box">
                            <div className="summary-badge-icon">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                            </div>
                            <h4>User Access Granted Successfully!</h4>
                            <p className="summary-desc">{summaryReport.message}</p>

                            <div className="summary-metrics">
                                <div className="sum-stat">
                                    <span className="val">{summaryReport.created_count}</span>
                                    <span className="lbl">New Accounts Created</span>
                                </div>
                                <div className="sum-stat">
                                    <span className="val">{summaryReport.updated_count}</span>
                                    <span className="lbl">Roles Updated</span>
                                </div>
                                <div className="sum-stat">
                                    <span className="val">{summaryReport.skipped_count}</span>
                                    <span className="lbl">Skipped Rows</span>
                                </div>
                            </div>

                            <div className="modal-foot">
                                <button type="button" className="btn-cancel" onClick={handleReset}>
                                    Upload Another File
                                </button>
                                <button type="button" className="btn-submit" onClick={onClose}>
                                    Done
                                </button>
                            </div>
                        </div>
                    ) : (
                        <form onSubmit={handleBulkSubmit} className="modal-form">
                            {/* Expected Format Template Card */}
                            <div className="template-download-card">
                                <div className="template-card-header">
                                    <div className="template-card-icon">
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                            <polyline points="14 2 14 8 20 8"></polyline>
                                            <line x1="12" y1="18" x2="12" y2="12"></line>
                                            <line x1="9" y1="15" x2="15" y2="15"></line>
                                        </svg>
                                    </div>
                                    <div>
                                        <h5 className="template-card-title">Expected Excel Format & Sample Template</h5>
                                        <p className="template-card-sub">Download expected template to know column format before uploading</p>
                                    </div>
                                </div>

                                <div className="template-columns-info">
                                    <span className="col-badge required">User Email / gmail *</span>
                                    <span className="col-badge optional">Role (Student, Mentor...)</span>
                                    <span className="col-badge optional">Password</span>
                                </div>

                                <div className="template-download-actions">
                                    <a 
                                        href="/api/templates/download/sample_user_access.xlsx" 
                                        download="sample_user_access.xlsx" 
                                        className="btn-download-tpl excel"
                                        title="Download Excel format template (.xlsx)"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                            <polyline points="7 10 12 15 17 10"></polyline>
                                            <line x1="12" y1="15" x2="12" y2="3"></line>
                                        </svg>
                                        Download Excel (.xlsx)
                                    </a>

                                    <a 
                                        href="/api/templates/download/sample_user_access.csv" 
                                        download="sample_user_access.csv" 
                                        className="btn-download-tpl csv"
                                        title="Download CSV format template (.csv)"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                            <polyline points="7 10 12 15 17 10"></polyline>
                                            <line x1="12" y1="15" x2="12" y2="3"></line>
                                        </svg>
                                        Download CSV (.csv)
                                    </a>
                                </div>
                            </div>

                            <div className="input-field" style={{ marginBottom: '16px' }}>
                                <label style={{ color: '#f8fafc', fontWeight: '500', marginBottom: '6px', display: 'block' }}>Default Assignee Role *</label>
                                <select
                                    className="form-select"
                                    value={selectedRole}
                                    onChange={(e) => setSelectedRole(e.target.value)}
                                    required
                                    style={{
                                        width: '100%',
                                        padding: '10px 14px',
                                        borderRadius: '6px',
                                        background: '#0f172a',
                                        border: '1px solid #334155',
                                        color: '#f8fafc'
                                    }}
                                >
                                    <option value="Student">Student</option>
                                    <option value="Mentor">Mentor</option>
                                    <option value="Department">Department</option>
                                    <option value="Recruiter">Recruiter</option>
                                    <option value="Coordinator">Coordinator</option>
                                </select>
                            </div>

                            <div className="file-dropzone" style={{ marginBottom: '16px' }}>
                                <input
                                    type="file"
                                    id="userAccessFileInput"
                                    accept=".xlsx, .xls, .csv"
                                    onChange={handleFileChange}
                                    style={{ display: 'none' }}
                                />
                                <label htmlFor="userAccessFileInput" className="dropzone-label">
                                    <div className="dropzone-icon">
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                                            <circle cx="9" cy="7" r="4"></circle>
                                        </svg>
                                    </div>
                                    {file ? (
                                        <div className="file-selected-info">
                                            <span className="fname">{file.name}</span>
                                            <span className="fsize">({(file.size / 1024).toFixed(1)} KB)</span>
                                        </div>
                                    ) : (
                                        <div>
                                            <span className="drop-title">Click to upload user access spreadsheet</span>
                                            <span className="drop-sub">Supports .xlsx and .csv files</span>
                                        </div>
                                    )}
                                </label>
                            </div>

                            <div className="modal-foot">
                                <button type="button" className="btn-cancel" onClick={onClose} disabled={loading}>
                                    Cancel
                                </button>
                                <button type="submit" className="btn-submit" disabled={loading || !file}>
                                    {loading ? 'Granting Access...' : 'Upload & Grant User Access'}
                                </button>
                            </div>
                        </form>
                    )
                )}
            </div>
        </div>
    );
}
