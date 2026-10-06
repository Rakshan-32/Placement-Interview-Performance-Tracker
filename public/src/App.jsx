window.interventionHeaders = (user) => ({
    'X-User-Id': user?.uuid || '',
    'X-User-Role': user?.role || '',
    'X-Department': user?.department || 'CSE'
});

function App() {
    const [currentUser, setCurrentUser] = React.useState(() => {
        try {
            const saved = localStorage.getItem('auth_user');
            return saved ? JSON.parse(saved) : null;
        } catch (e) {
            return null;
        }
    });

    const [hashRoute, setHashRoute] = React.useState(() => window.location.hash || '');

    React.useEffect(() => {
        const onHash = () => setHashRoute(window.location.hash || '');
        window.addEventListener('hashchange', onHash);
        return () => window.removeEventListener('hashchange', onHash);
    }, []);

    const handleLogout = () => {
        localStorage.removeItem('auth_user');
        setCurrentUser(null);
        window.location.hash = '';
    };

    const navigateTo = (hash) => {
        window.location.hash = hash;
    };

    // Route: #/activate/<token>
    const activateMatch = hashRoute.match(/^#\/activate\/(.+)$/);
    if (activateMatch) {
        return (
            <div className="app-viewport">
                <main className="main-content">
                    <ActivateAccountView token={activateMatch[1]} onGoToLogin={() => navigateTo('')} />
                </main>
            </div>
        );
    }

    // Route: #/reset-password/<token>
    const resetMatch = hashRoute.match(/^#\/reset-password\/(.+)$/);
    if (resetMatch) {
        return (
            <div className="app-viewport">
                <main className="main-content">
                    <ResetPasswordView token={resetMatch[1]} onGoToLogin={() => navigateTo('')} />
                </main>
            </div>
        );
    }

    // Route: #/forgot-password
    if (hashRoute === '#/forgot-password') {
        return (
            <div className="app-viewport">
                <main className="main-content">
                    <ForgotPasswordView onGoToLogin={() => navigateTo('')} />
                </main>
            </div>
        );
    }

    return (
        <div className="app-viewport">
            <main className="main-content">
                {currentUser ? (
                    <Dashboard
                        user={currentUser}
                        onLogout={handleLogout}
                    />
                ) : (
                    <LoginForm
                        onLoginSuccess={(user) => setCurrentUser(user)}
                        onShowForgotPassword={() => navigateTo('#/forgot-password')}
                    />
                )}
            </main>
        </div>
    );
}
