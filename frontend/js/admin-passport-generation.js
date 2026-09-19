function showMessage(message, type = 'error') {
    const element = document.getElementById('generation-message');
    element.textContent = message;
    element.className = `message ${type}`;
}

function render(items) {
    const container = document.getElementById('eligible-list');
    container.innerHTML = items.length ? items.map((application) => `
        <div class="application-card flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
            <div>
                <p class="font-semibold text-blue-900">${application.application_id}</p>
                <p class="mt-1 text-sm text-slate-600">${application.applicant_name} · ${application.status}</p>
                <p class="mt-1 text-sm ${application.police_verification?.verification_status === 'CLEAR' ? 'text-emerald-700' : 'text-red-700'}">Police verification: ${application.police_verification?.verification_status || 'Missing'}</p>
                ${application.passport ? '<p class="mt-1 text-sm text-slate-500">Passport already generated</p>' : ''}
            </div>
            ${application.passport ? `<a class="button-secondary" href="/passport-details.html?application_id=${application.application_id}">View passport</a>` : `<button class="button-primary" data-application-id="${application.application_id}">Generate Passport</button>`}
        </div>
    `).join('') : '<p class="text-sm text-slate-500">No approved applications are currently available.</p>';

    container.querySelectorAll('[data-application-id]').forEach((button) => button.addEventListener('click', async () => {
        if (!window.confirm('Generate passport for this approved application? The number and dates will be assigned automatically.')) return;
        try {
            const response = await apiRequest(`/api/admin/passports/generate/${button.dataset.applicationId}`, { method: 'POST' });
            showMessage('Passport generated successfully.', 'success');
            render([{ ...items.find((item) => item.application_id === button.dataset.applicationId), passport: response.data }]);
        } catch (error) {
            showMessage(error.message);
        }
    }));
}

async function loadEligible() {
    try {
        const response = await apiRequest('/api/admin/passports/eligible');
        render(response.data);
    } catch (error) {
        if (error.message === 'Authentication required' || error.message === 'Insufficient permissions') window.location.href = '/login.html';
        else showMessage(error.message);
    }
}

document.getElementById('refresh-button')?.addEventListener('click', loadEligible);
document.getElementById('logout-button')?.addEventListener('click', async () => {
    await apiRequest('/api/auth/logout', { method: 'POST' }).catch(() => {});
    window.location.href = '/login.html';
});
loadEligible();
