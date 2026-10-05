function UploadResultsModal({ isOpen, onClose, drives, initialDriveId, onResultsUploaded }) {
    if (!isOpen) return null;

    const [selectedDriveId, setSelectedDriveId] = React.useState(initialDriveId || (drives.length > 0 ? drives[0].id : ''));
    const [file, setFile] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [errorMsg, setErrorMsg] = React.useState('');
    const [summaryReport, setSummaryReport] = React.useState(null);

    React.useEffect(() => {
        if (initialDriveId) {
            setSelectedDriveId(initialDriveId);
        } else if (drives.length > 0 && !selectedDriveId) {
            setSelectedDriveId(drives[0].id);
        }
    }, [initialDriveId, drives]);

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

        if (!selectedDriveId) {
            setErrorMsg('Please select a placement drive.');
            return;
        }

        if (!file) {
            setErrorMsg('Please select an Excel (.xlsx) or CSV file to upload.');
            return;
        }

        setLoading(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const res = await fetch(`/api/drives/${selectedDriveId}/upload-results`, {
                method: 'POST',
                body: formData
            });

            const data = await res.json();

            if (res.ok && data.success) {
                setSummaryReport(data);
                if (onResultsUploaded) {
                    onResultsUploaded(selectedDriveId);
                }
            } else {
                setErrorMsg(data.message || 'Failed to process Excel results upload.');
            }
        } catch (err) {
            console.error('Error uploading results:', err);
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
            <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
                <div className="modal-head">
                    <div>
                        <h3>Upload Shortlisted Candidates Excel</h3>
                        <p className="modal-sub">Extracts 'gmail' column — all listed candidates are shortlisted for the next round</p>
                    </div>
                    <button type="button" className="modal-close" onClick={onClose}>&times;</button>
                </div>

                {errorMsg && (
                    <div className="form-alert-error">
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
                        <h4>Shortlist Upload Completed!</h4>
                        <p className="summary-desc">{summaryReport.message}</p>

                        <div className="summary-metrics">
                            <div className="sum-stat">
                                <span className="val">{summaryReport.updated_count}</span>
                                <span className="lbl">Shortlisted Candidates</span>
                            </div>
                            <div className="sum-stat">
                                <span className="val">{summaryReport.skipped_count}</span>
                                <span className="lbl">Skipped Rows</span>
                            </div>
                            <div className="sum-stat">
                                <span className="val">{summaryReport.total_rows}</span>
                                <span className="lbl">Total Rows</span>
                            </div>
                        </div>

                        {summaryReport.processed_records && summaryReport.processed_records.length > 0 && (
                            <div className="preview-list-container">
                                <span className="preview-title">Shortlisted Candidates & Updated Round:</span>
                                <div className="preview-list">
                                    {summaryReport.processed_records.slice(0, 5).map((rec, i) => (
                                        <div key={i} className="preview-item">
                                            <span className="p-gmail">{rec.gmail}</span>
                                            <span className="p-res">{rec.result} (Round {rec.round})</span>
                                        </div>
                                    ))}
                                    {summaryReport.processed_records.length > 5 && (
                                        <span className="more-count">+ {summaryReport.processed_records.length - 5} more candidates promoted</span>
                                    )}
                                </div>
                            </div>
                        )}

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
                                    <h5 className="template-card-title">Expected Excel Format & Sample Templates</h5>
                                    <p className="template-card-sub">Download pre-formatted sample templates to know exact column formats</p>
                                </div>
                            </div>

                            <div className="template-format-grid">
                                <div className="format-type-box">
                                    <div className="format-type-header">
                                        <span className="format-type-title">Drive Shortlist Template</span>
                                        <span className="format-type-badge">Emails Only</span>
                                    </div>
                                    <div className="template-columns-info">
                                        <span className="col-badge required">Student Gmail *</span>
                                        <span className="col-badge optional">Student Name</span>
                                        <span className="col-badge optional">Branch</span>
                                    </div>
                                    <div className="template-download-actions">
                                        <a 
                                            href="/api/templates/download/sample_drive_shortlist.xlsx" 
                                            download="sample_drive_shortlist.xlsx" 
                                            className="btn-download-tpl excel"
                                            title="Download Shortlist Excel template"
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                                <polyline points="7 10 12 15 17 10"></polyline>
                                                <line x1="12" y1="15" x2="12" y2="3"></line>
                                            </svg>
                                            Excel (.xlsx)
                                        </a>
                                        <a 
                                            href="/api/templates/download/sample_drive_shortlist.csv" 
                                            download="sample_drive_shortlist.csv" 
                                            className="btn-download-tpl csv"
                                            title="Download Shortlist CSV template"
                                        >
                                            CSV (.csv)
                                        </a>
                                    </div>
                                </div>

                                <div className="format-type-box">
                                    <div className="format-type-header">
                                        <span className="format-type-title">Drive Results & Verdicts</span>
                                        <span className="format-type-badge">Status & Scores</span>
                                    </div>
                                    <div className="template-columns-info">
                                        <span className="col-badge required">Student Gmail *</span>
                                        <span className="col-badge required">Result Status *</span>
                                        <span className="col-badge optional">Round</span>
                                        <span className="col-badge optional">Score</span>
                                    </div>
                                    <div className="template-download-actions">
                                        <a 
                                            href="/api/templates/download/sample_drive_results.xlsx" 
                                            download="sample_drive_results.xlsx" 
                                            className="btn-download-tpl excel"
                                            title="Download Drive Results Excel template"
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                                <polyline points="7 10 12 15 17 10"></polyline>
                                                <line x1="12" y1="15" x2="12" y2="3"></line>
                                            </svg>
                                            Excel (.xlsx)
                                        </a>
                                        <a 
                                            href="/api/templates/download/sample_drive_results.csv" 
                                            download="sample_drive_results.csv" 
                                            className="btn-download-tpl csv"
                                            title="Download Drive Results CSV template"
                                        >
                                            CSV (.csv)
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="input-field">
                            <label>Target Placement Drive *</label>
                            <select
                                className="form-select"
                                value={selectedDriveId}
                                onChange={(e) => setSelectedDriveId(e.target.value)}
                                required
                            >
                                {drives.map(d => (
                                    <option key={d.id} value={d.id}>
                                        {d.company_name} - {d.job_role} ({d.location})
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="file-dropzone">
                            <input
                                type="file"
                                id="excelFileInput"
                                accept=".xlsx, .xls, .csv"
                                onChange={handleFileChange}
                                style={{ display: 'none' }}
                            />
                            <label htmlFor="excelFileInput" className="dropzone-label">
                                <div className="dropzone-icon">
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                        <polyline points="14 2 14 8 20 8"></polyline>
                                        <line x1="12" y1="18" x2="12" y2="12"></line>
                                        <line x1="9" y1="15" x2="15" y2="15"></line>
                                    </svg>
                                </div>
                                {file ? (
                                    <div className="file-selected-info">
                                        <span className="fname">{file.name}</span>
                                        <span className="fsize">({(file.size / 1024).toFixed(1)} KB)</span>
                                    </div>
                                ) : (
                                    <div>
                                        <span className="drop-title">Click to upload candidate results spreadsheet</span>
                                        <span className="drop-sub">Supports .xlsx and .csv files</span>
                                    </div>
                                )}
                            </label>
                        </div>

                        <div className="info-box-tip">
                            <strong>Smart Mode Auto-Detection:</strong> Uploading a file with just <code>gmail</code> auto-promotes candidate rounds. Including <code>Result Status</code> (Selected, Rejected, On Hold) updates explicit candidate verdicts & scores.
                        </div>

                        <div className="modal-foot">
                            <button type="button" className="btn-cancel" onClick={onClose} disabled={loading}>
                                Cancel
                            </button>
                            <button type="submit" className="btn-submit" disabled={loading || !file}>
                                {loading ? 'Processing...' : 'Upload & Update Candidate Results'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}
