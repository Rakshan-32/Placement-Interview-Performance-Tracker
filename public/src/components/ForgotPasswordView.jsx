function ForgotPasswordView({ onGoToLogin }) {
    const [gmail, setGmail] = React.useState('');
    const [loading, setLoading] = React.useState(false);
    const [submitted, setSubmitted] = React.useState(false);
    const [alert, setAlert] = React.useState({ show: false, type: '', message: '' });
    const [devResetUrl, setDevResetUrl] = React.useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setAlert({ show: false, type: '', message: '' });
        setDevResetUrl(null);

        if (!gmail.trim() || !gmail.includes('@')) {
            setAlert({ show: true, type: 'error', message: 'Please enter a valid email address.' });
            return;
        }

        setLoading(true);
        try {
            const res = await fetch('/api/auth/forgot-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gmail: gmail.trim() })
            });
            const data = await res.json();
            setSubmitted(true);
            setAlert({ show: true, type: 'success', message: data.message });
            if (data.dev_reset_url) {
                setDevResetUrl(data.dev_reset_url);
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

    return (
        <div style={cardStyle}>
            <h2 style={{ color: '#f8fafc', marginBottom: '8px' }}>Forgot Password</h2>
            <p style={{ color: '#94a3b8', marginBottom: '20px', fontSize: '0.9rem' }}>
                Enter your email address and we'll send you a reset link.
            </p>

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

            {devResetUrl && (
                <div style={{
                    padding: '10px 14px', borderRadius: '6px', marginBottom: '16px', fontSize: '0.85rem',
                    background: 'rgba(168,85,247,0.15)', color: '#c084fc', border: '1px solid rgba(168,85,247,0.3)',
                    wordBreak: 'break-all'
                }}>
                    <strong>Dev Mode:</strong> <a href={devResetUrl} style={{ color: '#c084fc' }}>{devResetUrl}</a>
                </div>
            )}

            {!submitted ? (
                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ color: '#f8fafc', fontWeight: '500', display: 'block', marginBottom: '6px' }}>Email Address</label>
                        <input
                            type="email"
                            value={gmail}
                            onChange={(e) => setGmail(e.target.value)}
                            placeholder="name@gmail.com"
                            required
                            style={{ width: '100%', padding: '10px 14px', borderRadius: '6px', background: '#0f172a', border: '1px solid #334155', color: '#f8fafc' }}
                        />
                    </div>
                    <button type="submit" disabled={loading} style={{ width: '100%', padding: '12px', borderRadius: '8px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: '600', fontSize: '1rem', marginBottom: '12px' }}>
                        {loading ? 'Sending...' : 'Send Reset Link'}
                    </button>
                    <div style={{ textAlign: 'center' }}>
                        <button type="button" onClick={onGoToLogin} style={{ background: 'none', border: 'none', color: '#60a5fa', cursor: 'pointer', fontSize: '0.9rem', textDecoration: 'underline' }}>
                            Back to Login
                        </button>
                    </div>
                </form>
            ) : (
                <div style={{ textAlign: 'center' }}>
                    <button type="button" onClick={onGoToLogin} style={{ padding: '10px 24px', borderRadius: '8px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: '600' }}>
                        Back to Login
                    </button>
                </div>
            )}
        </div>
    );
}
