const applicationId = new URLSearchParams(window.location.search).get('application_id');
const root = document.getElementById('details-root');

function esc(value) {
    const e = document.createElement('span');
    e.textContent = value ?? '';
    return e.innerHTML;
}
function formatDate(value) { return value ? new Date(value).toLocaleString() : 'N/A'; }
function card(title, content) { return `<section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><h2 class="text-lg font-bold text-slate-900">${title}</h2><div class="mt-4">${content}</div></section>`; }
function statusBadge(status) {
    const cls = status === 'REJECTED' ? 'status-rejected' : status === 'PASSPORT_DISPATCHED' || status === 'PASSPORT_GENERATED' || status === 'APPROVED' ? 'status-approved' : status === 'DRAFT' ? 'status-draft' : 'status-processing';
    return `<span class="status-pill ${cls}">${esc(status)}</span>`;
}

const WORKFLOW_STEPS = [
    { label: 'Application Created', key: 'DRAFT' },
    { label: 'Application Submitted', key: 'SUBMITTED' },
    { label: 'Document Verification', key: 'DOCUMENT_VERIFICATION' },
    { label: 'Interview Scheduled', key: 'INTERVIEW_SCHEDULED' },
    { label: 'Police Verification', key: 'POLICE_VERIFICATION' },
    { label: 'Approved', key: 'APPROVED' },
    { label: 'Passport Generated', key: 'PASSPORT_GENERATED' },
    { label: 'Passport Dispatched', key: 'PASSPORT_DISPATCHED' }
];

const STATUS_ORDER = ['DRAFT','SUBMITTED','DOCUMENT_VERIFICATION','INTERVIEW_SCHEDULED','POLICE_VERIFICATION','APPROVED','PASSPORT_GENERATED','PASSPORT_DISPATCHED'];

function renderTimeline(currentStatus, timelineData) {
    const isRejected = currentStatus === 'REJECTED';
    const currentIndex = STATUS_ORDER.indexOf(currentStatus);
    return `<div class="relative">
        <div class="space-y-3">
            ${WORKFLOW_STEPS.map((step, idx) => {
                const stepIndex = STATUS_ORDER.indexOf(step.key);
                const completed = stepIndex <= currentIndex && !isRejected && stepIndex !== -1;
                const isCurrent = step.key === currentStatus;
                const isRejectedStep = isRejected && idx === 4;
                let dotClass = 'bg-slate-200 border-slate-300';
                let textClass = 'text-slate-500';
                if (isRejected && completed) { /* keep completed styled before rejection */ }
                if (completed) { dotClass = 'bg-emerald-500 border-emerald-600'; textClass = 'text-emerald-700 font-semibold'; }
                if (isCurrent && !isRejected) { dotClass = 'bg-blue-600 border-blue-700 ring-4 ring-blue-100'; textClass = 'text-blue-700 font-bold'; }
                if (isRejected && idx > 4) { dotClass = 'bg-slate-100 border-slate-200'; textClass = 'text-slate-400'; }
                const check = completed ? '&#10003;' : (isCurrent ? '&#9679;' : '');
                const labelExtra = isCurrent ? ' (Current)' : completed ? ' (Completed)' : ' (Pending)';
                return `<div class="flex items-center gap-4">
                    <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold text-white ${dotClass}">${check}</span>
                    <span class="text-sm ${textClass}">${esc(step.label)}${labelExtra}</span>
                    ${isCurrent && !isRejected ? '<span class="ml-auto text-xs font-semibold text-blue-600">IN PROGRESS</span>' : ''}
                </div>`;
            }).join('')}
            ${isRejected ? `<div class="mt-4 rounded-xl border border-red-200 bg-red-50 p-4"><p class="text-sm font-bold text-red-700">Application Rejected</p><p class="mt-1 text-sm text-red-600">This application was rejected and cannot proceed further.</p></div>` : ''}
            ${currentStatus === 'PASSPORT_DISPATCHED' ? '<div class="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4"><p class="text-sm font-bold text-emerald-700">Passport Dispatched - Final Status</p></div>' : ''}
        </div>
    </div>`;
}

