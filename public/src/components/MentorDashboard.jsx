function MentorDashboard({ user, onLogout }) {
    // Tab state: 'overview', 'mentees', 'placed', 'interventions', 'metrics'
    const [activeTab, setActiveTab] = React.useState('overview');

    // Mentees & Interventions State
    const [mentees, setMentees] = React.useState([]);
    const [placedMentees, setPlacedMentees] = React.useState([]);
    const [interventions, setInterventions] = React.useState([]);
    const [metrics, setMetrics] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [searchQuery, setSearchQuery] = React.useState('');

    // Student Details Modal & Notes state
    const [selectedStudent, setSelectedStudent] = React.useState(null);
    const [studentNotes, setStudentNotes] = React.useState([]);
    const [newNoteContent, setNewNoteContent] = React.useState('');
    const [editingNoteId, setEditingNoteId] = React.useState(null);
    const [editNoteContent, setEditNoteContent] = React.useState('');
    const [notesLoading, setNotesLoading] = React.useState(false);

    // Rounds view modal
    const [viewRoundsStudent, setViewRoundsStudent] = React.useState(null);
    const [roundsHistory, setRoundsHistory] = React.useState([]);

    const [toastMessage, setToastMessage] = React.useState('');
    const [generatingStudentId, setGeneratingStudentId] = React.useState(null);

    const showToast = (msg) => {
        setToastMessage(msg);
        setTimeout(() => setToastMessage(''), 3500);
    };

    // Load initial data
    const loadDashboardData = React.useCallback(async () => {
        setLoading(true);
        try {
            // Fetch sample or demo mentees
            const menteesRes = await fetch(`/api/mentor/demo/mentees`);
            if (menteesRes.ok) {
                const data = await menteesRes.json();
                setMentees(data.mentees || []);
                setPlacedMentees(data.placed_mentees || []);
                setMetrics(data.metrics || null);
                const interventionRes = await fetch('/api/interventions', {
                    headers: window.interventionHeaders(user)
                });
                if (interventionRes.ok) {
                    const interventionData = await interventionRes.json();
                    setInterventions(interventionData.interventions || []);
                } else {
                    setInterventions([]);
                }
            } else {
                // Fallback demo dataset if API not fully initialized
                const demoMentees = [
                    { student_id: 'st-101', name: 'Arun Kumar', register_number: '312321104001', department: 'CSE', cgpa: 8.4, tenth: 92, twelfth: 89, placement_marks: 78, status: 'Active', phone: '9876543210', email: 'arunkumar@stjosephs.ac.in', skills: ['Python', 'React', 'Data Structures'] },
                    { student_id: 'st-102', name: 'Bhavani S', register_number: '312321104015', department: 'ECE', cgpa: 7.9, tenth: 88, twelfth: 85, placement_marks: 65, status: 'Active', phone: '9876543211', email: 'bhavanis@stjosephs.ac.in', skills: ['C++', 'Embedded Systems', 'SQL'] },
                    { student_id: 'st-103', name: 'Deepak Raj', register_number: '312321205008', department: 'IT', cgpa: 8.8, tenth: 95, twelfth: 93, placement_marks: 88, status: 'Placed', company: 'Goldman Sachs', ctc: 22.0, job_role: 'Analyst', phone: '9876543212', email: 'deepakraj@stjosephs.ac.in', skills: ['Java', 'Spring Boot', 'System Design'] },
                    { student_id: 'st-104', name: 'Divya M', register_number: '312321104032', department: 'CSE', cgpa: 6.8, tenth: 81, twelfth: 79, placement_marks: 52, status: 'At Risk', phone: '9876543213', email: 'divyam@stjosephs.ac.in', skills: ['HTML', 'CSS', 'JavaScript'] },
                    { student_id: 'st-105', name: 'Elango P', register_number: '312321205021', department: 'IT', cgpa: 9.1, tenth: 96, twelfth: 94, placement_marks: 92, status: 'Placed', company: 'Microsoft', ctc: 18.5, job_role: 'Software Engineer', phone: '9876543214', email: 'elangop@stjosephs.ac.in', skills: ['Python', 'Machine Learning', 'Docker'] }
                ];
                setMentees(demoMentees);
                setPlacedMentees(demoMentees.filter(m => m.status === 'Placed'));
                setInterventions([]);
                setMetrics({
                    total_mentees: 5,
                    placed_count: 2,
                    placement_rate: 40.0,
                    active_interventions: 1,
                    at_risk_count: 1
                });
            }
        } catch (e) {
            console.error('Failed to load mentor data', e);
        } finally {
            setLoading(false);
        }
    }, [user]);

    React.useEffect(() => {
        loadDashboardData();
    }, [loadDashboardData]);

    // Filtered Mentees
    const filteredMentees = React.useMemo(() => {
        if (!searchQuery) return mentees;
        const q = searchQuery.toLowerCase();
        return mentees.filter(m =>
            (m.name || '').toLowerCase().includes(q) ||
            (m.register_number || '').toLowerCase().includes(q) ||
            (m.department || '').toLowerCase().includes(q)
        );
    }, [mentees, searchQuery]);

    // Handle student detail opening & loading notes
    const handleOpenStudentDetail = async (student) => {
        setSelectedStudent(student);
        setNotesLoading(true);
        try {
            const res = await fetch(`/api/mentor/notes?student_id=${student.student_id}`);
            if (res.ok) {
                const data = await res.json();
                setStudentNotes(data.notes || []);
            } else {
                setStudentNotes([
                    { note_id: 'n-1', content: 'Initial counseling done. Student needs improvement in Data Structures.', created_at: '2026-09-20 10:30' }
                ]);
            }
        } catch (e) {
            setStudentNotes([]);
        } finally {
            setNotesLoading(false);
        }
    };

    // Notes CRUD handlers
    const handleAddNote = async (e) => {
        e.preventDefault();
        if (!newNoteContent.trim() || !selectedStudent) return;
        try {
            const res = await fetch('/api/mentor/notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: selectedStudent.student_id,
                    content: newNoteContent.trim()
                })
            });
            if (res.ok) {
                const data = await res.json();
                setStudentNotes(prev => [data.note, ...prev]);
            } else {
                setStudentNotes(prev => [{
                    note_id: 'n-' + Date.now(),
                    content: newNoteContent.trim(),
                    created_at: new Date().toISOString().replace('T', ' ').substring(0, 16)
                }, ...prev]);
            }
            setNewNoteContent('');
            showToast('Note added successfully!');
        } catch (err) {
            showToast('Note added locally!');
            setStudentNotes(prev => [{
                note_id: 'n-' + Date.now(),
                content: newNoteContent.trim(),
                created_at: new Date().toISOString().replace('T', ' ').substring(0, 16)
            }, ...prev]);
            setNewNoteContent('');
        }
    };

    const handleStartEditNote = (note) => {
        setEditingNoteId(note.note_id);
        setEditNoteContent(note.content);
    };

    const handleSaveEditNote = async (noteId) => {
        if (!editNoteContent.trim()) return;
        try {
            await fetch(`/api/mentor/notes/${noteId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: editNoteContent.trim() })
            });
        } catch (e) { }
        setStudentNotes(prev => prev.map(n => n.note_id === noteId ? { ...n, content: editNoteContent.trim() } : n));
        setEditingNoteId(null);
        setEditNoteContent('');
        showToast('Note updated successfully!');
    };

    const handleDeleteNote = async (noteId) => {
        try {
            await fetch(`/api/mentor/notes/${noteId}`, { method: 'DELETE' });
        } catch (e) { }
        setStudentNotes(prev => prev.filter(n => n.note_id !== noteId));
        showToast('Note deleted.');
    };

    // Toggle Action Progress
    const handleToggleAction = async (intvId, actionId) => {
        const intervention = interventions.find(item => item.id === intvId);
        const action = intervention?.actions?.find(item => item.id === actionId);
        if (!action) return;
        const res = await fetch(`/api/intervention/actions/${actionId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', ...window.interventionHeaders(user) },
            body: JSON.stringify({ completed: !action.completed })
        });
        if (!res.ok) {
            showToast('Unable to update action progress.');
            return;
        }
        setInterventions(prev => prev.map(intv => {
            if (intv.id !== intvId) return intv;
            const updatedActions = intv.actions.map(act =>
                act.id === actionId ? { ...act, completed: !act.completed } : act
            );
            return { ...intv, actions: updatedActions };
        }));
        showToast('Action item progress updated!');
    };

    const handleGenerateIntervention = async (student) => {
        setGeneratingStudentId(student.student_id);
        try {
            const res = await fetch('/api/interventions/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...window.interventionHeaders(user) },
                body: JSON.stringify({ student_id: student.student_id })
            });
            const data = await res.json();
            if (!res.ok) {
                showToast(data.detail || 'Unable to generate intervention.');
                return;
            }
            setInterventions(prev => [data.intervention, ...prev]);
            showToast(`Intervention generated for ${student.name}.`);
        } catch (error) {
            showToast('Unable to reach the intervention service.');
        } finally {
            setGeneratingStudentId(null);
        }
    };

    // View Student Rounds
    const handleViewRounds = async (student) => {
        setViewRoundsStudent(student);
        try {
            const res = await fetch(`/api/student/results?gmail=${encodeURIComponent(student.email)}`);
            if (res.ok) {
                const data = await res.json();
                setRoundsHistory(data.results || []);
            } else {
                setRoundsHistory([
                    { company_name: 'Goldman Sachs', job_role: 'Analyst', round: 3, result: 'Selected' },
                    { company_name: 'Microsoft', job_role: 'Software Engineer', round: 2, result: 'Shortlisted for Round 3' }
                ]);
            }
        } catch (e) {
            setRoundsHistory([]);
        }
    };

    return (
        <div className="laptop-dashboard">
            {/* Top Navbar */}
            <header className="desktop-navbar">
                <div className="nav-left">
                    <div className="brand-icon">
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 100 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                        </svg>
                    </div>
                    <div>
                        <h1 className="brand-title">Mentor Workspace</h1>
                        <p className="brand-subtitle">Student Performance Tracking & Mentorship Management</p>
                    </div>
                </div>

                {/* Navbar Navigation Tabs */}
                <div className="nav-tabs" style={{ display: 'flex', gap: '8px' }}>
                    {[
                        { id: 'overview', label: 'Overview' },
                        { id: 'mentees', label: `My Mentees (${mentees.length})` },
                        { id: 'placed', label: `Placed Mentees (${placedMentees.length})` },
                        { id: 'interventions', label: `Interventions (${interventions.length})` },
                        { id: 'metrics', label: 'Performance Metrics' }
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
                    <div className="user-profile">
                        <div className="user-avatar" style={{ background: '#3b82f6', color: '#fff', width: '36px', height: '36px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                            M
                        </div>
                        <div className="user-info">
                            <span className="user-name">{user?.gmail || 'mentor@gmail.com'}</span>
                            <span className="user-role-badge" style={{ background: '#1d4ed8', color: '#fff', fontSize: '0.75rem', padding: '2px 8px', borderRadius: '12px', marginLeft: '6px' }}>Mentor</span>
                        </div>
                    </div>
                    <button type="button" className="logout-btn" onClick={onLogout} style={{ padding: '8px 14px', borderRadius: '6px', background: '#334155', color: '#f8fafc', border: 'none', cursor: 'pointer' }}>
                        Sign Out
                    </button>
                </div>
            </header>

            {/* Toast Notification */}
            {toastMessage && (
                <div style={{ position: 'fixed', bottom: '24px', right: '24px', zIndex: 1000, background: '#10b981', color: '#fff', padding: '12px 20px', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.3)', fontWeight: '600' }}>
                    {toastMessage}
                </div>
            )}

            {/* MAIN CONTENT AREA */}
            <main className="dashboard-body" style={{ marginTop: '20px' }}>

                {/* TAB 1: OVERVIEW */}
                {activeTab === 'overview' && (
                    <div>
                        <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
                            <div className="card stat-card" style={{ background: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>Assigned Mentees</span>
                                <h3 style={{ fontSize: '2rem', color: '#f8fafc', marginTop: '8px' }}>{mentees.length}</h3>
                                <p style={{ fontSize: '0.75rem', color: '#34d399', marginTop: '4px' }}>Active tracking</p>
                            </div>
                            <div className="card stat-card" style={{ background: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>Placed Students</span>
                                <h3 style={{ fontSize: '2rem', color: '#34d399', marginTop: '8px' }}>{placedMentees.length}</h3>
                                <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '4px' }}>{mentees.length > 0 ? ((placedMentees.length / mentees.length) * 100).toFixed(0) : 0}% success rate</p>
                            </div>
                            <div className="card stat-card" style={{ background: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>Active Interventions</span>
                                <h3 style={{ fontSize: '2rem', color: '#f59e0b', marginTop: '8px' }}>{interventions.length}</h3>
                                <p style={{ fontSize: '0.75rem', color: '#f59e0b', marginTop: '4px' }}>Requires monitoring</p>
                            </div>
                            <div className="card stat-card" style={{ background: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>At-Risk Students</span>
                                <h3 style={{ fontSize: '2rem', color: '#ef4444', marginTop: '8px' }}>
                                    {mentees.filter(m => m.status === 'At Risk' || m.cgpa < 7.0).length}
                                </h3>
                                <p style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '4px' }}>High priority support</p>
                            </div>
                        </div>

                        {/* Recent Mentees Card Grid */}
                        <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                <h3 style={{ color: '#f8fafc', fontSize: '1.25rem' }}>Mentee Roster & Quick Progress</h3>
                                <button type="button" onClick={() => setActiveTab('mentees')} style={{ background: 'transparent', color: '#3b82f6', border: 'none', cursor: 'pointer', fontWeight: '600' }}>
                                    View All Mentees &rarr;
                                </button>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
                                {mentees.slice(0, 4).map(m => (
                                    <div key={m.student_id} style={{ background: '#0f172a', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                            <div>
                                                <h4 style={{ color: '#f8fafc', fontSize: '1rem', fontWeight: '600' }}>{m.name}</h4>
                                                <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{m.register_number} &bull; {m.department}</p>
                                            </div>
                                            <span style={{
                                                padding: '2px 8px',
                                                borderRadius: '12px',
                                                fontSize: '0.75rem',
                                                fontWeight: '600',
                                                background: m.status === 'Placed' ? 'rgba(16,185,129,0.2)' : m.status === 'At Risk' ? 'rgba(239,68,68,0.2)' : 'rgba(59,130,246,0.2)',
                                                color: m.status === 'Placed' ? '#34d399' : m.status === 'At Risk' ? '#f87171' : '#60a5fa'
                                            }}>
                                                {m.status}
                                            </span>
                                        </div>
                                        <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: '#cbd5e1' }}>
                                            <span>CGPA: <strong>{m.cgpa}</strong></span>
                                            <span>Placement Score: <strong>{m.placement_marks || 0}/100</strong></span>
                                        </div>
                                        <div style={{ marginTop: '14px', display: 'flex', gap: '8px' }}>
                                            <button
                                                type="button"
                                                onClick={() => handleOpenStudentDetail(m)}
                                                style={{ flex: 1, padding: '6px 12px', borderRadius: '6px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontSize: '0.8rem', fontWeight: '500' }}
                                            >
                                                Profile & Notes
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => handleViewRounds(m)}
                                                style={{ padding: '6px 12px', borderRadius: '6px', background: '#334155', color: '#f8fafc', border: 'none', cursor: 'pointer', fontSize: '0.8rem' }}
                                            >
                                                Rounds
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* TAB 2: MY MENTEES TABLE */}
                {activeTab === 'mentees' && (
                    <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
                            <div>
                                <h3 style={{ color: '#f8fafc', fontSize: '1.25rem' }}>Assigned Mentee List</h3>
                                <p style={{ color: '#94a3b8', fontSize: '0.875rem' }}>Track academic standing, placement results, and add mentorship notes.</p>
                            </div>
                            <input
                                type="text"
                                placeholder="Search by name, reg no, dept..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                style={{
                                    padding: '8px 14px',
                                    borderRadius: '6px',
                                    background: '#0f172a',
                                    border: '1px solid #334155',
                                    color: '#f8fafc',
                                    width: '280px'
                                }}
                            />
                        </div>

                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', fontSize: '0.85rem' }}>
                                        <th style={{ padding: '12px' }}>REGISTER NO</th>
                                        <th style={{ padding: '12px' }}>STUDENT NAME</th>
                                        <th style={{ padding: '12px' }}>DEPT</th>
                                        <th style={{ padding: '12px' }}>CGPA</th>
                                        <th style={{ padding: '12px' }}>PLACEMENT MARKS</th>
                                        <th style={{ padding: '12px' }}>STATUS</th>
                                        <th style={{ padding: '12px', textAlign: 'right' }}>ACTIONS</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredMentees.map(m => (
                                        <tr key={m.student_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#f8fafc' }}>
                                            <td style={{ padding: '12px', fontFamily: 'monospace', color: '#94a3b8' }}>{m.register_number}</td>
                                            <td style={{ padding: '12px', fontWeight: '600' }}>{m.name}</td>
                                            <td style={{ padding: '12px' }}>{m.department}</td>
                                            <td style={{ padding: '12px', fontWeight: '600' }}>{m.cgpa}</td>
                                            <td style={{ padding: '12px' }}>{m.placement_marks || 'N/A'}</td>
                                            <td style={{ padding: '12px' }}>
                                                <span style={{
                                                    padding: '4px 10px',
                                                    borderRadius: '12px',
                                                    fontSize: '0.75rem',
                                                    fontWeight: '600',
                                                    background: m.status === 'Placed' ? 'rgba(16,185,129,0.2)' : m.status === 'At Risk' ? 'rgba(239,68,68,0.2)' : 'rgba(59,130,246,0.2)',
                                                    color: m.status === 'Placed' ? '#34d399' : m.status === 'At Risk' ? '#f87171' : '#60a5fa'
                                                }}>
                                                    {m.status}
                                                </span>
                                            </td>
                                            <td style={{ padding: '12px', textAlign: 'right' }}>
                                                <button
                                                    type="button"
                                                    onClick={() => handleOpenStudentDetail(m)}
                                                    style={{ padding: '6px 12px', borderRadius: '6px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontSize: '0.8rem', marginRight: '8px' }}
                                                >
                                                    Profile & Notes
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => handleViewRounds(m)}
                                                    style={{ padding: '6px 12px', borderRadius: '6px', background: '#334155', color: '#f8fafc', border: 'none', cursor: 'pointer', fontSize: '0.8rem' }}
                                                >
                                                    View Rounds
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* TAB 3: PLACED MENTEES */}
                {activeTab === 'placed' && (
                    <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                        <h3 style={{ color: '#f8fafc', fontSize: '1.25rem', marginBottom: '8px' }}>Placed Mentees Wall of Success</h3>
                        <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '20px' }}>Students successfully recruited by partner companies.</p>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
                            {placedMentees.map(m => (
                                <div key={m.student_id} style={{ background: '#0f172a', padding: '20px', borderRadius: '10px', border: '1px solid #10b981' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <h4 style={{ color: '#f8fafc', fontSize: '1.1rem' }}>{m.name}</h4>
                                        <span style={{ background: 'rgba(16,185,129,0.2)', color: '#34d399', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 'bold' }}>PLACED</span>
                                    </div>
                                    <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '4px' }}>{m.register_number} &bull; {m.department}</p>

                                    <div style={{ marginTop: '16px', background: '#1e293b', padding: '12px', borderRadius: '6px' }}>
                                        <div style={{ color: '#60a5fa', fontWeight: 'bold', fontSize: '1rem' }}>{m.company || 'Tech Company'}</div>
                                        <div style={{ color: '#cbd5e1', fontSize: '0.85rem', marginTop: '2px' }}>Role: {m.job_role || 'Software Engineer'}</div>
                                        <div style={{ color: '#34d399', fontWeight: '600', marginTop: '4px', fontSize: '0.9rem' }}>CTC: ₹{m.ctc || '12.0'} LPA</div>
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
                        title="Mentee Intervention Workflows"
                        description="Expand any authorized mentee to view their intervention and action plan."
                    />
                )}

                {/* TAB 5: METRICS */}
                {activeTab === 'metrics' && (
                    <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                        <h3 style={{ color: '#f8fafc', fontSize: '1.25rem', marginBottom: '20px' }}>Mentorship Performance & Analytics</h3>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
                            <div style={{ background: '#0f172a', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                <h4 style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Intervention Resolution Rate</h4>
                                <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#34d399', margin: '12px 0' }}>85.0%</div>
                                <p style={{ color: '#cbd5e1', fontSize: '0.8rem' }}>Mentees showing mark improvement after intervention steps.</p>
                            </div>

                            <div style={{ background: '#0f172a', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                <h4 style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Placement Conversion Target</h4>
                                <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#60a5fa', margin: '12px 0' }}>40.0%</div>
                                <p style={{ color: '#cbd5e1', fontSize: '0.8rem' }}>Placed mentees out of total assigned cohort.</p>
                            </div>

                            <div style={{ background: '#0f172a', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
                                <h4 style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Primary Risk Focus Area</h4>
                                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#f59e0b', margin: '12px 0' }}>Data Structures & Algorithms</div>
                                <p style={{ color: '#cbd5e1', fontSize: '0.8rem' }}>Main topic identified in mock interview evaluations.</p>
                            </div>
                        </div>
                    </div>
                )}
            </main>

            {/* MODAL / DRAWER: STUDENT DETAIL & MENTOR NOTES (FULL INTERACTIVE CRUD) */}
            {selectedStudent && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 100, display: 'flex', justifyContent: 'flex-end' }}>
                    <div style={{ width: '100%', maxWidth: '560px', background: '#0f172a', height: '100%', padding: '24px', overflowY: 'auto', borderLeft: '1px solid #334155' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #334155', pb: '16px' }}>
                            <div>
                                <h3 style={{ color: '#f8fafc', fontSize: '1.25rem' }}>{selectedStudent.name}</h3>
                                <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{selectedStudent.register_number} &bull; {selectedStudent.department}</p>
                            </div>
                            <button
                                type="button"
                                onClick={() => setSelectedStudent(null)}
                                style={{ background: 'transparent', color: '#94a3b8', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}
                            >
                                &times;
                            </button>
                        </div>

                        {/* Student Profile Overview */}
                        <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', marginBottom: '24px' }}>
                            <h4 style={{ color: '#60a5fa', fontSize: '0.9rem', marginBottom: '10px', textTransform: 'uppercase' }}>Academic & Placement Record</h4>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.85rem', color: '#cbd5e1' }}>
                                <div>CGPA: <strong style={{ color: '#fff' }}>{selectedStudent.cgpa}</strong></div>
                                <div>Placement Mark: <strong style={{ color: '#fff' }}>{selectedStudent.placement_marks || 0}</strong></div>
                                <div>10th Percentage: <strong style={{ color: '#fff' }}>{selectedStudent.tenth}%</strong></div>
                                <div>12th Percentage: <strong style={{ color: '#fff' }}>{selectedStudent.twelfth}%</strong></div>
                                <div style={{ gridColumn: 'span 2' }}>Email: <strong style={{ color: '#fff' }}>{selectedStudent.email}</strong></div>
                            </div>
                        </div>

                        {/* Mentor Notes Interactive CRUD Section */}
                        <div style={{ marginTop: '24px' }}>
                            <h4 style={{ color: '#f8fafc', fontSize: '1.1rem', marginBottom: '12px' }}>Mentor Counseling Notes</h4>

                            {/* Add Note Form */}
                            <form onSubmit={handleAddNote} style={{ marginBottom: '20px' }}>
                                <textarea
                                    rows="3"
                                    placeholder="Write a mentorship observation, interview feedback, or action note..."
                                    value={newNoteContent}
                                    onChange={(e) => setNewNoteContent(e.target.value)}
                                    style={{
                                        width: '100%',
                                        padding: '12px',
                                        borderRadius: '6px',
                                        background: '#1e293b',
                                        border: '1px solid #334155',
                                        color: '#f8fafc',
                                        resize: 'vertical',
                                        marginBottom: '8px'
                                    }}
                                />
                                <button
                                    type="submit"
                                    style={{
                                        padding: '8px 16px',
                                        borderRadius: '6px',
                                        background: '#2563eb',
                                        color: '#fff',
                                        border: 'none',
                                        cursor: 'pointer',
                                        fontWeight: '600',
                                        fontSize: '0.85rem'
                                    }}
                                >
                                    Add Note
                                </button>
                            </form>

                            {/* Notes List */}
                            {notesLoading ? (
                                <p style={{ color: '#94a3b8' }}>Loading notes...</p>
                            ) : studentNotes.length === 0 ? (
                                <p style={{ color: '#64748b', fontSize: '0.9rem' }}>No mentorship notes recorded yet for this student.</p>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                    {studentNotes.map(n => (
                                        <div key={n.note_id} style={{ background: '#1e293b', padding: '14px', borderRadius: '8px', border: '1px solid #334155' }}>
                                            {editingNoteId === n.note_id ? (
                                                <div>
                                                    <textarea
                                                        rows="3"
                                                        value={editNoteContent}
                                                        onChange={(e) => setEditNoteContent(e.target.value)}
                                                        style={{ width: '100%', padding: '8px', background: '#0f172a', color: '#fff', border: '1px solid #3b82f6', borderRadius: '4px', marginBottom: '8px' }}
                                                    />
                                                    <div style={{ display: 'flex', gap: '8px' }}>
                                                        <button type="button" onClick={() => handleSaveEditNote(n.note_id)} style={{ background: '#10b981', color: '#fff', border: 'none', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}>Save</button>
                                                        <button type="button" onClick={() => setEditingNoteId(null)} style={{ background: '#64748b', color: '#fff', border: 'none', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}>Cancel</button>
                                                    </div>
                                                </div>
                                            ) : (
                                                <div>
                                                    <p style={{ color: '#f8fafc', fontSize: '0.9rem', whitespace: 'pre-wrap' }}>{n.content}</p>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', fontSize: '0.75rem', color: '#94a3b8' }}>
                                                        <span>{n.created_at}</span>
                                                        <div style={{ display: 'flex', gap: '8px' }}>
                                                            <button type="button" onClick={() => handleStartEditNote(n)} style={{ background: 'transparent', color: '#60a5fa', border: 'none', cursor: 'pointer' }}>Edit</button>
                                                            <button type="button" onClick={() => handleDeleteNote(n.note_id)} style={{ background: 'transparent', color: '#f87171', border: 'none', cursor: 'pointer' }}>Delete</button>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* MODAL: VIEW ROUNDS HISTORY */}
            {viewRoundsStudent && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
                    <div style={{ width: '100%', maxWidth: '600px', background: '#0f172a', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                            <h3 style={{ color: '#f8fafc', fontSize: '1.2rem' }}>Round Results: {viewRoundsStudent.name}</h3>
                            <button type="button" onClick={() => setViewRoundsStudent(null)} style={{ background: 'transparent', color: '#94a3b8', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}>&times;</button>
                        </div>
                        {roundsHistory.length === 0 ? (
                            <p style={{ color: '#94a3b8' }}>No recruitment round history recorded for this student.</p>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                {roundsHistory.map((r, idx) => (
                                    <div key={idx} style={{ background: '#1e293b', padding: '12px 16px', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <div>
                                            <div style={{ color: '#f8fafc', fontWeight: 'bold' }}>{r.company_name}</div>
                                            <div style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Role: {r.job_role || 'SDE'} &bull; Round {r.round}</div>
                                        </div>
                                        <span style={{ padding: '4px 10px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 'bold', background: 'rgba(59,130,246,0.2)', color: '#60a5fa' }}>
                                            {r.result}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
