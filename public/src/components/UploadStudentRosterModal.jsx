function UploadStudentRosterModal({ isOpen, onClose, onRosterUploaded }) {
    if (!isOpen) return null;

    const [file, setFile] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [errorMsg, setErrorMsg] = React.useState('');
    const [summaryReport, setSummaryReport] = React.useState(null);

    const handleFileChange = (e) => {
        const selected = e.target.files[0];
        if (selected) {
            setFile(selected);
            setErrorMsg('');
        }
    };

    const handleSubmit = async (e) => {
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

            const res = await fetch('/api/upload/student-roster', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();

            if (res.ok && data.success) {
                setSummaryReport(data);
                if (onRosterUploaded) {
                    onRosterUploaded(data);
                }
            } else {
                setErrorMsg(data.message || data.detail || 'Failed to process student roster upload.');
            }
        } catch (err) {
            console.error('Error uploading student roster:', err);
            setErrorMsg('Network error. Could not connect to API server.');
        } finally {
            setLoading(false);
        }
    };

    const handleReset = () => {
        setFile(null);
        setSummaryReport(null);
        setErrorMsg('');
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-dialog large-dialog" onClick={(e) => e.stopPropagation()}>
                <div className="modal-head">
                    <div>
                        <h3>Bulk Student Academic Roster Import</h3>
                        <p className="modal-sub">Import or update academic records, CGPA, department, and skills for all students at once</p>
                    </div>
                    <button type="button" className="modal-close" onClick={onClose}>&times;</button>
                </div>

                {errorMsg && (
                    <div className="form-alert-error" style={{ marginBottom: '16px' }}>
                        {errorMsg}
                    </div>
                )}

                {summaryReport ? (
                    <div className="upload-summary-box">
                        <div className="summary-badge-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <h4>Student Academic Roster Updated!</h4>
                        <p className="summary-desc">{summaryReport.message}</p>

                        <div className="summary-metrics">
                            <div className="sum-stat">
                                <span className="val">{summaryReport.imported_count}</span>
                                <span className="lbl">Profiles Imported/Updated</span>
                            </div>
                            <div className="sum-stat">
                                <span className="val">{summaryReport.skipped_count}</span>
                                <span className="lbl">Skipped Invalid Rows</span>
                            </div>
                            <div className="sum-stat">
                                <span className="val">{summaryReport.total_rows}</span>
                                <span className="lbl">Total File Rows</span>
                            </div>
                        </div>

                        {summaryReport.students && summaryReport.students.length > 0 && (
                            <div className="preview-list-container">
                                <span className="preview-title">Sample Updated Student Profiles:</span>
                                <div className="preview-list">
                                    {summaryReport.students.slice(0, 5).map((st, i) => (
                                        <div key={i} className="preview-item">
                                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                                                <span className="p-gmail">{st.name} ({st.register_number})</span>
                                                <span style={{ fontSize: '0.74rem', color: '#94a3b8' }}>{st.email} &bull; {st.department}</span>
                                            </div>
                                            <span className="p-res">CGPA {st.cgpa}</span>
                                        </div>
                                    ))}
                                    {summaryReport.students.length > 5 && (
                                        <span className="more-count">+ {summaryReport.students.length - 5} more student profiles updated</span>
                                    )}
                                </div>
                            </div>
                        )}

                        <div className="modal-foot">
                            <button type="button" className="btn-cancel" onClick={handleReset}>
                                Upload Another Spreadsheet
                            </button>
                            <button type="button" className="btn-submit" onClick={onClose}>
                                Done
                            </button>
                        </div>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="modal-form">
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
                                    <p className="template-card-sub">Download template to verify expected column headers before uploading</p>
                                </div>
                            </div>

                            <div className="template-columns-info">
                                <span className="col-badge required">Register Number *</span>
                                <span className="col-badge required">Full Name *</span>
                                <span className="col-badge required">Student Email *</span>
                                <span className="col-badge required">Department *</span>
                                <span className="col-badge required">CGPA *</span>
                                <span className="col-badge optional">10th Percentage</span>
                                <span className="col-badge optional">12th Percentage</span>
                                <span className="col-badge optional">Technical Skills</span>
                            </div>

                            <div className="template-download-actions">
                                <a 
                                    href="/api/templates/download/sample_student_roster.xlsx" 
                                    download="sample_student_roster.xlsx" 
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
                                    href="/api/templates/download/sample_student_roster.csv" 
                                    download="sample_student_roster.csv" 
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

                        <div className="file-dropzone" style={{ marginBottom: '16px' }}>
                            <input
                                type="file"
                                id="studentRosterFileInput"
                                accept=".xlsx, .xls, .csv"
                                onChange={handleFileChange}
                                style={{ display: 'none' }}
                            />
                            <label htmlFor="studentRosterFileInput" className="dropzone-label">
                                <div className="dropzone-icon">
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                                        <circle cx="8.5" cy="7" r="4"></circle>
                                        <line x1="20" y1="8" x2="20" y2="14"></line>
                                        <line x1="23" y1="11" x2="17" y2="11"></line>
                                    </svg>
                                </div>
                                {file ? (
                                    <div className="file-selected-info">
                                        <span className="fname">{file.name}</span>
                                        <span className="fsize">({(file.size / 1024).toFixed(1)} KB)</span>
                                    </div>
                                ) : (
                                    <div>
                                        <span className="drop-title">Click to upload Student Academic Roster spreadsheet</span>
                                        <span className="drop-sub">Supports .xlsx and .csv files</span>
                                    </div>
                                )}
                            </label>
                        </div>

                        <div className="info-box-tip">
                            <strong>Automatic Upsert Engine:</strong> Matches students by <code>Register Number</code>. Existing student records will be updated with new CGPA, percentages, and skills, while new students will be automatically registered into the database.
                        </div>

                        <div className="modal-foot">
                            <button type="button" className="btn-cancel" onClick={onClose} disabled={loading}>
                                Cancel
                            </button>
                            <button type="submit" className="btn-submit" disabled={loading || !file}>
                                {loading ? 'Importing Roster...' : 'Upload & Update All Student Records'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}