function render(application, statusInfo, dispatch, passport) {
    const personal = application.personal_details || {};
    const address = application.address_details || {};
    const family = application.family_details || {};
    const docs = application.documents || [];
    const payments = application.payments || [];
    const currentStatus = statusInfo?.status || application.status;
    document.getElementById('application-subtitle').textContent = `${application.application_id} \u00B7 ${application.application_type}`;
    root.innerHTML = `
        <div class="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:flex-row md:items-center md:justify-between">
            <div>
                <h2 class="text-2xl font-bold">${esc(application.application_id)}</h2>
                <p class="mt-1 text-sm text-slate-500">${esc(application.application_type)} \u00B7 Created ${formatDate(application.created_at)}</p>
            </div>
            <div class="flex flex-wrap items-center gap-3">${statusBadge(currentStatus)}<a class="button-ghost !px-3 !py-2 text-sm" href="/application-form.html?application_id=${encodeURIComponent(application.application_id)}">${application.status === 'DRAFT' ? 'Edit Application' : 'View Form Data'}</a></div>
        </div>

        <div class="grid gap-6 lg:grid-cols-3">
            <section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-1">
                <h2 class="text-lg font-bold">Status Timeline</h2>
                <p class="mt-1 text-sm text-slate-500">Track your application through every stage.</p>
                <div class="mt-6">${renderTimeline(currentStatus, statusInfo?.timeline)}</div>
                ${application.rejection_reason ? `<div class="mt-6 rounded-xl border border-red-200 bg-red-50 p-4"><p class="text-sm font-semibold text-red-700">Rejection Reason</p><p class="mt-1 text-sm text-red-600">${esc(application.rejection_reason)}</p></div>` : ''}
            </section>
            <div class="space-y-6 lg:col-span-2">
                ${card('Application Summary', `<div class="grid gap-4 text-sm md:grid-cols-2"><p><strong>Current Status:</strong> ${esc(currentStatus)}</p><p><strong>Application Type:</strong> ${esc(application.application_type)}</p><p><strong>Submitted:</strong> ${formatDate(application.submitted_at)}</p><p><strong>Last Updated:</strong> ${formatDate(application.updated_at)}</p><p><strong>Passport Number:</strong> ${esc(passport?.passport_number || 'Not yet generated')}</p><p><strong>Tracking Number:</strong> ${esc(dispatch?.tracking_number || 'Not yet dispatched')}</p></div>`)}
                ${passport ? card('Passport Information', `<div class="grid gap-4 text-sm md:grid-cols-2"><p><strong>Passport Number:</strong> ${esc(passport.passport_number)}</p><p><strong>Issue Date:</strong> ${esc(passport.issue_date)}</p><p><strong>Expiry Date:</strong> ${esc(passport.expiry_date)}</p><p><strong>Status:</strong> ${esc(passport.passport_status)}</p></div><a class="button-secondary mt-4 inline-flex" href="/passport-details.html?application_id=${encodeURIComponent(application.application_id)}">View Passport</a>`) : ''}
                ${dispatch ? card('Dispatch Information', `<div class="grid gap-4 text-sm md:grid-cols-2"><p><strong>Courier:</strong> ${esc(dispatch.courier_name)}</p><p><strong>Tracking:</strong> ${esc(dispatch.tracking_number)}</p><p><strong>Method:</strong> ${esc(dispatch.delivery_method)}</p><p><strong>Dispatch Date:</strong> ${formatDate(dispatch.dispatch_date)}</p><p class="md:col-span-2"><strong>Remarks:</strong> ${esc(dispatch.dispatch_remarks || 'None')}</p></div>`) : ''}
                ${card('Documents', docs.length ? `<div class="space-y-3">${docs.map(d => `<div class="flex flex-col gap-1 rounded-xl border border-slate-100 p-3 md:flex-row md:items-center md:justify-between"><div><p class="text-sm font-semibold">${esc(d.document_type)} <span class="status-pill ${d.verification_status === 'VERIFIED' ? 'status-approved' : d.verification_status === 'REJECTED' ? 'status-rejected' : 'status-processing'}">${esc(d.verification_status)}</span></p><p class="text-xs text-slate-500">${esc(d.original_filename)} \u00B7 ${esc(d.mime_type)}</p>${d.rejection_reason ? `<p class="text-xs text-red-600">Reason: ${esc(d.rejection_reason)}</p>` : ''}</div></div>`).join('')}` : '<p class="text-sm text-slate-500">No documents uploaded.</p>')}
                ${card('Payment', payments.length ? payments.map(p => `<div class="grid gap-3 text-sm md:grid-cols-3"><p><strong>Transaction:</strong> ${esc(p.transaction_id)}</p><p><strong>Amount:</strong> ${p.amount}</p><p><strong>Status:</strong> ${esc(p.payment_status)}</p></div>`).join('') : '<p class="text-sm text-slate-500">No payment recorded.</p>')}
                ${card('Personal & Address', `<div class="space-y-4 text-sm"><div class="grid gap-3 md:grid-cols-2">${Object.entries(personal).map(([k,v])=>`<p><strong>${esc(k.replaceAll('_',' '))}:</strong> ${esc(String(v))}</p>`).join('') || '<p>No personal details</p>'}</div><div class="grid gap-4 md:grid-cols-2"><div><h4 class="font-semibold">Current Address</h4><p class="mt-1 text-slate-600">${esc(Object.values(address.current_address||{}).join(', ')||'N/A')}</p></div><div><h4 class="font-semibold">Permanent Address</h4><p class="mt-1 text-slate-600">${esc(Object.values(address.permanent_address||{}).join(', ')||'N/A')}</p></div></div></div>`)}
            </div>
        </div>
    `;
}

async function load() {
    if (!applicationId) { root.innerHTML = '<div class="message error">Application ID is required.</div>'; return; }
    try {
        const [appRes, statusRes] = await Promise.all([
            apiRequest(`/api/applications/${applicationId}`),
            apiRequest(`/api/applications/${applicationId}/status`).catch(()=>null)
        ]);
        let passport = null, dispatch = null;
        try { passport = (await apiRequest(`/api/passports/${applicationId}`)).data; } catch(e) { if (!e.message.includes('not been generated') && !e.message.includes('not found') && !e.message.includes('Passport')) throw e; }
        try { dispatch = (await apiRequest(`/api/dispatch/${applicationId}`)).data; } catch(e) { if (!e.message.includes('not been recorded') && !e.message.includes('not found') && !e.message.includes('Dispatch')) throw e; }
        render(appRes.data, statusRes?.data, dispatch, passport);
    } catch (error) {
        if (error.message === 'Authentication required' || error.message === 'Insufficient permissions') { window.location.href = '/login.html'; return; }
        root.innerHTML = `<div class="message error">${esc(error.message)}</div>`;
    }
}
document.getElementById('logout-button')?.addEventListener('click', async () => { await apiRequest('/api/auth/logout', {method:'POST'}).catch(()=>{}); window.location.href='/login.html'; });
load();
