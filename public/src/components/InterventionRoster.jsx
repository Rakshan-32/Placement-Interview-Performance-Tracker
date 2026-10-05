function InterventionRoster({ user, canGenerate = true, title = 'Interventions', description = 'Expand a student to view their intervention.' }) {
    const [students, setStudents] = React.useState([]);
    const [expandedStudentId, setExpandedStudentId] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [refreshing, setRefreshing] = React.useState(false);
    const [generatingStudentId, setGeneratingStudentId] = React.useState(null);
    const [generatingAll, setGeneratingAll] = React.useState(false);
    const [error, setError] = React.useState('');

    const loadStudents = React.useCallback(async (showLoader = false) => {
        if (showLoader) {
            setLoading(true);
        } else {
            setRefreshing(true);
        }
        setError('');
        try {
            const response = await fetch('/api/interventions/students', {
                headers: window.interventionHeaders(user)
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Unable to load intervention students.');
            }
            setStudents(data.students || []);
        } catch (loadError) {
            setError(loadError.message);
        } finally {
            if (showLoader) {
                setLoading(false);
            } else {
                setRefreshing(false);
            }
        }
    }, [user]);

    React.useEffect(() => {
        loadStudents(true);
    }, [loadStudents]);

    const generateForStudent = async (student) => {
        setGeneratingStudentId(student.uuid);
        setError('');
        try {
            const response = await fetch('/api/interventions/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...window.interventionHeaders(user) },
                body: JSON.stringify({ student_id: student.uuid })
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Unable to generate intervention.');
            }
            await loadStudents(false);
            setExpandedStudentId(student.uuid);
        } catch (generationError) {
            setError(generationError.message);
        } finally {
            setGeneratingStudentId(null);
        }
    };

    const generateForAll = async () => {
        setGeneratingAll(true);
        setError('');
        try {
            const response = await fetch('/api/interventions/generate-all', {
                method: 'POST',
                headers: window.interventionHeaders(user)
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Unable to generate interventions.');
            }
            await loadStudents(false);
            if (data.failures?.length) {
                const rateLimited = data.failures.filter(failure => String(failure.error || '').includes('HTTP 429')).length;
                const details = data.failures.slice(0, 3).map(failure => `${failure.gmail}: ${failure.error}`).join(' | ');
                const prefix = rateLimited ? 'Groq rate limit reached. ' : '';
                setError(`${prefix}${data.generated?.length || 0} generated; ${data.failures.length} failed. ${details}`);
            }
        } catch (generationError) {
            setError(generationError.message);
        } finally {
            setGeneratingAll(false);
        }
    };

    const updateStatus = async (interventionId, nextStatus) => {
        const response = await fetch(`/api/interventions/${interventionId}/status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', ...window.interventionHeaders(user) },
            body: JSON.stringify({ status: nextStatus })
        });
        if (response.ok) {
            await loadStudents(false);
        } else {
            const data = await response.json();
            setError(data.detail || 'Unable to update intervention status.');
        }
    };

    const updateAction = async (action) => {
        const response = await fetch(`/api/intervention/actions/${action.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', ...window.interventionHeaders(user) },
            body: JSON.stringify({ completed: !action.completed })
        });
        if (response.ok) {
            await loadStudents(false);
        } else {
            const data = await response.json();
            setError(data.detail || 'Unable to update intervention action.');
        }
    };

    return (
        <div className="card" style={{ background: '#1e293b', padding: '24px', borderRadius: '10px', border: '1px solid #334155' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap', marginBottom: '20px' }}>
                <div>
                    <h3 style={{ color: '#f8fafc', fontSize: '1.25rem', margin: 0 }}>{title}</h3>
                    <p style={{ color: '#94a3b8', fontSize: '0.875rem', margin: '8px 0 0' }}>{description}</p>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                    <button type="button" onClick={() => loadStudents(false)} style={{ padding: '8px 12px', borderRadius: '6px', background: '#334155', color: '#f8fafc', border: 'none', cursor: 'pointer' }}>
                        {refreshing ? 'Refreshing...' : 'Refresh'}
                    </button>
                    {canGenerate && (
                        <button type="button" onClick={generateForAll} disabled={generatingAll || loading || students.length === 0} style={{ padding: '8px 14px', borderRadius: '6px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: '600' }}>
                            {generatingAll ? 'Generating All...' : 'Generate All'}
                        </button>
                    )}
                </div>
            </div>

            {error && <div style={{ background: 'rgba(239,68,68,0.12)', color: '#fca5a5', padding: '10px 12px', borderRadius: '6px', marginBottom: '14px' }}>{error}</div>}
            {refreshing && !loading && <div style={{ color: '#94a3b8', fontSize: '0.8rem', marginBottom: '10px' }}>Updating intervention data...</div>}
            {loading ? (
                <p style={{ color: '#94a3b8' }}>Loading authorized students...</p>
            ) : students.length === 0 ? (
                <p style={{ color: '#64748b' }}>No students are available in your authorized scope.</p>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {students.map(student => {
                        const expanded = expandedStudentId === student.uuid;
                        return (
                            <div key={student.uuid} style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', overflow: 'hidden' }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', padding: '14px 16px', flexWrap: 'wrap' }}>
                                    <button type="button" onClick={() => setExpandedStudentId(expanded ? null : student.uuid)} style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: '240px', textAlign: 'left', background: 'transparent', color: '#f8fafc', border: 'none', cursor: 'pointer' }}>
                                        <span style={{ color: '#60a5fa', fontSize: '1.1rem' }}>{expanded ? '-' : '+'}</span>
                                        <span>
                                            <strong style={{ display: 'block' }}>{student.gmail}</strong>
                                            <small style={{ color: '#94a3b8' }}>{student.department || 'Department not assigned'} · {student.intervention_count || 0} intervention(s)</small>
                                        </span>
                                    </button>
                                    {canGenerate && (
                                        <button type="button" onClick={() => generateForStudent(student)} disabled={generatingStudentId === student.uuid} style={{ padding: '7px 12px', borderRadius: '6px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: '600' }}>
                                            {generatingStudentId === student.uuid ? 'Generating...' : 'Generate Intervention'}
                                        </button>
                                    )}
                                </div>

                                {expanded && (
                                    <div style={{ borderTop: '1px solid #334155', padding: '16px' }}>
                                        {student.interventions.length === 0 ? (
                                            <p style={{ color: '#64748b', margin: 0 }}>No intervention generated for this student.</p>
                                        ) : (
                                            student.interventions.map(intervention => (
                                                <div key={intervention.id} style={{ background: '#1e293b', padding: '14px', borderRadius: '7px', marginBottom: '10px' }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
                                                        <div>
                                                            <strong style={{ color: '#f8fafc' }}>{intervention.title}</strong>
                                                            <p style={{ color: '#cbd5e1', fontSize: '0.85rem', margin: '8px 0 0' }}>{intervention.failure_summary}</p>
                                                        </div>
                                                        {canGenerate ? (
                                                            <select value={intervention.status} onChange={(event) => updateStatus(intervention.id, event.target.value)} style={{ height: '32px', background: '#334155', color: '#f8fafc', border: '1px solid #475569', borderRadius: '5px' }}>
                                                                <option value="OPEN">OPEN</option>
                                                                <option value="IN_PROGRESS">IN PROGRESS</option>
                                                                <option value="COMPLETED">COMPLETED</option>
                                                                <option value="CANCELLED">CANCELLED</option>
                                                            </select>
                                                        ) : (
                                                            <span style={{ color: '#fbbf24', fontSize: '0.8rem', fontWeight: '700' }}>{intervention.status}</span>
                                                        )}
                                                    </div>
                                                    <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{intervention.ai_analysis}</p>
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
                                                        {intervention.actions.map(action => (
                                                            <label key={action.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', color: action.completed ? '#94a3b8' : '#f8fafc', fontSize: '0.85rem' }}>
                                                                <input type="checkbox" checked={Boolean(action.completed)} disabled={!canGenerate} onChange={() => canGenerate && updateAction(action)} />
                                                                <span style={{ textDecoration: action.completed ? 'line-through' : 'none' }}>{action.title}</span>
                                                            </label>
                                                        ))}
                                                    </div>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
