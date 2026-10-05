function DepartmentDashboard({ user, onLogout }) {
    // Navigation Tabs: 'overview', 'students', 'mentors', 'interventions', 'placed'
    const [activeTab, setActiveTab] = React.useState('overview');

    // Data states
    const [deptData, setDeptData] = React.useState(null);
    const [interventions, setInterventions] = React.useState([]);
    const [loading, setLoading] = React.useState(true);

    // Filters & Search
    const [searchQuery, setSearchQuery] = React.useState('');
    const [statusFilter, setStatusFilter] = React.useState('ALL');

    // Selected Student for Slide-Over Drawer
    const [selectedStudent, setSelectedStudent] = React.useState(null);

    // Toast Notification
    const [toastMsg, setToastMsg] = React.useState('');

    const showToast = (msg) => {
        setToastMsg(msg);
        setTimeout(() => setToastMsg(''), 3500);
    };

    // Fetch Department Data from Backend API
    const fetchDepartmentData = React.useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/department/dashboard?dept=CSE');
            if (res.ok) {
                const data = await res.json();
                setDeptData(data);
            }
            const interventionRes = await fetch('/api/interventions', {
                headers: window.interventionHeaders(user)
            });
            if (interventionRes.ok) {
                const interventionData = await interventionRes.json();
                setInterventions(interventionData.interventions || []);
            } else {
                setInterventions([]);
            }
        } catch (err) {
            console.error('Failed to load department dashboard data:', err);
        } finally {
            setLoading(false);
        }
    }, [user]);

    React.useEffect(() => {
        fetchDepartmentData();
    }, [fetchDepartmentData]);

    const metrics = deptData?.metrics || {
        total_students: 0,
        placed_count: 0,
        placement_rate: 0,
        at_risk_count: 0,
        total_mentors: 0,
        avg_ctc: 0,
        highest_ctc: 0
    };

    const students = deptData?.students || [];
    const mentors = deptData?.mentors || [];
    const placedStudents = deptData?.placed_students || [];

    const updateInterventionStatus = async (interventionId, nextStatus) => {
        const res = await fetch(`/api/interventions/${interventionId}/status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', ...window.interventionHeaders(user) },
            body: JSON.stringify({ status: nextStatus })
        });
        if (res.ok) {
            setInterventions(prev => prev.map(item => item.id === interventionId ? { ...item, status: nextStatus } : item));
            showToast(`Intervention marked ${nextStatus.toLowerCase()}.`);
        } else {
            showToast('Unable to update intervention status.');
        }
    };

    // Filtered Students List
    const filteredStudents = React.useMemo(() => {
        return students.filter(s => {
            const matchesSearch = (s.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                (s.register_number || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                (s.email || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                (s.assigned_mentor || '').toLowerCase().includes(searchQuery.toLowerCase());

            const matchesStatus = statusFilter === 'ALL' ||
                (statusFilter === 'PLACED' && s.status === 'Placed') ||
                (statusFilter === 'AT_RISK' && s.status === 'At Risk') ||
                (statusFilter === 'ACTIVE' && (s.status === 'Active' || s.status === 'In Progress'));

            return matchesSearch && matchesStatus;
        });
    }, [students, searchQuery, statusFilter]);

    return (
        <div className="laptop-dashboard">
            {/* Top Navbar Header */}
            <header className="desktop-navbar">
                <div className="nav-left">
                    <div className="brand-icon" style={{ background: '#7c3aed' }}>
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ width: '20px', height: '20px', color: '#fff' }}>
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5m0 0h4m-4 0V11m0 4h4" />
                        </svg>
                    </div>
                    <div>
                        <h1 className="brand-title">Department Workspace</h1>
                        <p className="brand-subtitle">{deptData?.department?.name || 'Computer Science & Engineering'} &bull; Department Head Overview</p>
                    </div>
                </div>

                {/* Navbar Tabs */}
                <div className="nav-tabs" style={{ display: 'flex', gap: '8px' }}>
                    {[
                        { id: 'overview', label: 'Overview & Metrics' },
                        { id: 'students', label: `Dept Students (${students.length})` },
                        { id: 'mentors', label: `Mentors (${mentors.length})` },
                        { id: 'interventions', label: `Interventions (${interventions.length})` },
                        { id: 'placed', label: `Placed Gallery (${placedStudents.length})` }
                    ].map(tab => (
                        <button
                            key={tab.id}
                            type="button"
                            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(tab.id)}
                            style={{
                                padding: '8px 16px',
                                borderRadius: '6px',
                                background: activeTab === tab.id ? '#7c3aed' : 'transparent',
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

                {/* Header User Profile & Sign Out */}
                <div className="nav-right" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div className="user-profile" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div className="user-avatar" style={{ background: '#7c3aed', color: '#fff', width: '36px', height: '36px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                            D
                        </div>
                        <div className="user-info">
                            <span className="user-name" style={{ fontWeight: '600', color: '#f8fafc' }}>{user?.gmail || 'dept.cse@gmail.com'}</span>
                            <span className="user-role-badge" style={{ background: '#7c3aed', color: '#fff', fontSize: '0.75rem', padding: '2px 8px', borderRadius: '12px', marginLeft: '6px' }}>Department Head</span>
                        </div>
                    </div>
                    <button type="button" className="logout-btn" onClick={onLogout} style={{ padding: '8px 14px', borderRadius: '6px', background: '#334155', color: '#f8fafc', border: 'none', cursor: 'pointer' }}>
                        Sign Out
                    </button>
                </div>
            </header>

            {/* Toast Notification */}
            {toastMsg && (
                <div style={{ position: 'fixed', bottom: '24px', right: '24px', zIndex: 1000, background: '#7c3aed', color: '#fff', padding: '12px 20px', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.3)', fontWeight: '600' }}>
                    {toastMsg}
                </div>
            )}

            {/* MAIN DASHBOARD CONTENT */}
            <main className="dashboard-body" style={{ marginTop: '20px' }}>
                {loading ? (
                    <div style={{ color: '#94a3b8', padding: '40px', textAlign: 'center' }}>
                        <p>Loading Department Workspace...</p>
                    </div>
                ) : (
                    <>
                        {/* TAB 1: OVERVIEW & METRICS */}
                        {activeTab === 'overview' && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                                {/* Top KPI Metric Cards */}
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                                    <div style={{ background: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                        <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Total Dept Students</span>
                                        <h3 style={{ fontSize: '2rem', color: '#f8fafc', marginTop: '6px' }}>{metrics.total_students}</h3>
                                        <p style={{ color: '#60a5fa', fontSize: '0.75rem', marginTop: '4px' }}>Active Batch Enrolled</p>
                                    </div>

                                    <div style={{ background: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                        <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Placement Rate</span>
                                        <h3 style={{ fontSize: '2rem', color: '#34d399', marginTop: '6px' }}>{metrics.placement_rate}%</h3>
                                        <p style={{ color: '#34d399', fontSize: '0.75rem', marginTop: '4px' }}>{metrics.placed_count} Placed Candidates</p>
                                    </div>

                                    <div style={{ background: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                        <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Department Mentors</span>
                                        <h3 style={{ fontSize: '2rem', color: '#a78bfa', marginTop: '6px' }}>{metrics.total_mentors}</h3>
                                        <p style={{ color: '#a78bfa', fontSize: '0.75rem', marginTop: '4px' }}>Active Faculty Supervisors</p>
                                    </div>

                                    <div style={{ background: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                        <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Average CTC Package</span>
                                        <h3 style={{ fontSize: '2rem', color: '#38bdf8', marginTop: '6px' }}>₹{metrics.avg_ctc} LPA</h3>
                                        <p style={{ color: '#38bdf8', fontSize: '0.75rem', marginTop: '4px' }}>Highest: ₹{metrics.highest_ctc} LPA</p>
                                    </div>

                                    <div style={{ background: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                        <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Students Needing Focus</span>
                                        <h3 style={{ fontSize: '2rem', color: '#f87171', marginTop: '6px' }}>{metrics.at_risk_count}</h3>
                                        <p style={{ color: '#f87171', fontSize: '0.75rem', marginTop: '4px' }}>Active Interventions Flagged</p>
                                    </div>
                                </div>

                                {/* Placement Progress Bar */}
                                <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px', color: '#f8fafc' }}>
                                        <h4 style={{ fontSize: '1.05rem' }}>Batch Placement Progress</h4>
                                        <span style={{ color: '#34d399', fontWeight: 'bold' }}>{metrics.placed_count} / {metrics.total_students} Placed ({metrics.placement_rate}%)</span>
                                    </div>
                                    <div style={{ width: '100%', height: '12px', background: '#0f172a', borderRadius: '6px', overflow: 'hidden' }}>
                                        <div style={{ width: `${metrics.placement_rate}%`, height: '100%', background: 'linear-gradient(90deg, #7c3aed, #34d399)', borderRadius: '6px', transition: 'width 0.5s ease-in-out' }}></div>
                                    </div>
                                </div>

                                {/* Quick Summary Grids */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                                    {/* Faculty Mentors Overview */}
                                    <div className="card" style={{ background: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                        <h4 style={{ color: '#f8fafc', fontSize: '1.1rem', marginBottom: '16px' }}>Department Faculty Mentors</h4>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                            {mentors.map(m => (
                                                <div key={m.id} style={{ background: '#0f172a', padding: '14px', borderRadius: '8px', border: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <div>
                                                        <h5 style={{ color: '#f8fafc', fontSize: '0.95rem', fontWeight: 'bold' }}>{m.name}</h5>
                                                        <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{m.specialization}</p>
                                                    </div>
                                                    <div style={{ textAlign: 'right' }}>
                                                        <span style={{ background: 'rgba(124,58,237,0.2)', color: '#c4b5fd', padding: '4px 10px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 'bold' }}>
                                                            {m.assigned_mentees} Mentees ({m.placed_mentees} Placed)
                                                        </span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Recent Interventions Overview */}
                                    <div className="card" style={{ background: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                        <h4 style={{ color: '#f8fafc', fontSize: '1.1rem', marginBottom: '16px' }}>Active Department Interventions</h4>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                            {interventions.map(inv => (
                                                <div key={inv.id} style={{ background: '#0f172a', padding: '14px', borderRadius: '8px', border: '1px solid #334155' }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                                        <h5 style={{ color: '#f8fafc', fontSize: '0.95rem', fontWeight: 'bold' }}>{inv.title}</h5>
                                                        <span style={{ background: inv.status === 'APPROVED' ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)', color: inv.status === 'APPROVED' ? '#34d399' : '#f59e0b', padding: '2px 8px', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 'bold' }}>
                                                            {inv.status}
                                                        </span>
                                                    </div>
                                                    <p style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '6px' }}>
                                                        Student: <strong style={{ color: '#f8fafc' }}>{inv.student_gmail}</strong>
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* TAB 2: DEPARTMENT STUDENTS TABLE */}
                        {activeTab === 'students' && (
                            <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
                                    <div>
                                        <h3 style={{ color: '#f8fafc', fontSize: '1.25rem' }}>Department Students Directory</h3>
                                        <p style={{ color: '#94a3b8', fontSize: '0.875rem' }}>Complete student roster for {deptData?.department?.name || 'CSE'}</p>
                                    </div>

                                    {/* Search & Status Filters */}
                                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                                        <input
                                            type="text"
                                            placeholder="Search student, reg no, mentor..."
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                            style={{ padding: '8px 14px', borderRadius: '6px', background: '#0f172a', border: '1px solid #334155', color: '#f8fafc', fontSize: '0.875rem', width: '240px' }}
                                        />
                                        <select
                                            value={statusFilter}
                                            onChange={(e) => setStatusFilter(e.target.value)}
                                            style={{ padding: '8px 14px', borderRadius: '6px', background: '#0f172a', border: '1px solid #334155', color: '#f8fafc', fontSize: '0.875rem' }}
                                        >
                                            <option value="ALL">All Statuses</option>
                                            <option value="PLACED">Placed Only</option>
                                            <option value="AT_RISK">At Risk Only</option>
                                            <option value="ACTIVE">Active / In Progress</option>
                                        </select>
                                    </div>
                                </div>

                                <div style={{ overflowX: 'auto' }}>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                        <thead>
                                            <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', fontSize: '0.85rem' }}>
                                                <th style={{ padding: '12px' }}>STUDENT NAME</th>
                                                <th style={{ padding: '12px' }}>REG NUMBER</th>
                                                <th style={{ padding: '12px' }}>CGPA</th>
                                                <th style={{ padding: '12px' }}>STATUS</th>
                                                <th style={{ padding: '12px' }}>OFFER / COMPANY</th>
                                                <th style={{ padding: '12px' }}>ASSIGNED MENTOR</th>
                                                <th style={{ padding: '12px', textAlign: 'right' }}>ACTION</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredStudents.length === 0 ? (
                                                <tr>
                                                    <td colSpan="7" style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>No students found matching filters.</td>
                                                </tr>
                                            ) : (
                                                filteredStudents.map(st => (
                                                    <tr key={st.student_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#f8fafc' }}>
                                                        <td style={{ padding: '12px' }}>
                                                            <div style={{ fontWeight: 'bold' }}>{st.name}</div>
                                                            <div style={{ color: '#94a3b8', fontSize: '0.75rem' }}>{st.email}</div>
                                                        </td>
                                                        <td style={{ padding: '12px', color: '#94a3b8', fontSize: '0.85rem' }}>{st.register_number}</td>
                                                        <td style={{ padding: '12px', color: '#34d399', fontWeight: 'bold' }}>{st.cgpa}</td>
                                                        <td style={{ padding: '12px' }}>
                                                            <span style={{
                                                                padding: '4px 10px',
                                                                borderRadius: '12px',
                                                                fontSize: '0.75rem',
                                                                fontWeight: 'bold',
                                                                background: st.status === 'Placed' ? 'rgba(16,185,129,0.2)' : st.status === 'At Risk' ? 'rgba(239,68,68,0.2)' : 'rgba(59,130,246,0.2)',
                                                                color: st.status === 'Placed' ? '#34d399' : st.status === 'At Risk' ? '#f87171' : '#60a5fa'
                                                            }}>
                                                                {st.status}
                                                            </span>
                                                        </td>
                                                        <td style={{ padding: '12px' }}>
                                                            {st.company ? (
                                                                <div>
                                                                    <span style={{ fontWeight: 'bold', color: '#fff' }}>{st.company}</span>
                                                                    <span style={{ color: '#34d399', fontWeight: 'bold', fontSize: '0.8rem', marginLeft: '6px' }}>₹{st.ctc} LPA</span>
                                                                </div>
                                                            ) : (
                                                                <span style={{ color: '#64748b', fontSize: '0.8rem' }}>Searching</span>
                                                            )}
                                                        </td>
                                                        <td style={{ padding: '12px', color: '#cbd5e1', fontSize: '0.85rem' }}>{st.assigned_mentor}</td>
                                                        <td style={{ padding: '12px', textAlign: 'right' }}>
                                                            <button
                                                                type="button"
                                                                onClick={() => setSelectedStudent(st)}
                                                                style={{ padding: '6px 12px', borderRadius: '6px', background: '#334155', color: '#f8fafc', border: 'none', cursor: 'pointer', fontSize: '0.8rem', fontWeight: '600' }}
                                                            >
                                                                View Details &rarr;
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* TAB 3: DEPARTMENT MENTORS */}
                        {activeTab === 'mentors' && (
                            <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                                <h3 style={{ color: '#f8fafc', fontSize: '1.25rem', marginBottom: '8px' }}>Department Faculty Mentors</h3>
                                <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '20px' }}>Supervising mentors assigned to students in {deptData?.department?.name || 'CSE'}</p>

                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
                                    {mentors.map(m => (
                                        <div key={m.id} style={{ background: '#0f172a', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
                                                <div style={{ background: '#7c3aed', color: '#fff', width: '42px', height: '42px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '1.1rem' }}>
                                                    {m.name[0]}
                                                </div>
                                                <div>
                                                    <h4 style={{ color: '#f8fafc', fontSize: '1.05rem', fontWeight: 'bold' }}>{m.name}</h4>
                                                    <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{m.email}</p>
                                                </div>
                                            </div>

                                            <div style={{ background: '#1e293b', padding: '12px', borderRadius: '6px', border: '1px solid #334155', marginBottom: '14px' }}>
                                                <span style={{ color: '#94a3b8', fontSize: '0.75rem', display: 'block' }}>SPECIALIZATION</span>
                                                <span style={{ color: '#a78bfa', fontWeight: 'bold', fontSize: '0.85rem' }}>{m.specialization}</span>
                                            </div>

                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', textAlign: 'center' }}>
                                                <div style={{ background: '#1e293b', padding: '10px', borderRadius: '6px' }}>
                                                    <span style={{ color: '#94a3b8', fontSize: '0.75rem', display: 'block' }}>Assigned Mentees</span>
                                                    <strong style={{ color: '#fff', fontSize: '1.1rem' }}>{m.assigned_mentees}</strong>
                                                </div>
                                                <div style={{ background: '#1e293b', padding: '10px', borderRadius: '6px' }}>
                                                    <span style={{ color: '#94a3b8', fontSize: '0.75rem', display: 'block' }}>Placed Mentees</span>
                                                    <strong style={{ color: '#34d399', fontSize: '1.1rem' }}>{m.placed_mentees}</strong>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* TAB 4: INTERVENTIONS */}
                        {activeTab === 'interventions' && (
                            <InterventionRoster
                                user={user}
                                canGenerate={true}
                                title="Department Student Interventions"
                                description="Expand a department student to inspect their intervention and action plan."
                            />
                        )}

                        {/* TAB 5: PLACED GALLERY */}
                        {activeTab === 'placed' && (
                            <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                                <h3 style={{ color: '#f8fafc', fontSize: '1.25rem', marginBottom: '8px' }}>Department Placed Students Hall of Fame</h3>
                                <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '20px' }}>Celebrating successful campus selections from {deptData?.department?.name || 'CSE'}</p>

                                {placedStudents.length === 0 ? (
                                    <p style={{ color: '#64748b' }}>No students placed yet in this batch.</p>
                                ) : (
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
                                        {placedStudents.map(st => (
                                            <div key={st.student_id} style={{ background: '#0f172a', padding: '18px', borderRadius: '10px', border: '1px solid #334155' }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                                    <div>
                                                        <h4 style={{ color: '#f8fafc', fontSize: '1.05rem', fontWeight: 'bold' }}>{st.name}</h4>
                                                        <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{st.register_number}</p>
                                                    </div>
                                                    <span style={{ background: 'rgba(16,185,129,0.2)', color: '#34d399', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 'bold' }}>
                                                        PLACED
                                                    </span>
                                                </div>

                                                <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                                                    <div style={{ color: '#60a5fa', fontWeight: 'bold', fontSize: '0.95rem' }}>{st.company}</div>
                                                    <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Role: {st.job_role || 'Software Engineer'}</p>
                                                    <p style={{ color: '#34d399', fontWeight: 'bold', fontSize: '1.05rem', marginTop: '4px' }}>₹{st.ctc} LPA</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </>
                )}
            </main>

            {/* STUDENT DETAIL SLIDE-OVER DRAWER */}
            {selectedStudent && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', zIndex: 1100, display: 'flex', justifyContent: 'flex-end' }}>
                    <div style={{ width: '480px', maxWidth: '100%', background: '#0f172a', borderLeft: '1px solid #334155', padding: '24px', height: '100%', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #334155', paddingBottom: '14px' }}>
                            <div>
                                <h3 style={{ color: '#f8fafc', fontSize: '1.2rem', fontWeight: 'bold' }}>{selectedStudent.name}</h3>
                                <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{selectedStudent.register_number} &bull; {selectedStudent.department}</p>
                            </div>
                            <button
                                type="button"
                                onClick={() => setSelectedStudent(null)}
                                style={{ background: '#1e293b', border: '1px solid #334155', color: '#f8fafc', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer' }}
                            >
                                Close &times;
                            </button>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
                                <h4 style={{ color: '#a78bfa', fontSize: '0.9rem', marginBottom: '8px' }}>Academic Overview</h4>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', color: '#cbd5e1', fontSize: '0.85rem' }}>
                                    <div>CGPA: <strong style={{ color: '#34d399' }}>{selectedStudent.cgpa}</strong></div>
                                    <div>10th %: <strong style={{ color: '#fff' }}>{selectedStudent.tenth}%</strong></div>
                                    <div>12th %: <strong style={{ color: '#fff' }}>{selectedStudent.twelfth}%</strong></div>
                                    <div>Status: <strong style={{ color: selectedStudent.status === 'Placed' ? '#34d399' : '#f87171' }}>{selectedStudent.status}</strong></div>
                                </div>
                            </div>

                            <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
                                <h4 style={{ color: '#a78bfa', fontSize: '0.9rem', marginBottom: '8px' }}>Assigned Supervisor</h4>
                                <p style={{ color: '#f8fafc', fontSize: '0.9rem', fontWeight: 'bold' }}>{selectedStudent.assigned_mentor}</p>
                                <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Email: {selectedStudent.email}</p>
                            </div>

                            {selectedStudent.company && (
                                <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #10b981' }}>
                                    <h4 style={{ color: '#34d399', fontSize: '0.9rem', marginBottom: '6px' }}>Placed Offer Details</h4>
                                    <p style={{ color: '#fff', fontWeight: 'bold', fontSize: '1rem' }}>{selectedStudent.company}</p>
                                    <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Role: {selectedStudent.job_role}</p>
                                    <p style={{ color: '#34d399', fontWeight: 'bold', fontSize: '1.1rem', marginTop: '4px' }}>₹{selectedStudent.ctc} LPA</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
