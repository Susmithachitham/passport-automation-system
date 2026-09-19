let currentPage = 1;

function showQueueMessage(message, type = 'error') {
    const element = document.getElementById('queue-message');
    element.textContent = message;
    element.className = `message ${type}`;
}

function badgeClass(status) {
    if (status === 'REJECTED') return 'status-rejected';
    if (status === 'POLICE_VERIFICATION' || status === 'APPROVED') return 'status-approved';
    if (status === 'SUBMITTED') return 'status-submitted';
    return 'status-processing';
}

async function loadApplications() {
    const params = new URLSearchParams({ page: String(currentPage), search: document.getElementById('search').value, status: document.getElementById('status').value, application_type: document.getElementById('application-type').value, sort: document.getElementById('sort').value });
    try {
        const response = await apiRequest(`/api/officer/applications?${params}`);
        const result = response.data;
        document.getElementById('applications-body').innerHTML = result.items.length ? result.items.map((application) => `
            <tr class="border-b border-slate-100 align-top"><td class="px-3 py-4 font-semibold text-blue-900">${application.application_id}</td><td class="px-3 py-4">${application.applicant_name}</td><td class="px-3 py-4">${application.application_type}</td><td class="px-3 py-4">${application.submitted_at ? new Date(application.submitted_at).toLocaleDateString() : 'N/A'}</td><td class="px-3 py-4"><span class="status-pill ${badgeClass(application.status)}">${application.status}</span></td><td class="px-3 py-4">${application.document_status}</td><td class="px-3 py-4">${application.interview?.status || 'Not scheduled'}</td><td class="px-3 py-4"><a class="button-secondary !px-3 !py-2 !text-xs" href="/officer-application-details.html?application_id=${application.application_id}">Review</a></td></tr>
        `).join('') : '<tr><td class="px-3 py-8 text-center text-slate-500" colspan="8">No applications match these filters.</td></tr>';
        document.getElementById('pagination').innerHTML = `<span>Page ${result.page} of ${Math.max(result.pages, 1)} (${result.total} applications)</span><span class="flex gap-2"><button id="previous-page" class="button-ghost !px-3 !py-2" ${result.page <= 1 ? 'disabled' : ''}>Previous</button><button id="next-page" class="button-ghost !px-3 !py-2" ${result.page >= result.pages ? 'disabled' : ''}>Next</button></span>`;
        document.getElementById('previous-page')?.addEventListener('click', () => { currentPage -= 1; loadApplications(); });
        document.getElementById('next-page')?.addEventListener('click', () => { currentPage += 1; loadApplications(); });
    } catch (error) {
        showQueueMessage(error.message);
    }
}

['search', 'status', 'application-type', 'sort'].forEach((id) => document.getElementById(id).addEventListener('input', () => { currentPage = 1; loadApplications(); }));
document.getElementById('logout-button')?.addEventListener('click', async () => { await apiRequest('/api/auth/logout', { method: 'POST' }).catch(() => {}); window.location.href = '/login.html'; });
loadApplications();
