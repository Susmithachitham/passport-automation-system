async function loadPoliceDashboard() {
    try {
        const [dashboard, user] = await Promise.all([apiRequest('/api/police/dashboard'), apiRequest('/api/auth/me')]);
        Object.entries(dashboard.data).forEach(([key, value]) => {
            const element = document.getElementById(key.replaceAll('_', '-'));
            if (element && !Array.isArray(value)) element.textContent = String(value);
        });
        document.getElementById('police-name').textContent = user.user.full_name;
        const recent = document.getElementById('recent-cases');
        recent.innerHTML = dashboard.data.recently_assigned_cases.length ? dashboard.data.recently_assigned_cases.map((id) => `<a class="application-card p-4" href="/police-application-details.html?application_id=${encodeURIComponent(id)}"><span class="font-semibold text-blue-900">${id}</span><span class="mt-1 block text-sm text-slate-500">Review case</span></a>`).join('') : '<p class="text-sm text-slate-500">No pending police verification cases.</p>';
    } catch (error) {
        if (error.message === 'Authentication required' || error.message === 'Insufficient permissions') window.location.href = '/login.html';
    }
}

document.getElementById('logout-button')?.addEventListener('click', async () => { await apiRequest('/api/auth/logout', { method: 'POST' }).catch(() => {}); window.location.href = '/login.html'; });
loadPoliceDashboard();
