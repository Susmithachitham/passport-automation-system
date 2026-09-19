async function loadOfficerDashboard() {
    try {
        const [dashboard, user] = await Promise.all([apiRequest('/api/officer/dashboard'), apiRequest('/api/auth/me')]);
        const stats = dashboard.data;
        Object.entries(stats).forEach(([key, value]) => {
            const element = document.getElementById(key.replaceAll('_', '-'));
            if (element) element.textContent = String(value);
        });
        document.getElementById('officer-name').textContent = user.user.full_name;
    } catch (error) {
        if (error.message === 'Authentication required' || error.message === 'Insufficient permissions') window.location.href = '/login.html';
    }
}

document.getElementById('logout-button')?.addEventListener('click', async () => {
    await apiRequest('/api/auth/logout', { method: 'POST' }).catch(() => {});
    window.location.href = '/login.html';
});
loadOfficerDashboard();
