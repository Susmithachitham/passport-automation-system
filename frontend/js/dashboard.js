async function fetchDashboardData() {
    try {
        const response = await apiRequest('/api/applications');
        const applications = response.data || [];

        const total = applications.length;
        const draft = applications.filter((app) => app.status === 'DRAFT').length;
        const processing = applications.filter((app) => ['SUBMITTED', 'DOCUMENT_VERIFICATION', 'INTERVIEW_SCHEDULED', 'POLICE_VERIFICATION'].includes(app.status)).length;
        const approved = applications.filter((app) => ['APPROVED', 'PASSPORT_GENERATED', 'PASSPORT_DISPATCHED'].includes(app.status)).length;
        const rejected = applications.filter((app) => app.status === 'REJECTED').length;

        document.getElementById('total-applications').textContent = String(total);
        document.getElementById('draft-applications').textContent = String(draft);
        document.getElementById('processing-applications').textContent = String(processing);
        document.getElementById('approved-applications').textContent = String(approved);
        document.getElementById('rejected-applications').textContent = String(rejected);

        const container = document.getElementById('applications-container');
        if (!applications.length) {
            container.innerHTML = `
                <div class="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-10 text-center">
                    <p class="text-xl font-semibold text-slate-700">No passport applications yet.</p>
                    <p class="mt-2 text-slate-500">Start your first application</p>
                </div>
            `;
            return;
        }

        container.innerHTML = applications.slice(0, 5).map((app) => {
            const badgeClass = app.status === 'DRAFT'
                ? 'status-draft'
                : ['SUBMITTED', 'DOCUMENT_VERIFICATION', 'INTERVIEW_SCHEDULED', 'POLICE_VERIFICATION'].includes(app.status)
                    ? 'status-processing'
                    : app.status === 'REJECTED'
                        ? 'status-rejected'
                        : 'status-approved';

            return `
                <div class="application-card p-4">
                    <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                        <div>
                            <div class="flex items-center gap-3">
                                <span class="text-lg font-bold text-slate-900">${app.application_id}</span>
                                <span class="status-pill ${badgeClass}">${app.status}</span>
                            </div>
                            <div class="mt-2 flex flex-wrap gap-4 text-sm text-slate-500">
                                <span>Application Type: ${app.application_type}</span>
                                <span>Submitted Date: ${app.submitted_at ? new Date(app.submitted_at).toLocaleDateString() : 'N/A'}</span>
                                <span>Last Updated: ${new Date(app.updated_at || app.created_at).toLocaleDateString()}</span>
                            </div>
                        </div>
                        ${app.passport ? `<a class="button-secondary" href="/passport-details.html?application_id=${app.application_id}">View Passport</a>` : `<button class="button-secondary" data-application-id="${app.application_id}">View Details</button>`}
                    </div>
                </div>
            `;
        }).join('');

        container.querySelectorAll('[data-application-id]').forEach((button) => {
            button.addEventListener('click', () => {
                window.location.href = `/application-details.html?application_id=${button.dataset.applicationId}`;
            });
        });
    } catch (error) {
        document.getElementById('applications-container').innerHTML = `
            <div class="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-700">
                ${error.message || 'Unable to load dashboard data.'}
            </div>
        `;
    }
}

document.getElementById('apply-button')?.addEventListener('click', () => {
    window.location.href = '/new-application.html';
});

document.getElementById('logout-button')?.addEventListener('click', async () => {
    try {
        await apiRequest('/api/auth/logout', { method: 'POST' });
        window.location.href = '/login.html';
    } catch (error) {
        window.location.href = '/login.html';
    }
});

fetchDashboardData();
