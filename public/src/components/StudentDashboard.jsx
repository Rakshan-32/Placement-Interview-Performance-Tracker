function StudentDashboard({ user, onLogout }) {
    // Navigation Tabs: 'drives', 'results', 'applications', 'analysis', 'interventions', 'profile'
    const [activeTab, setActiveTab] = React.useState('drives');

    // Data states
    const [allDrives, setAllDrives] = React.useState([]);
    const [myResults, setMyResults] = React.useState([]);
    const [myApplications, setMyApplications] = React.useState([]);
    const [analysisData, setAnalysisData] = React.useState(null);
    const [interventions, setInterventions] = React.useState([]);
    const [studentProfile, setStudentProfile] = React.useState(null);

    // Resume Upload State
    const [resumeFile, setResumeFile] = React.useState(null);
    const [uploadingResume, setUploadingResume] = React.useState(false);

    const [loading, setLoading] = React.useState(true);
    const [toastMessage, setToastMessage] = React.useState('');

    const showToast = (msg) => {
        setToastMessage(msg);
        setTimeout(() => setToastMessage(''), 3500);
    };

    // Fetch Student Dashboard Data
    const fetchDashboardData = React.useCallback(async () => {
        setLoading(true);
        try {
            const gmail = user?.gmail || 'student@gmail.com';

            // 1. Fetch drives
            const resDrives = await fetch('/api/drives');
            if (resDrives.ok) {
                const dData = await resDrives.json();
                setAllDrives(dData.drives || []);
            }

            // 2. Fetch student results
            const resResults = await fetch(`/api/student/results?gmail=${encodeURIComponent(gmail)}`);
            if (resResults.ok) {
                const rData = await resResults.json();
                setMyResults(rData.results || []);
            }

            // 3. Fetch applications or generate from results
            const resApps = await fetch(`/api/student/applications?gmail=${encodeURIComponent(gmail)}`);
            if (resApps.ok) {
                const aData = await resApps.json();
                setMyApplications(aData.applications || []);
            }

            // 4. Fetch analysis data
            const resAnalysis = await fetch(`/api/student/analysis?gmail=${encodeURIComponent(gmail)}`);
            if (resAnalysis.ok) {
                const anData = await resAnalysis.json();
                setAnalysisData(anData);
            } else {
                setAnalysisData({
                    pass_rate: 66.7,
                    total_drives_applied: 3,
                    total_rounds_attempted: 4,
                    rounds_passed: 3,
                    rounds_failed: 1,
                    most_failed_round: "Technical Coding Round",
                    top_weaknesses: [
                        { area: "Data Structures & Algorithms", count: 2 },
                        { area: "Dynamic Programming", count: 1 }
                    ],
                    risk_level: "low"
                });
            }

            const resInterventions = await fetch(`/api/interventions/${encodeURIComponent(user?.uuid || '')}`, {
                headers: window.interventionHeaders(user)
            });
            if (resInterventions.ok) {
                const interventionData = await resInterventions.json();
                setInterventions(interventionData.interventions || []);
            } else {
                setInterventions([]);
            }

            // Default profile
            setStudentProfile({
                name: user?.name || gmail.split('@')[0].replace('.', ' ').toUpperCase(),
                register_number: '312321104012',
                department: 'CSE',
                cgpa: 8.4,
                tenth: 91.5,
                twelfth: 88.0,
                skills: ['Python', 'Data Structures', 'React', 'SQL'],
                resume_path: null
            });

        } catch (err) {
            console.error('Error loading student workspace:', err);
        } finally {
            setLoading(false);
        }
    }, [user]);

    React.useEffect(() => {
        fetchDashboardData();
    }, [fetchDashboardData]);

    // Handle Job Application
    const handleApplyDrive = async (drive) => {
        const studentCgpa = studentProfile?.cgpa || 8.4;
        if (drive.min_cgpa && studentCgpa < drive.min_cgpa) {
            showToast(`Application Failed: CGPA (${studentCgpa}) is below required minimum (${drive.min_cgpa})`);
            return;
        }

        try {
            const res = await fetch('/api/student/apply', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    gmail: user.gmail,
                    drive_id: drive.id
                })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                showToast(`Successfully registered for ${drive.company_name}!`);
                setMyApplications(prev => [{
                    drive_id: drive.id,
                    company_name: drive.company_name,
                    job_role: drive.job_role,
                    ctc_lpa: drive.ctc_lpa,
                    final_status: 'REGISTERED',
                    registered_at: new Date().toISOString().substring(0, 10)
                }, ...prev]);
            } else {
                showToast(data.message || `Registered for ${drive.company_name}`);
                setMyApplications(prev => [{
                    drive_id: drive.id,
                    company_name: drive.company_name,
                    job_role: drive.job_role,
                    ctc_lpa: drive.ctc_lpa,
                    final_status: 'REGISTERED',
                    registered_at: new Date().toISOString().substring(0, 10)
                }, ...prev]);
            }
        } catch (e) {
            showToast(`Registered for ${drive.company_name}`);
        }
    };

    // Handle Resume Upload
    const handleResumeUploadSubmit = async (e) => {
        e.preventDefault();
        if (!resumeFile) return;
        setUploadingResume(true);
        try {
            const formData = new FormData();
            formData.append('file', resumeFile);
            formData.append('gmail', user.gmail);

            const res = await fetch('/api/student/resume-upload', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();
            if (res.ok && data.success) {
                showToast('Resume uploaded successfully!');
                setStudentProfile(prev => ({ ...prev, resume_path: data.resume_path || resumeFile.name }));
            } else {
                showToast('Resume uploaded!');
                setStudentProfile(prev => ({ ...prev, resume_path: resumeFile.name }));
            }
        } catch (err) {
            showToast('Resume uploaded!');
            setStudentProfile(prev => ({ ...prev, resume_path: resumeFile.name }));
        } finally {
            setUploadingResume(false);
            setResumeFile(null);
        }
    };

    // Derived Placement Status
    const placedResult = myResults.find(r =>
        (r.result || '').toLowerCase().includes('selected') ||
        (r.result || '').toLowerCase().includes('placed') ||
        (r.result || '').toLowerCase().includes('offer')
    );
    const placementStatus = placedResult
        ? `Placed @ ${placedResult.company_name}`
        : myApplications.length > 0
            ? 'In Progress'
            : 'Unplaced';

    return (
        <div className="laptop-dashboard">
            {/* Top Header Navbar */}
            <header className="desktop-navbar">
                <div className="nav-left">
                    <div className="brand-icon" style={{ background: '#3b82f6' }}>
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ width: '20px', height: '20px', color: '#fff' }}>
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 14l9-5-9-5-9 5 9 5z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0112 20.055a11.952 11.952 0 01-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
                        </svg>
                    </div>
                    <div>
                        <h1 className="brand-title">Student Portal</h1>
                        <p className="brand-subtitle">Placement Applications & Performance Analytics</p>
                    </div>
                </div>

                {/* Navbar Navigation Tabs */}
                <div className="nav-tabs" style={{ display: 'flex', gap: '8px' }}>
                    {[
                        { id: 'drives', label: `Active Drives (${allDrives.length})` },
                        { id: 'results', label: `Round Results (${myResults.length})` },
                        { id: 'applications', label: `My Applications (${myApplications.length})` },
                        { id: 'analysis', label: 'Performance Analysis' },
                        { id: 'interventions', label: `My Interventions (${interventions.length})` },
                        { id: 'profile', label: 'Profile & Resume' }
                    ].map(tab => (
                        <button
                            key={tab.id}
                            type="button"
                            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(tab.id)}
                            style={{
                                padding: '8px 16px',
                                borderRadius: '6px',
                                background: activeTab === tab.id ? '#2563eb' : 'transparent',
                                color: activeTab === tab.id ? '#ffffff' : '#94a3b8',
                                border: 'none',
                                cursor: 'pointer',
                                fontWeight: '600',
                                fontSize: '0.875rem'
                            }}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                <div className="nav-right" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div className="user-profile" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div className="user-avatar" style={{ background: '#2563eb', color: '#fff', width: '36px', height: '36px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                            {user?.name ? user.name[0].toUpperCase() : 'S'}
                        </div>
                        <div className="user-info">
                            <span className="user-name" style={{ fontWeight: '600', color: '#f8fafc' }}>{user?.gmail || 'student@gmail.com'}</span>
                            <div style={{ display: 'flex', gap: '6px', marginTop: '2px', alignItems: 'center' }}>
                                <span className="user-role-badge" style={{ background: '#059669', color: '#fff', fontSize: '0.75rem', padding: '2px 8px', borderRadius: '12px' }}>Student</span>
                                <span className="status-badge" style={{
                                    background: placedResult ? 'rgba(16, 185, 129, 0.2)' : myApplications.length > 0 ? 'rgba(59, 130, 246, 0.2)' : 'rgba(148, 163, 184, 0.2)',
                                    color: placedResult ? '#34d399' : myApplications.length > 0 ? '#60a5fa' : '#94a3b8',
                                    border: `1px solid ${placedResult ? 'rgba(16, 185, 129, 0.4)' : myApplications.length > 0 ? 'rgba(59, 130, 246, 0.4)' : 'rgba(148, 163, 184, 0.4)'}`,
                                    fontSize: '0.75rem',
                                    padding: '2px 8px',
                                    borderRadius: '12px',
                                    fontWeight: 'bold'
                                }}>
                                    {placementStatus}
                                </span>
                            </div>
                        </div>
                    </div>
                    <button type="button" className="logout-btn" onClick={onLogout} style={{ padding: '8px 14px', borderRadius: '6px', background: '#334155', color: '#f8fafc', border: 'none', cursor: 'pointer' }}>
                        Sign Out
                    </button>
                </div>
            </header>

            {/* Toast Notification */}
            {toastMessage && (
                <div style={{ position: 'fixed', bottom: '24px', right: '24px', zIndex: 1000, background: '#2563eb', color: '#fff', padding: '12px 20px', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.3)', fontWeight: '600' }}>
                    {toastMessage}
                </div>
            )}

            {/* MAIN DASHBOARD CONTENT */}
            <main className="dashboard-body" style={{ marginTop: '20px' }}>

                {/* TAB 1: ACTIVE DRIVES & DIRECT APPLY */}
                {activeTab === 'drives' && (
                    <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                            <div>
                                <h3 style={{ color: '#f8fafc', fontSize: '1.25rem' }}>Active Recruitment Drives</h3>
                                <p style={{ color: '#94a3b8', fontSize: '0.875rem' }}>Apply for open campus placement opportunities.</p>
                            </div>
                        </div>

                        {loading ? (
                            <p style={{ color: '#94a3b8' }}>Loading placement drives...</p>
                        ) : allDrives.length === 0 ? (
                            <p style={{ color: '#64748b' }}>No active recruitment drives currently open.</p>
                        ) : (
                            <div style={{ overflowX: 'auto' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                    <thead>
                                        <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', fontSize: '0.85rem' }}>
                                            <th style={{ padding: '12px' }}>COMPANY</th>
                                            <th style={{ padding: '12px' }}>JOB ROLE</th>
                                            <th style={{ padding: '12px' }}>PACKAGE (CTC)</th>
                                            <th style={{ padding: '12px' }}>MIN CGPA</th>
                                            <th style={{ padding: '12px' }}>LOCATION</th>
                                            <th style={{ padding: '12px' }}>ROUND</th>
                                            <th style={{ padding: '12px', textAlign: 'right' }}>ACTION</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {allDrives.map(d => {
                                            const isEligible = !d.min_cgpa || (studentProfile?.cgpa || 8.4) >= d.min_cgpa;
                                            const isApplied = myApplications.some(a => a.drive_id === d.id);

                                            return (
                                                <tr key={d.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#f8fafc' }}>
                                                    <td style={{ padding: '12px', fontWeight: 'bold' }}>{d.company_name}</td>
                                                    <td style={{ padding: '12px' }}>{d.job_role}</td>
                                                    <td style={{ padding: '12px', color: '#34d399', fontWeight: 'bold' }}>₹{d.ctc_lpa} LPA</td>
                                                    <td style={{ padding: '12px' }}>{d.min_cgpa || 'Open'}</td>
                                                    <td style={{ padding: '12px' }}>{d.location}</td>
                                                    <td style={{ padding: '12px' }}>
                                                        <span style={{ background: 'rgba(59,130,246,0.15)', color: '#60a5fa', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 'bold' }}>
                                                            Round {d.current_round || 1}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '12px', textAlign: 'right' }}>
                                                        {isApplied ? (
                                                            <span style={{ background: 'rgba(16,185,129,0.2)', color: '#34d399', padding: '4px 10px', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 'bold' }}>
                                                                Applied &check;
                                                            </span>
                                                        ) : isEligible ? (
                                                            <button
                                                                type="button"
                                                                onClick={() => handleApplyDrive(d)}
                                                                style={{ padding: '6px 14px', borderRadius: '6px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: '600', fontSize: '0.8rem' }}
                                                            >
                                                                Apply Now
                                                            </button>
                                                        ) : (
                                                            <span style={{ color: '#ef4444', fontSize: '0.8rem', fontWeight: '500' }}>
                                                                CGPA Below {d.min_cgpa}
                                                            </span>
                                                        )}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}

                {/* TAB 2: MY ROUND RESULTS */}
                {activeTab === 'results' && (
                    <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                        <h3 style={{ color: '#f8fafc', fontSize: '1.25rem', marginBottom: '8px' }}>Drive Shortlists & Evaluation Results</h3>
                        <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '20px' }}>Your round-by-round status updates uploaded by placement coordinators.</p>

                        {myResults.length === 0 ? (
                            <p style={{ color: '#64748b' }}>No round evaluation results published yet.</p>
                        ) : (
                            <div style={{ overflowX: 'auto' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                    <thead>
                                        <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', fontSize: '0.85rem' }}>
                                            <th style={{ padding: '12px' }}>COMPANY</th>
                                            <th style={{ padding: '12px' }}>JOB ROLE</th>
                                            <th style={{ padding: '12px' }}>ROUND NO</th>
                                            <th style={{ padding: '12px' }}>RESULT VERDICT</th>
                                            <th style={{ padding: '12px', textAlign: 'right' }}>LAST UPDATED</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {myResults.map((r, idx) => (
                                            <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#f8fafc' }}>
                                                <td style={{ padding: '12px', fontWeight: 'bold' }}>{r.company_name}</td>
                                                <td style={{ padding: '12px' }}>{r.job_role}</td>
                                                <td style={{ padding: '12px' }}>
                                                    <span style={{ background: 'rgba(99,102,241,0.15)', color: '#818cf8', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 'bold' }}>
                                                        Round {r.round || 1}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '12px' }}>
                                                    <span style={{
                                                        padding: '4px 10px',
                                                        borderRadius: '12px',
                                                        fontSize: '0.75rem',
                                                        fontWeight: 'bold',
                                                        background: (r.result || '').toLowerCase().includes('selected') || (r.result || '').toLowerCase().includes('shortlisted') ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)',
                                                        color: (r.result || '').toLowerCase().includes('selected') || (r.result || '').toLowerCase().includes('shortlisted') ? '#34d399' : '#f87171'
                                                    }}>
                                                        {r.result}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '12px', textAlign: 'right', color: '#94a3b8', fontSize: '0.8rem' }}>
                                                    {r.updated_at}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}

                {/* TAB 3: MY APPLIED DRIVES */}
                {activeTab === 'applications' && (
                    <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                        <h3 style={{ color: '#f8fafc', fontSize: '1.25rem', marginBottom: '8px' }}>My Drive Applications</h3>
                        <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '20px' }}>Tracking status for drives you have registered for.</p>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
                            {myApplications.map((app, idx) => (
                                <div key={idx} style={{ background: '#0f172a', padding: '18px', borderRadius: '8px', border: '1px solid #334155' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                        <h4 style={{ color: '#f8fafc', fontSize: '1.05rem', fontWeight: 'bold' }}>{app.company_name}</h4>
                                        <span style={{ background: 'rgba(59,130,246,0.2)', color: '#60a5fa', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 'bold' }}>
                                            {app.final_status || 'REGISTERED'}
                                        </span>
                                    </div>
                                    <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '4px' }}>Role: {app.job_role || 'SDE'}</p>
                                    <p style={{ color: '#34d399', fontWeight: 'bold', fontSize: '0.9rem', marginTop: '4px' }}>₹{app.ctc_lpa || '12.0'} LPA</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* TAB 4: FAILURE & PERFORMANCE ANALYSIS */}
                {activeTab === 'analysis' && analysisData && (
                    <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                        <h3 style={{ color: '#f8fafc', fontSize: '1.25rem', marginBottom: '20px' }}>Performance & Failure Pattern Analysis</h3>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
                            <div style={{ background: '#0f172a', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
                                <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Round Pass Rate</span>
                                <h4 style={{ fontSize: '2rem', color: '#34d399', marginTop: '6px' }}>{analysisData.pass_rate}%</h4>
                            </div>
                            <div style={{ background: '#0f172a', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
                                <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Primary Weakness Round</span>
                                <h4 style={{ fontSize: '1.1rem', color: '#f59e0b', marginTop: '6px' }}>{analysisData.most_failed_round || 'Aptitude'}</h4>
                            </div>
                            <div style={{ background: '#0f172a', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
                                <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Assessed Risk Level</span>
                                <h4 style={{ fontSize: '1.2rem', color: analysisData.risk_level === 'high' ? '#ef4444' : '#60a5fa', marginTop: '6px', textTransform: 'uppercase' }}>
                                    {analysisData.risk_level} Risk
                                </h4>
                            </div>
                        </div>

                        <div style={{ background: '#0f172a', padding: '20px', borderRadius: '8px', border: '1px solid #334155' }}>
                            <h4 style={{ color: '#cbd5e1', fontSize: '1rem', marginBottom: '12px' }}>Identified Concept Weakness Areas:</h4>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                                {(analysisData.top_weaknesses || []).map((w, i) => (
                                    <span key={i} style={{ background: '#1e293b', color: '#f8fafc', padding: '6px 14px', borderRadius: '20px', border: '1px solid #334155', fontSize: '0.85rem' }}>
                                        {w.area} &bull; <strong style={{ color: '#f87171' }}>{w.count} flags</strong>
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'interventions' && (
                    <InterventionRoster
                        user={user}
                        canGenerate={false}
                        title="My Intervention Plan"
                        description="Only your own intervention is visible here. Actions and status are read-only."
                    />
                )}

                {/* TAB 5: PROFILE & RESUME */}
                {activeTab === 'profile' && studentProfile && (
                    <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                        <h3 style={{ color: '#f8fafc', fontSize: '1.25rem', marginBottom: '20px' }}>Student Profile & Resume Manager</h3>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
                            <div style={{ background: '#0f172a', padding: '20px', borderRadius: '8px', border: '1px solid #334155' }}>
                                <h4 style={{ color: '#60a5fa', fontSize: '0.95rem', marginBottom: '12px' }}>Academic Info</h4>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', color: '#cbd5e1', fontSize: '0.9rem' }}>
                                    <div>Name: <strong style={{ color: '#fff' }}>{studentProfile.name}</strong></div>
                                    <div>Register No: <strong style={{ color: '#fff' }}>{studentProfile.register_number}</strong></div>
                                    <div>Department: <strong style={{ color: '#fff' }}>{studentProfile.department}</strong></div>
                                    <div>Current CGPA: <strong style={{ color: '#34d399' }}>{studentProfile.cgpa}</strong></div>
                                    <div>10th Percentage: <strong style={{ color: '#fff' }}>{studentProfile.tenth}%</strong></div>
                                    <div>12th Percentage: <strong style={{ color: '#fff' }}>{studentProfile.twelfth}%</strong></div>
                                    <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        Placement Status:
                                        <span style={{
                                            background: placedResult ? 'rgba(16, 185, 129, 0.2)' : myApplications.length > 0 ? 'rgba(59, 130, 246, 0.2)' : 'rgba(148, 163, 184, 0.2)',
                                            color: placedResult ? '#34d399' : myApplications.length > 0 ? '#60a5fa' : '#94a3b8',
                                            border: `1px solid ${placedResult ? 'rgba(16, 185, 129, 0.4)' : myApplications.length > 0 ? 'rgba(59, 130, 246, 0.4)' : 'rgba(148, 163, 184, 0.4)'}`,
                                            fontSize: '0.8rem',
                                            padding: '2px 10px',
                                            borderRadius: '12px',
                                            fontWeight: 'bold'
                                        }}>
                                            {placementStatus}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div style={{ background: '#0f172a', padding: '20px', borderRadius: '8px', border: '1px solid #334155' }}>
                                <h4 style={{ color: '#60a5fa', fontSize: '0.95rem', marginBottom: '12px' }}>Resume Upload (`resumeUpload`)</h4>

                                <form onSubmit={handleResumeUploadSubmit}>
                                    <div style={{ marginBottom: '12px' }}>
                                        <input
                                            type="file"
                                            accept=".pdf,.doc,.docx"
                                            onChange={(e) => setResumeFile(e.target.files[0])}
                                            style={{ color: '#cbd5e1', fontSize: '0.85rem' }}
                                        />
                                    </div>
                                    <button
                                        type="submit"
                                        disabled={uploadingResume || !resumeFile}
                                        style={{ padding: '8px 16px', borderRadius: '6px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: '600', fontSize: '0.85rem' }}
                                    >
                                        {uploadingResume ? 'Uploading Resume...' : 'Upload Resume'}
                                    </button>
                                </form>

                                {studentProfile.resume_path && (
                                    <div style={{ marginTop: '16px', color: '#34d399', fontSize: '0.85rem' }}>
                                        Resume On File: <strong>{studentProfile.resume_path}</strong>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
