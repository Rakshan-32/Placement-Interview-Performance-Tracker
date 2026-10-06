function ResetPasswordView({ token, onGoToLogin }) {
    const [password, setPassword] = React.useState('');
    const [confirmPassword, setConfirmPassword] = React.useState('');
    const [loading, setLoading] = React.useState(false);
    const [validating, setValidating] = React.useState(true);
    const [tokenValid, setTokenValid] = React.useState(false);
    const [tokenError, setTokenError] = React.useState('');
    const [alert, setAlert] = React.useState({ show: false, type: '', message: '' });
    const [resetDone, setResetDone] = React.useState(false);

    React.useEffect(() => {
        (async () => {
            try {
                const res = await fetch(`/api/auth/validate-token?token=${encodeURIComponent(token)}&purpose=PASSWORD_RESET`);
                const data = await res.json();
                if (data.valid) {
                    setTokenValid(true);
                } else {
                    setTokenError(data.error || 'Invalid or expired reset link.');
                }
            } catch (err) {
                setTokenError('Unable to verify reset link.');
            }
            setValidating(false);
        })();
    }, [token]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setAlert({ show: false, type: '', message: '' });

        if (password.length < 6) {
            setAlert({ show: true, type: 'error', message: 'Password must be at least 6 characters.' });
            return;
        }
        if (password !== confirmPassword) {
            setAlert({ show: true, type: 'error', message: 'Passwords do not match.' });
            return;
        }

        setLoading(true);
        try {
            const res = await fetch('/api/auth/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, password })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                setResetDone(true);
                setAlert({ show: true, type: 'success', message: data.message });
            } else {
                setAlert({ show: true, type: 'error', message: data.message || 'Password reset failed.' });
            }
        } catch (err) {
            setAlert({ show: true, type: 'error', message: 'Network error. Please try again.' });
        }
        setLoading(false);
    };

    const cardStyle = {
        maxWidth: '460px',
        margin: '60px auto',
        padding: '32px',
        background: '#1e293b',
        borderRadius: '12px',
        border: '1px solid #334155'
    };

    if (validating) {
        return (
            <div style={cardStyle}>
                <p style={{ color: '#94a3b8', textAlign: 'center' }}>Validating reset link...</p>
            </div>
        );
    }

    if (tokenError) {
        return (
            <div style={cardStyle}>
                <h2 style={{ color: '#f87171', marginBottom: '12px' }}>Reset Link Invalid</h2>
                <p style={{ color: '#94a3b8', marginBottom: '20px' }}>{tokenError}</p>
                <button type="button" onClick={onGoToLogin} style={{ padding: '10px 24px', borderRadius: '8px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: '600' }}>
                    Go to Login
                </button>
            </div>
        );
    }

    if (resetDone) {
        return (
            <div style={cardStyle}>
                <h2 style={{ color: '#34d399', marginBottom: '12px' }}>Password Reset Complete</h2>
                <p style={{ color: '#f8fafc', marginBottom: '20px' }}>Your password has been updated. You can now sign in.</p>
                <button type="button" onClick={onGoToLogin} style={{ padding: '10px 24px', borderRadius: '8px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: '600' }}>
                    Sign In
                </button>
            </div>
        );
    }

    return (
        <div style={cardStyle}>
            <h2 style={{ color: '#f8fafc', marginBottom: '16px' }}>Reset Your Password</h2>

            {alert.show && (
                <div style={{
                    padding: '10px 14px', borderRadius: '6px', marginBottom: '16px', fontSize: '0.9rem',
                    background: alert.type === 'error' ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)',
                    color: alert.type === 'error' ? '#f87171' : '#34d399',
                    border: `1px solid ${alert.type === 'error' ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'}`
                }}>
                    {alert.message}
                </div>
            )}

            <form onSubmit={handleSubmit}>
                <div style={{ marginBottom: '16px' }}>
                    <label style={{ color: '#f8fafc', fontWeight: '500', display: 'block', marginBottom: '6px' }}>New Password</label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="At least 6 characters"
                        required
                        style={{ width: '100%', padding: '10px 14px', borderRadius: '6px', background: '#0f172a', border: '1px solid #334155', color: '#f8fafc' }}
                    />
                </div>
                <div style={{ marginBottom: '20px' }}>
                    <label style={{ color: '#f8fafc', fontWeight: '500', display: 'block', marginBottom: '6px' }}>Confirm Password</label>
                    <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="Re-enter password"
                        required
                        style={{ width: '100%', padding: '10px 14px', borderRadius: '6px', background: '#0f172a', border: '1px solid #334155', color: '#f8fafc' }}
                    />
                </div>
                <button type="submit" disabled={loading} style={{ width: '100%', padding: '12px', borderRadius: '8px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: '600', fontSize: '1rem' }}>
                    {loading ? 'Resetting...' : 'Reset Password'}
                </button>
            </form>
        </div>
    );
}
