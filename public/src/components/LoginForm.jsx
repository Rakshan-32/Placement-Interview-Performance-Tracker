function LoginForm({ onLoginSuccess, onShowForgotPassword }) {
    const [gmail, setGmail] = React.useState('');
    const [password, setPassword] = React.useState('');
    const [showPassword, setShowPassword] = React.useState(false);
    const [loading, setLoading] = React.useState(false);
    const [alert, setAlert] = React.useState({ show: false, type: '', message: '' });

    const handleQuickFill = (demoGmail, demoPassword) => {
        setGmail(demoGmail);
        setPassword(demoPassword);
        setAlert({ show: false, type: '', message: '' });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setAlert({ show: false, type: '', message: '' });

        if (!gmail.trim()) {
            setAlert({ show: true, type: 'error', message: 'Please enter your Gmail address.' });
            return;
        }

        if (!password) {
            setAlert({ show: true, type: 'error', message: 'Please enter your password.' });
            return;
        }

        setLoading(true);

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gmail: gmail.trim(), password })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // Save role and uuid in browser localStorage as requested
                localStorage.setItem('auth_user', JSON.stringify(data.user));
                
                setAlert({ show: true, type: 'success', message: data.message || 'Logged in successfully!' });
                setTimeout(() => {
                    onLoginSuccess(data.user);
                }, 600);
            } else {
                setAlert({
                    show: true,
                    type: 'error',
                    message: data.message || 'Invalid Gmail or password'
                });
            }
        } catch (err) {
            console.error('React login error:', err);
            setAlert({
                show: true,
                type: 'error',
                message: 'Unable to connect to the authentication server.'
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="glass-card">
            <div className="brand-header">
                <div className="logo-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
                        <path d="M6 12v5c3 3 9 3 12 0v-5"/>
                    </svg>
                </div>
                <h2>Placement Portal (React)</h2>
                <p>Welcome back! Please sign in to your account.</p>
            </div>

            {/* React Dynamic Alert Box */}
            {alert.show && (
                <div className={`alert-box ${alert.type}`}>
                    <div className="alert-icon">
                        {alert.type === 'error' ? (
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="10"></circle>
                                <line x1="12" y1="8" x2="12" y2="12"></line>
                                <line x1="12" y1="16" x2="12.01" y2="16"></line>
                            </svg>
                        ) : (
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                                <polyline points="22 4 12 14.01 9 11.01"></polyline>
                            </svg>
                        )}
                    </div>
                    <div className="alert-message">{alert.message}</div>
                </div>
            )}

            {/* React Login Form */}
            <form onSubmit={handleSubmit} noValidate>
                <div className="input-group">
                    <label htmlFor="gmailInput">Gmail Address</label>
                    <div className="input-wrapper">
                        <span className="field-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                                <polyline points="22,6 12,13 2,6"></polyline>
                            </svg>
                        </span>
                        <input
                            type="email"
                            id="gmailInput"
                            placeholder="name@gmail.com"
                            value={gmail}
                            onChange={(e) => setGmail(e.target.value)}
                            required
                        />
                    </div>
                </div>

                <div className="input-group">
                    <label htmlFor="passwordInput">Password</label>
                    <div className="input-wrapper">
                        <span className="field-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                            </svg>
                        </span>
                        <input
                            type={showPassword ? 'text' : 'password'}
                            id="passwordInput"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                        <button
                            type="button"
                            className="toggle-password"
                            onClick={() => setShowPassword(!showPassword)}
                            title="Toggle Password Visibility"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                {showPassword ? (
                                    <>
                                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                                        <line x1="1" y1="1" x2="23" y2="23"></line>
                                    </>
                                ) : (
                                    <>
                                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                                        <circle cx="12" cy="12" r="3"></circle>
                                    </>
                                )}
                            </svg>
                        </button>
                    </div>
                </div>

                <button type="submit" className="submit-btn" disabled={loading}>
                    {loading ? (
                        <span className="btn-loader">
                            <svg className="spinner" viewBox="0 0 50 50">
                                <circle className="path" cx="25" cy="25" r="20" fill="none" strokeWidth="5"></circle>
                            </svg>
                        </span>
                    ) : (
                        <span className="btn-text">Sign In</span>
                    )}
                </button>
            </form>

            {onShowForgotPassword && (
                <div style={{ textAlign: 'center', marginTop: '12px' }}>
                    <button
                        type="button"
                        onClick={onShowForgotPassword}
                        style={{ background: 'none', border: 'none', color: '#60a5fa', cursor: 'pointer', fontSize: '0.9rem', textDecoration: 'underline' }}
                    >
                        Forgot Password?
                    </button>
                </div>
            )}

            <div className="demo-section">
                <span className="demo-title">Quick Test Accounts (Click to autofill):</span>
                <div className="demo-chips">
                    <button
                        type="button"
                        className="chip"
                        onClick={() => handleQuickFill('coordinator@gmail.com', 'coord123')}
                    >
                        <span className="chip-badge coordinator">Coordinator</span> coordinator@gmail.com
                    </button>
                    <button
                        type="button"
                        className="chip"
                        onClick={() => handleQuickFill('mentor@gmail.com', 'mentor123')}
                    >
                        <span className="chip-badge mentor" style={{ background: 'rgba(59,130,246,0.2)', color: '#60a5fa' }}>Mentor</span> mentor@gmail.com
                    </button>
                    <button
                        type="button"
                        className="chip"
                        onClick={() => handleQuickFill('dept.cse@gmail.com', 'dept123')}
                    >
                        <span className="chip-badge department" style={{ background: 'rgba(124,58,237,0.25)', color: '#c4b5fd' }}>Department</span> dept.cse@gmail.com
                    </button>
                    <button
                        type="button"
                        className="chip"
                        onClick={() => handleQuickFill('student@gmail.com', 'student123')}
                    >
                        <span className="chip-badge student">Student</span> student@gmail.com
                    </button>

                </div>
            </div>
        </div>
    );
}
