function CoordinatorDashboard({ user, onLogout }) {
    // Strict Access Control Guard: Students cannot view Coordinator Workspace or User Access tools
    if (user && user.role && user.role.toLowerCase() === 'student') {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0f172a', color: '#f8fafc', padding: '24px' }}>
                <h2 style={{ fontSize: '1.5rem', color: '#ef4444', marginBottom: '8px' }}>Access Restricted</h2>
                <p style={{ color: '#94a3b8', marginBottom: '20px' }}>Student accounts are not authorized to access Coordinator management tools.</p>
                <button type="button" onClick={onLogout} style={{ padding: '10px 20px', borderRadius: '8px', background: '#3b82f6', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: '600' }}>
                    Sign Out
                </button>
            </div>
        );
    }

    const [drives, setDrives] = React.useState([]);
    const [loadingDrives, setLoadingDrives] = React.useState(true);
    const [interventions, setInterventions] = React.useState([]);
    const [loadingInterventions, setLoadingInterventions] = React.useState(true);
    const [activeTab, setActiveTab] = React.useState('drives');

    // Modal states
    const [isCreateModalOpen, setIsCreateModalOpen] = React.useState(false);
    const [isUploadModalOpen, setIsUploadModalOpen] = React.useState(false);
    const [isViewModalOpen, setIsViewModalOpen] = React.useState(false);
    const [isUserAccessModalOpen, setIsUserAccessModalOpen] = React.useState(false);
    const [isTemplatesModalOpen, setIsTemplatesModalOpen] = React.useState(false);
    const [isRosterModalOpen, setIsRosterModalOpen] = React.useState(false);
    const [selectedDriveForUpload, setSelectedDriveForUpload] = React.useState(null);
    const [selectedDriveForView, setSelectedDriveForView] = React.useState(null);

    // User management state
    const [managedUsers, setManagedUsers] = React.useState([]);
    const [loadingUsers, setLoadingUsers] = React.useState(false);
    const [userSearchTerm, setUserSearchTerm] = React.useState('');
    const [userRoleFilter, setUserRoleFilter] = React.useState('All');
    const [userStatusFilter, setUserStatusFilter] = React.useState('All');
    const [confirmRevoke, setConfirmRevoke] = React.useState(null);
    const [accessHistory, setAccessHistory] = React.useState([]);
    const [loadingHistory, setLoadingHistory] = React.useState(false);
    const [historyTarget, setHistoryTarget] = React.useState(null);
    const [roleEditUser, setRoleEditUser] = React.useState(null);
    const [roleEditValue, setRoleEditValue] = React.useState('');

    const [searchTerm, setSearchTerm] = React.useState('');
    const [viewMode, setViewMode] = React.useState('table'); // 'table' or 'grid'
    const [toastMessage, setToastMessage] = React.useState('');

    const fetchDrives = React.useCallback(async () => {
        setLoadingDrives(true);
        try {
            const res = await fetch('/api/drives');
            const data = await res.json();
            if (res.ok && data.success) {
                setDrives(data.drives || []);
            }
        } catch (err) {
            console.error('Failed to fetch drives:', err);
        } finally {
            setLoadingDrives(false);
        }
    }, []);

    React.useEffect(() => {
        fetchDrives();
    }, [fetchDrives]);

    const fetchInterventions = React.useCallback(async () => {
        setLoadingInterventions(true);
        try {
            const res = await fetch('/api/interventions', {
                headers: window.interventionHeaders(user)
            });
            if (res.ok) {
                const data = await res.json();
                setInterventions(data.interventions || []);
            }
        } catch (err) {
            console.error('Failed to fetch interventions:', err);
        } finally {
            setLoadingInterventions(false);
        }
    }, [user]);

    React.useEffect(() => {
        fetchInterventions();
    }, [fetchInterventions]);

    const updateInterventionStatus = async (interventionId, nextStatus) => {
        const res = await fetch(`/api/interventions/${interventionId}/status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', ...window.interventionHeaders(user) },
            body: JSON.stringify({ status: nextStatus })
        });
        if (res.ok) {
            setInterventions(prev => prev.map(item => item.id === interventionId ? { ...item, status: nextStatus } : item));
            setToastMessage(`Intervention marked ${nextStatus.toLowerCase()}.`);
            setTimeout(() => setToastMessage(''), 3500);
        }
    };

    const regenerateIntervention = async (studentGmail) => {
        const res = await fetch('/api/interventions/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...window.interventionHeaders(user) },
            body: JSON.stringify({ gmail: studentGmail })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            await fetchInterventions();
            setToastMessage('Intervention generated successfully.');
        } else {
            setToastMessage(data.detail || 'Unable to generate intervention.');
        }
        setTimeout(() => setToastMessage(''), 3500);
    };

    const handleDriveCreated = (newDrive) => {
        setDrives(prev => [newDrive, ...prev]);
        setToastMessage(`Drive for "${newDrive.company_name}" published successfully.`);
        setTimeout(() => setToastMessage(''), 3500);
    };

    const handleResultsUploaded = (driveId) => {
        fetchDrives();
        setToastMessage(`Student results updated successfully.`);
        setTimeout(() => setToastMessage(''), 3500);
    };

    const handleUserAccessGranted = (data) => {
        setToastMessage(`Successfully granted access to ${data.total_processed} user account(s).`);
        setTimeout(() => setToastMessage(''), 3500);
    };

    const handleRosterUploaded = (data) => {
        setToastMessage(`Successfully imported/updated ${data.imported_count} student academic profiles.`);
        setTimeout(() => setToastMessage(''), 3500);
    };

    const authHeaders = { 'X-User-Id': user.uuid };

    const fetchManagedUsers = React.useCallback(async () => {
        setLoadingUsers(true);
        try {
            const res = await fetch('/api/users/managed', { headers: authHeaders });
            const data = await res.json();
            if (res.ok && data.success) setManagedUsers(data.users || []);
        } catch (err) { console.error('Failed to fetch users:', err); }
        finally { setLoadingUsers(false); }
    }, [user.uuid]);

    React.useEffect(() => {
        if (activeTab === 'users') fetchManagedUsers();
    }, [activeTab, fetchManagedUsers]);

    const handleRevoke = async (gmail) => {
        try {
            const res = await fetch('/api/users/revoke', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify({ gmail })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                setToastMessage(data.message);
                fetchManagedUsers();
            } else {
                setToastMessage(data.detail || data.message || 'Failed to revoke access.');
            }
        } catch (err) { setToastMessage('Network error revoking access.'); }
        setConfirmRevoke(null);
        setTimeout(() => setToastMessage(''), 3500);
    };

    const handleReactivate = async (gmail) => {
        try {
            const res = await fetch('/api/users/reactivate', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify({ gmail })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                setToastMessage(data.message);
                fetchManagedUsers();
            } else {
                setToastMessage(data.detail || data.message || 'Failed to reactivate access.');
            }
        } catch (err) { setToastMessage('Network error reactivating access.'); }
        setTimeout(() => setToastMessage(''), 3500);
    };

    const handleRoleUpdate = async (gmail, newRole) => {
        try {
            const res = await fetch('/api/users/update-role', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify({ gmail, new_role: newRole })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                setToastMessage(data.message);
                fetchManagedUsers();
            } else {
                setToastMessage(data.detail || data.message || 'Failed to update role.');
            }
        } catch (err) { setToastMessage('Network error updating role.'); }
        setRoleEditUser(null);
        setTimeout(() => setToastMessage(''), 3500);
    };

    const fetchAccessHistory = async (gmail) => {
        setLoadingHistory(true);
        setHistoryTarget(gmail || 'all');
        try {
            const url = gmail ? `/api/users/access-history?gmail=${encodeURIComponent(gmail)}` : '/api/users/access-history';
            const res = await fetch(url, { headers: authHeaders });
            const data = await res.json();
            if (res.ok && data.success) setAccessHistory(data.history || []);
        } catch (err) { console.error('Failed to fetch history:', err); }
        finally { setLoadingHistory(false); }
    };

    const filteredUsers = managedUsers.filter(u => {
        const matchSearch = u.gmail.toLowerCase().includes(userSearchTerm.toLowerCase());
        const matchRole = userRoleFilter === 'All' || u.role === userRoleFilter;
        const statusLabel = u.is_active ? 'ACTIVE' : 'REVOKED';
        const matchStatus = userStatusFilter === 'All' || userStatusFilter === statusLabel;
        return matchSearch && matchRole && matchStatus;
    });

    const openUploadModal = (driveId = null) => {
        setSelectedDriveForUpload(driveId);
        setIsUploadModalOpen(true);
    };

    const openViewModal = (drive) => {
        setSelectedDriveForView(drive);
        setIsViewModalOpen(true);
    };

    const filteredDrives = drives.filter(d =>
        d.company_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        d.job_role.toLowerCase().includes(searchTerm.toLowerCase()) ||
        d.allowed_branches.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="laptop-dashboard">
            {/* Top Navigation Bar */}
            <header className="desktop-navbar">
                <div className="nav-left">
                    <div className="brand-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M22 10v6M2 10l10-5 10 5-10 5z"></path>
                            <path d="M6 12v5c3 3 9 3 12 0v-5"></path>
                        </svg>
                    </div>
                    <div className="brand-text">
                        <span className="portal-name">Placement Management Portal</span>
                        <span className="portal-sub">Coordinator Workspace</span>
                    </div>
                </div>

                <div className="nav-tabs" style={{ display: 'flex', gap: '8px', marginLeft: '24px' }}>
                    <button type="button" className={`tab-btn ${activeTab === 'drives' ? 'active' : ''}`} onClick={() => setActiveTab('drives')}>Placement Drives</button>
                    <button type="button" className={`tab-btn ${activeTab === 'interventions' ? 'active' : ''}`} onClick={() => setActiveTab('interventions')}>Interventions ({interventions.length})</button>
                    <button type="button" className={`tab-btn ${activeTab === 'users' ? 'active' : ''}`} onClick={() => setActiveTab('users')}>Manage Users</button>
                </div>

                <div className="nav-right">
                    <div className="user-badge">
                        <span className="user-email">{user.gmail}</span>
                        <span className="badge-pill coordinator-pill">Coordinator</span>
                    </div>

                    <button type="button" className="btn-nav-signout" onClick={onLogout} title="Sign Out">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                            <polyline points="16 17 21 12 16 7"></polyline>
                            <line x1="21" y1="12" x2="9" y2="12"></line>
                        </svg>
                        Sign Out
                    </button>
                </div>
            </header>

            {/* Toast Notification */}
            {toastMessage && (
                <div className="toast-bar">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    <span>{toastMessage}</span>
                </div>
            )}

            {/* Main Content Area */}
            <div className="dashboard-content">
                {/* Metrics Banner */}
                <div className="metrics-row">
                    <div className="metric-box">
                        <span className="metric-num">{drives.length}</span>
                        <span className="metric-title">Active Drives</span>
                    </div>
                    <div className="metric-box">
                        <span className="metric-num">482</span>
                        <span className="metric-title">Candidates Registered</span>
                    </div>
                    <div className="metric-box">
                        <span className="metric-num">145</span>
                        <span className="metric-title">Placed Students</span>
                    </div>
                    <div className="metric-box">
                        <span className="metric-num">
                            {drives.reduce((acc, d) => acc + (d.results_count || 0), 0)}
                        </span>
                        <span className="metric-title">Total Results Uploaded</span>
                    </div>
                </div>

                {activeTab === 'interventions' && (
                    <InterventionRoster
                        user={user}
                        canGenerate={true}
                        title="All Student Interventions"
                        description="Expand any authorized student to inspect their intervention and action plan."
                    />
                )}

                {activeTab === 'users' && (
                    <div style={{ marginBottom: '20px' }}>
                        {/* User Management Controls */}
                        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '16px' }}>
                            <div className="search-field" style={{ flex: '1 1 240px' }}>
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                                <input type="text" placeholder="Search by email..." value={userSearchTerm} onChange={(e) => setUserSearchTerm(e.target.value)} />
                            </div>
                            <select value={userRoleFilter} onChange={(e) => setUserRoleFilter(e.target.value)} style={{ padding: '9px 14px', borderRadius: '6px', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc', fontSize: '0.9rem' }}>
                                <option value="All">All Roles</option>
                                <option value="Student">Student</option>
                                <option value="Mentor">Mentor</option>
                                <option value="Department">Department</option>
                                <option value="Recruiter">Recruiter</option>
                                <option value="Coordinator">Coordinator</option>
                            </select>
                            <select value={userStatusFilter} onChange={(e) => setUserStatusFilter(e.target.value)} style={{ padding: '9px 14px', borderRadius: '6px', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc', fontSize: '0.9rem' }}>
                                <option value="All">All Status</option>
                                <option value="ACTIVE">Active</option>
                                <option value="REVOKED">Revoked</option>
                            </select>
                            <button type="button" className="btn-upload-access" onClick={() => setIsUserAccessModalOpen(true)} style={{ whiteSpace: 'nowrap' }}>
                                + Grant Access
                            </button>
                            <button type="button" onClick={() => fetchAccessHistory(null)} style={{ padding: '9px 16px', borderRadius: '6px', background: '#334155', color: '#f8fafc', border: 'none', cursor: 'pointer', fontWeight: '500', fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
                                View All History
                            </button>
                            <button type="button" onClick={() => fetchManagedUsers()} style={{ padding: '9px 16px', borderRadius: '6px', background: '#334155', color: '#f8fafc', border: 'none', cursor: 'pointer', fontWeight: '500', fontSize: '0.85rem' }}>
                                Refresh
                            </button>
                        </div>

                        {/* Users Table */}
                        {loadingUsers ? (
                            <div className="panel-loading"><div className="spinner-sm"></div><span>Loading users...</span></div>
                        ) : filteredUsers.length === 0 ? (
                            <div className="panel-empty"><h3>No Users Found</h3><p>No users match the current filters.</p></div>
                        ) : (
                            <div className="table-responsive">
                                <table className="enterprise-table">
                                    <thead>
                                        <tr>
                                            <th>Email</th>
                                            <th>Role</th>
                                            <th>Status</th>
                                            <th>Created</th>
                                            <th style={{ textAlign: 'right' }}>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filteredUsers.map(u => (
                                            <tr key={u.uuid}>
                                                <td className="font-semibold">{u.gmail}</td>
                                                <td>
                                                    {roleEditUser === u.uuid ? (
                                                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                                                            <select value={roleEditValue} onChange={(e) => setRoleEditValue(e.target.value)} style={{ padding: '4px 8px', borderRadius: '4px', background: '#0f172a', border: '1px solid #475569', color: '#f8fafc', fontSize: '0.85rem' }}>
                                                                {['Student', 'Mentor', 'Department', 'Recruiter', 'Coordinator'].map(r => <option key={r} value={r}>{r}</option>)}
                                                            </select>
                                                            <button onClick={() => handleRoleUpdate(u.gmail, roleEditValue)} style={{ padding: '3px 10px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}>Save</button>
                                                            <button onClick={() => setRoleEditUser(null)} style={{ padding: '3px 10px', background: '#475569', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}>Cancel</button>
                                                        </div>
                                                    ) : (
                                                        <span className={`badge-pill ${u.role.toLowerCase()}-pill`} style={{ cursor: 'pointer' }} onClick={() => { setRoleEditUser(u.uuid); setRoleEditValue(u.role); }} title="Click to change role">{u.role}</span>
                                                    )}
                                                </td>
                                                <td>
                                                    <span style={{ display: 'inline-block', padding: '3px 10px', borderRadius: '12px', fontSize: '0.8rem', fontWeight: '600', background: u.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: u.is_active ? '#34d399' : '#f87171', border: `1px solid ${u.is_active ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}` }}>
                                                        {u.is_active ? 'ACTIVE' : 'REVOKED'}
                                                    </span>
                                                </td>
                                                <td style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
                                                <td style={{ textAlign: 'right' }}>
                                                    <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                                                        {u.is_active ? (
                                                            <button onClick={() => setConfirmRevoke(u)} style={{ padding: '5px 12px', borderRadius: '6px', background: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)', cursor: 'pointer', fontSize: '0.8rem', fontWeight: '600' }}>Revoke</button>
                                                        ) : (
                                                            <button onClick={() => handleReactivate(u.gmail)} style={{ padding: '5px 12px', borderRadius: '6px', background: 'rgba(16,185,129,0.15)', color: '#34d399', border: '1px solid rgba(16,185,129,0.3)', cursor: 'pointer', fontSize: '0.8rem', fontWeight: '600' }}>Reactivate</button>
                                                        )}
                                                        <button onClick={() => fetchAccessHistory(u.gmail)} style={{ padding: '5px 12px', borderRadius: '6px', background: 'rgba(37,99,235,0.15)', color: '#60a5fa', border: '1px solid rgba(37,99,235,0.3)', cursor: 'pointer', fontSize: '0.8rem', fontWeight: '500' }}>History</button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        {/* Revoke Confirmation Modal */}
                        {confirmRevoke && (
                            <div className="modal-overlay" onClick={() => setConfirmRevoke(null)}>
                                <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '440px' }}>
                                    <div className="modal-head">
                                        <h3 style={{ color: '#f87171' }}>Confirm Revoke Access</h3>
                                        <button type="button" className="modal-close" onClick={() => setConfirmRevoke(null)}>&times;</button>
                                    </div>
                                    <div style={{ padding: '16px 0' }}>
                                        <p style={{ color: '#f8fafc', marginBottom: '8px' }}>Revoke access for <strong>{confirmRevoke.gmail}</strong>?</p>
                                        <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>This user will no longer be able to log in until access is reactivated by a coordinator.</p>
                                    </div>
                                    <div className="modal-foot">
                                        <button type="button" className="btn-cancel" onClick={() => setConfirmRevoke(null)}>Cancel</button>
                                        <button type="button" onClick={() => handleRevoke(confirmRevoke.gmail)} style={{ padding: '10px 20px', borderRadius: '6px', background: '#ef4444', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: '600' }}>Revoke Access</button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Access History Modal */}
                        {historyTarget && (
                            <div className="modal-overlay" onClick={() => { setHistoryTarget(null); setAccessHistory([]); }}>
                                <div className="modal-dialog large-dialog" onClick={(e) => e.stopPropagation()}>
                                    <div className="modal-head">
                                        <div>
                                            <h3>Access History{historyTarget !== 'all' ? ` — ${historyTarget}` : ''}</h3>
                                            <p className="modal-sub">Audit log of access changes</p>
                                        </div>
                                        <button type="button" className="modal-close" onClick={() => { setHistoryTarget(null); setAccessHistory([]); }}>&times;</button>
                                    </div>
                                    {loadingHistory ? (
                                        <div className="panel-loading"><div className="spinner-sm"></div><span>Loading history...</span></div>
                                    ) : accessHistory.length === 0 ? (
                                        <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8' }}>No access history found.</div>
                                    ) : (
                                        <div className="table-responsive" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                                            <table className="enterprise-table">
                                                <thead><tr><th>User</th><th>Action</th><th>Old Role</th><th>New Role</th><th>Old Status</th><th>New Status</th><th>Actor</th><th>Time</th></tr></thead>
                                                <tbody>
                                                    {accessHistory.map(h => (
                                                        <tr key={h.id}>
                                                            <td style={{ fontSize: '0.85rem' }}>{h.user_gmail}</td>
                                                            <td>
                                                                <span style={{ padding: '2px 8px', borderRadius: '10px', fontSize: '0.78rem', fontWeight: '600',
                                                                    background: h.action === 'GRANTED' ? 'rgba(16,185,129,0.15)' : h.action === 'REVOKED' ? 'rgba(239,68,68,0.15)' : h.action === 'REACTIVATED' ? 'rgba(59,130,246,0.15)' : 'rgba(168,85,247,0.15)',
                                                                    color: h.action === 'GRANTED' ? '#34d399' : h.action === 'REVOKED' ? '#f87171' : h.action === 'REACTIVATED' ? '#60a5fa' : '#c084fc' }}>
                                                                    {h.action}
                                                                </span>
                                                            </td>
                                                            <td style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{h.old_role || '—'}</td>
                                                            <td style={{ fontSize: '0.85rem' }}>{h.new_role || '—'}</td>
                                                            <td style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{h.old_status || '—'}</td>
                                                            <td style={{ fontSize: '0.85rem' }}>{h.new_status || '—'}</td>
                                                            <td style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{h.actor_gmail || 'System'}</td>
                                                            <td style={{ color: '#64748b', fontSize: '0.8rem' }}>{h.created_at ? new Date(h.created_at).toLocaleString() : '—'}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                    <div className="modal-foot" style={{ marginTop: '12px' }}><button type="button" className="btn-submit" onClick={() => { setHistoryTarget(null); setAccessHistory([]); }}>Close</button></div>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Toolbar & Filter Bar */}
                {activeTab === 'drives' && <div className="table-toolbar">
                    <div className="search-field">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="11" cy="11" r="8"></circle>
                            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                        </svg>
                        <input
                            type="text"
                            placeholder="Filter by company, position, or branch..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>

                    <div className="toolbar-actions">
                        <div className="view-toggle-group">
                            <button
                                type="button"
                                className={`view-btn ${viewMode === 'table' ? 'active' : ''}`}
                                onClick={() => setViewMode('table')}
                                title="Table View"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <line x1="8" y1="6" x2="21" y2="6"></line>
                                    <line x1="8" y1="12" x2="21" y2="12"></line>
                                    <line x1="8" y1="18" x2="21" y2="18"></line>
                                    <line x1="3" y1="6" x2="3.01" y2="6"></line>
                                    <line x1="3" y1="12" x2="3.01" y2="12"></line>
                                    <line x1="3" y1="18" x2="3.01" y2="18"></line>
                                </svg>
                                Table
                            </button>
                            <button
                                type="button"
                                className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
                                onClick={() => setViewMode('grid')}
                                title="Grid View"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <rect x="3" y="3" width="7" height="7"></rect>
                                    <rect x="14" y="3" width="7" height="7"></rect>
                                    <rect x="14" y="14" width="7" height="7"></rect>
                                    <rect x="3" y="14" width="7" height="7"></rect>
                                </svg>
                                Cards
                            </button>
                        </div>

                        <button
                            type="button"
                            className="btn-templates-hub"
                            onClick={() => setIsTemplatesModalOpen(true)}
                            title="Download official Excel (.xlsx) and CSV templates"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="7 10 12 15 17 10"></polyline>
                                <line x1="12" y1="15" x2="12" y2="3"></line>
                            </svg>
                            Download Templates
                        </button>

                        <button
                            type="button"
                            className="btn-upload-access"
                            onClick={() => setIsUserAccessModalOpen(true)}
                            title="Upload Excel with Gmails to Grant User Access"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                                <circle cx="9" cy="7" r="4"></circle>
                                <path d="M23 21v-2a4 4 0 0 3-3.87"></path>
                                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                            </svg>
                            Grant User Access (Excel)
                        </button>

                        <button
                            type="button"
                            className="btn-upload-roster"
                            onClick={() => setIsRosterModalOpen(true)}
                            title="Upload Excel with Student Academic Profiles, CGPA, and Skills"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                                <circle cx="8.5" cy="7" r="4"></circle>
                                <line x1="20" y1="8" x2="20" y2="14"></line>
                                <line x1="23" y1="11" x2="17" y2="11"></line>
                            </svg>
                            Import Student Roster (Excel)
                        </button>

                        <button
                            type="button"
                            className="btn-upload-results"
                            onClick={() => openUploadModal(null)}
                            title="Upload Excel with Candidate Gmail & Results"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="17 8 12 3 7 8"></polyline>
                                <line x1="12" y1="3" x2="12" y2="15"></line>
                            </svg>
                            Upload Excel Results
                        </button>

                        <button
                            type="button"
                            className="btn-create-drive"
                            onClick={() => setIsCreateModalOpen(true)}
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <line x1="12" y1="5" x2="12" y2="19"></line>
                                <line x1="5" y1="12" x2="19" y2="12"></line>
                            </svg>
                            Create Placement Drive
                        </button>
                    </div>
                </div>}

                {/* Main Data Section */}
                {activeTab === 'drives' && <div className="data-panel">
                    {loadingDrives ? (
                        <div className="panel-loading">
                            <div className="spinner-sm"></div>
                            <span>Loading placement drives...</span>
                        </div>
                    ) : filteredDrives.length === 0 ? (
                        <div className="panel-empty">
                            <h3>No Drives Found</h3>
                            <p>Click "Create Placement Drive" to add a new recruitment drive.</p>
                            <button type="button" className="btn-create-drive" onClick={() => setIsCreateModalOpen(true)}>
                                Create Drive
                            </button>
                        </div>
                    ) : viewMode === 'table' ? (
                        /* Professional Compact Data Table */
                        <div className="table-responsive">
                            <table className="enterprise-table">
                                <thead>
                                    <tr>
                                        <th>Company</th>
                                        <th>Job Designation</th>
                                        <th>CTC (LPA)</th>
                                        <th>Min CGPA</th>
                                        <th>Eligible Branches</th>
                                        <th>Location</th>
                                        <th>Deadline</th>
                                        <th>Results Count</th>
                                        <th>Status</th>
                                        <th style={{ textAlign: 'right' }}>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredDrives.map(drive => (
                                        <tr key={drive.id}>
                                            <td className="font-semibold">{drive.company_name}</td>
                                            <td>{drive.job_role}</td>
                                            <td className="ctc-text">{drive.ctc_lpa} LPA</td>
                                            <td>{drive.min_cgpa ? `${drive.min_cgpa} / 10` : 'None'}</td>
                                            <td>
                                                <div className="tag-list">
                                                    {drive.allowed_branches.split(',').map((b, i) => (
                                                        <span key={i} className="mini-tag">{b.trim()}</span>
                                                    ))}
                                                </div>
                                            </td>
                                            <td>{drive.location || 'On Campus'}</td>
                                            <td>{drive.deadline || 'Open'}</td>
                                            <td>
                                                <span className="results-badge" onClick={() => openViewModal(drive)}>
                                                    {drive.results_count || 0} Updated
                                                </span>
                                            </td>
                                            <td>
                                                <span className={`status-badge ${drive.status ? drive.status.toLowerCase() : 'active'}`}>
                                                    {drive.status || 'Active'}
                                                </span>
                                            </td>
                                            <td style={{ textAlign: 'right' }}>
                                                <div className="action-button-group">
                                                    <button
                                                        type="button"
                                                        className="action-btn-secondary"
                                                        onClick={() => openUploadModal(drive.id)}
                                                        title="Upload Excel results with Gmail & Result"
                                                    >
                                                        Upload Results
                                                    </button>
                                                    <button
                                                        type="button"
                                                        className="action-btn-primary"
                                                        onClick={() => openViewModal(drive)}
                                                        title="View student results"
                                                    >
                                                        View Results ({drive.results_count || 0})
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        /* Compact Desktop Cards Grid */
                        <div className="cards-grid-laptop">
                            {filteredDrives.map(drive => (
                                <div key={drive.id} className="laptop-card">
                                    <div className="card-top">
                                        <div>
                                            <h4 className="card-company">{drive.company_name}</h4>
                                            <span className="card-role">{drive.job_role}</span>
                                        </div>
                                        <span className={`status-badge ${drive.status ? drive.status.toLowerCase() : 'active'}`}>
                                            {drive.status || 'Active'}
                                        </span>
                                    </div>
                                    <div className="card-metrics">
                                        <div>
                                            <span className="lbl">Package</span>
                                            <span className="val ctc-text">{drive.ctc_lpa} LPA</span>
                                        </div>
                                        <div>
                                            <span className="lbl">CGPA</span>
                                            <span className="val">{drive.min_cgpa || '0.0'}</span>
                                        </div>
                                        <div>
                                            <span className="lbl">Results</span>
                                            <span className="val">{drive.results_count || 0} Records</span>
                                        </div>
                                    </div>
                                    <div className="card-branches">
                                        {drive.allowed_branches.split(',').map((b, i) => (
                                            <span key={i} className="mini-tag">{b.trim()}</span>
                                        ))}
                                    </div>
                                    <div className="card-actions-row">
                                        <button
                                            type="button"
                                            className="btn-card-action outline"
                                            onClick={() => openUploadModal(drive.id)}
                                        >
                                            Upload Excel
                                        </button>
                                        <button
                                            type="button"
                                            className="btn-card-action primary"
                                            onClick={() => openViewModal(drive)}
                                        >
                                            View Results ({drive.results_count || 0})
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>}
            </div>

            {/* Create Drive Modal */}
            <CreateDriveModal
                isOpen={isCreateModalOpen}
                onClose={() => setIsCreateModalOpen(false)}
                onDriveCreated={handleDriveCreated}
            />

            {/* Upload Excel Results Modal */}
            <UploadResultsModal
                isOpen={isUploadModalOpen}
                onClose={() => setIsUploadModalOpen(false)}
                drives={drives}
                initialDriveId={selectedDriveForUpload}
                onResultsUploaded={handleResultsUploaded}
            />

            {/* View Candidate Results Modal */}
            <ViewResultsModal
                isOpen={isViewModalOpen}
                onClose={() => setIsViewModalOpen(false)}
                drive={selectedDriveForView}
            />

            {/* Upload User Access Modal */}
            <UploadUserAccessModal
                isOpen={isUserAccessModalOpen}
                onClose={() => setIsUserAccessModalOpen(false)}
                onAccessGranted={(data) => { handleUserAccessGranted(data); if (activeTab === 'users') fetchManagedUsers(); }}
                userUuid={user.uuid}
            />

            {/* Upload Student Roster Modal */}
            <UploadStudentRosterModal
                isOpen={isRosterModalOpen}
                onClose={() => setIsRosterModalOpen(false)}
                onRosterUploaded={handleRosterUploaded}
            />

            {/* Templates Hub Repository Modal */}
            <TemplatesHubModal
                isOpen={isTemplatesModalOpen}
                onClose={() => setIsTemplatesModalOpen(false)}
            />
        </div>
    );
}

function TemplatesHubModal({ isOpen, onClose }) {
    if (!isOpen) return null;

    const templates = [
        {
            title: "User Accounts & Role Access Template",
            badge: "Grant User Access",
            filename_xlsx: "sample_user_access.xlsx",
            filename_csv: "sample_user_access.csv",
            description: "Bulk grant platform credentials for Students, Mentors, Coordinators, Department Heads, and Recruiters.",
            required: ["User Email / gmail *"],
            optional: ["Role (Student, Mentor...)", "Password"]
        },
        {
            title: "Drive Results & Verdicts Template",
            badge: "Upload Excel Results",
            filename_xlsx: "sample_drive_results.xlsx",
            filename_csv: "sample_drive_results.csv",
            description: "Upload candidate evaluations with explicit statuses (Selected, Rejected, On Hold) and scores.",
            required: ["Student Gmail *", "Result Status *"],
            optional: ["Round", "Score", "Student Name"]
        },
        {
            title: "Drive Shortlist Template (Emails Only)",
            badge: "Upload Shortlist",
            filename_xlsx: "sample_drive_shortlist.xlsx",
            filename_csv: "sample_drive_shortlist.csv",
            description: "Upload shortlisted candidate emails to automatically advance them to the next interview round.",
            required: ["Student Gmail *"],
            optional: ["Student Name", "Branch"]
        },
        {
            title: "Student Academic Profiles Roster Template",
            badge: "Student Roster",
            filename_xlsx: "sample_student_roster.xlsx",
            filename_csv: "sample_student_roster.csv",
            description: "Bulk import academic records, CGPA, 10th/12th percentages, and technical skills.",
            required: ["Register Number *", "Full Name *", "Student Email *", "Department *", "CGPA *"],
            optional: ["10th Percentage", "12th Percentage", "Technical Skills"]
        },
        {
            title: "Company Placement Drives Schedule Template",
            badge: "Company Drives",
            filename_xlsx: "sample_company_drives.xlsx",
            filename_csv: "sample_company_drives.csv",
            description: "Bulk schedule on-campus placement drives with company type, CTC LPA, eligibility criteria, and rounds.",
            required: ["Company Name *", "Job Role *", "CTC LPA *"],
            optional: ["Company Type", "Required CGPA", "Allowed Branches", "Total Rounds", "Location", "Drive Date", "Status"]
        }
    ];

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-dialog large-dialog" onClick={(e) => e.stopPropagation()}>
                <div className="modal-head">
                    <div>
                        <h3>Coordinator Excel Templates Repository</h3>
                        <p className="modal-sub">Download official sample templates to verify column formats before uploading bulk files</p>
                    </div>
                    <button type="button" className="modal-close" onClick={onClose}>&times;</button>
                </div>

                <div className="templates-hub-list" style={{ marginTop: '14px' }}>
                    {templates.map((tpl, i) => (
                        <div key={i} className="tpl-item-card">
                            <div className="tpl-item-info">
                                <div className="tpl-item-title">
                                    {tpl.title}
                                    <span className="tpl-item-mode">{tpl.badge}</span>
                                </div>
                                <p className="tpl-item-desc">{tpl.description}</p>
                                <div className="template-columns-info" style={{ marginTop: '6px', marginBottom: 0 }}>
                                    {tpl.required.map((req, rIdx) => (
                                        <span key={rIdx} className="col-badge required">{req}</span>
                                    ))}
                                    {tpl.optional.map((opt, oIdx) => (
                                        <span key={oIdx} className="col-badge optional">{opt}</span>
                                    ))}
                                </div>
                            </div>

                            <div className="template-download-actions" style={{ flexDirection: 'column', minWidth: '130px' }}>
                                <a
                                    href={`/api/templates/download/${tpl.filename_xlsx}`}
                                    download={tpl.filename_xlsx}
                                    className="btn-download-tpl excel"
                                    style={{ justifyContent: 'center' }}
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                        <polyline points="7 10 12 15 17 10"></polyline>
                                        <line x1="12" y1="15" x2="12" y2="3"></line>
                                    </svg>
                                    Excel (.xlsx)
                                </a>
                                <a
                                    href={`/api/templates/download/${tpl.filename_csv}`}
                                    download={tpl.filename_csv}
                                    className="btn-download-tpl csv"
                                    style={{ justifyContent: 'center' }}
                                >
                                    CSV (.csv)
                                </a>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="modal-foot" style={{ marginTop: '16px' }}>
                    <button type="button" className="btn-submit" onClick={onClose}>
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
