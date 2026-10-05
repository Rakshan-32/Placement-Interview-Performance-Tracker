window.interventionHeaders = (user) => ({
    'X-User-Id': user?.uuid || '',
    'X-User-Role': user?.role || '',
    'X-Department': user?.department || 'CSE'
});

function App() {
    // Restore session from browser localStorage if present
    const [currentUser, setCurrentUser] = React.useState(() => {
        try {
            const saved = localStorage.getItem('auth_user');
            return saved ? JSON.parse(saved) : null;
        } catch (e) {
            return null;
        }
    });

    const handleLogout = () => {
        localStorage.removeItem('auth_user');
        setCurrentUser(null);
    };

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
                    />
                )}
            </main>
        </div>
    );
}
