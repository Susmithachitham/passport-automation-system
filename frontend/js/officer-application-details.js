const applicationId = new URLSearchParams(window.location.search).get('application_id');
const root = document.getElementById('details-root');

function esc(value) { const element = document.createElement('span'); element.textContent = value ?? ''; return element.innerHTML; }
function formatDate(value) { return value ? new Date(value).toLocaleString() : 'N/A'; }
function card(title, content) { return `<section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><h2 class="text-lg font-bold text-slate-900">${title}</h2><div class="mt-4">${content}</div></section>`; }

async function post(path, body) { return apiRequest(path, { method: 'POST', body: JSON.stringify(body || {}) }); }

function render(application) {
    const personal = application.personal_details || {};
    const address = application.address_details || {};
    const current = address.current_address || {};
    const permanent = address.permanent_address || {};
    const family = application.family_details || {};
    const passport = application.passport_details || {};
    const interview = application.interview;
    const documents = application.documents || [];
    const payments = application.payments || [];
    root.innerHTML = `
        <div class="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:flex-row md:items-center md:justify-between"><div><p class="text-sm font-semibold uppercase tracking-[0.2em] text-teal-700">Officer Review</p><h2 class="mt-1 text-2xl font-bold">${esc(application.application_id)}</h2><p class="mt-1 text-slate-500">${esc(application.applicant?.full_name)} · ${esc(application.application_type)}</p></div><span class="status-pill ${application.status === 'REJECTED' ? 'status-rejected' : 'status-processing'}">${esc(application.status)}</span></div>
        <div id="action-message" class="message hidden"></div>
        ${card('Application Information', `<div class="grid gap-4 text-sm md:grid-cols-3"><p><strong>Created:</strong> ${formatDate(application.created_at)}</p><p><strong>Submitted:</strong> ${formatDate(application.submitted_at)}</p><p><strong>Updated:</strong> ${formatDate(application.updated_at)}</p><p><strong>Documents:</strong> ${esc(application.document_status)}</p><p><strong>Forwarded:</strong> ${formatDate(application.forwarded_at)}</p><p><strong>Rejection:</strong> ${esc(application.rejection_reason || 'None')}</p></div>`)}
        ${card('Applicant Information', `<div class="grid gap-4 text-sm md:grid-cols-3">${[['Full Name', personal.full_name], ['Date of Birth', personal.date_of_birth], ['Gender', personal.gender], ['Place of Birth', personal.place_of_birth], ['Nationality', personal.nationality], ['Mobile', personal.mobile_number], ['Email', personal.email]].map(([label, value]) => `<p><strong>${label}:</strong> ${esc(value || application.applicant?.[label === 'Full Name' ? 'full_name' : label.toLowerCase()])}</p>`).join('')}</div>`)}
        ${card('Address and Family', `<div class="grid gap-6 text-sm md:grid-cols-2"><div><h3 class="font-semibold">Current Address</h3><p class="mt-2">${esc(Object.values(current).filter(Boolean).join(', ')) || 'N/A'}</p><h3 class="mt-4 font-semibold">Permanent Address</h3><p class="mt-2">${esc(Object.values(permanent).filter(Boolean).join(', ')) || 'N/A'}</p></div><div><p><strong>Father:</strong> ${esc(family.father_name || personal.father_name)}</p><p class="mt-2"><strong>Mother:</strong> ${esc(family.mother_name || personal.mother_name)}</p><p class="mt-2"><strong>Spouse:</strong> ${esc(family.spouse || 'N/A')}</p><p class="mt-2"><strong>Guardian:</strong> ${esc(family.guardian || 'N/A')}</p></div></div>`)}
        ${card('Passport Details', `<div class="grid gap-4 text-sm md:grid-cols-3">${Object.entries(passport).map(([key, value]) => `<p><strong>${key.replaceAll('_', ' ')}:</strong> ${esc(value)}</p>`).join('') || '<p>No passport details recorded.</p>'}</div>`)}
        ${card('Documents', `<div class="space-y-3">${documents.length ? documents.map((document) => `<div class="rounded-xl border border-slate-200 p-4"><div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between"><div><p class="font-semibold">${esc(document.document_type)} <span class="status-pill ${document.verification_status === 'VERIFIED' ? 'status-approved' : document.verification_status === 'REJECTED' ? 'status-rejected' : 'status-processing'}">${esc(document.verification_status)}</span></p><p class="mt-1 text-sm text-slate-500">${esc(document.original_filename)} · ${document.file_size} bytes · ${esc(document.mime_type)} · uploaded ${formatDate(document.uploaded_at)}</p><p class="mt-1 text-sm text-red-700">${esc(document.rejection_reason || document.verification_remarks || '')}</p></div><div class="flex gap-2"><button class="button-secondary !px-3 !py-2 !text-xs" data-verify="${document.id}">Verify</button><button class="button-ghost !px-3 !py-2 !text-xs" data-reject="${document.id}">Reject</button></div></div></div>`).join('') : '<p class="text-slate-500">No documents uploaded.</p>'}</div>`)}
        ${card('Payment', payments.length ? payments.map((payment) => `<div class="grid gap-3 text-sm md:grid-cols-4"><p><strong>Status:</strong> ${esc(payment.payment_status)}</p><p><strong>Transaction:</strong> ${esc(payment.transaction_id)}</p><p><strong>Amount:</strong> ${payment.amount}</p><p><strong>Date:</strong> ${formatDate(payment.paid_at)}</p></div>`).join('') : '<p class="text-slate-500">No payment recorded.</p>')}
        ${card('Interview', `<div class="grid gap-4 text-sm md:grid-cols-4"><p><strong>Status:</strong> ${esc(interview?.status || 'Not scheduled')}</p><p><strong>Date:</strong> ${esc(interview?.scheduled_date || 'N/A')}</p><p><strong>Time:</strong> ${esc(interview?.scheduled_time || 'N/A')}</p><p><strong>Location:</strong> ${esc(interview?.location || 'N/A')}</p></div><p class="mt-3 text-sm text-slate-600">${esc(interview?.officer_remarks || '')}</p><div class="mt-4 flex flex-wrap gap-2">${!interview && application.status === 'DOCUMENT_VERIFICATION' ? '<button id="schedule-button" class="button-primary">Schedule interview</button>' : ''}${interview?.status === 'SCHEDULED' ? '<button id="complete-button" class="button-secondary">Complete interview</button><button id="missed-button" class="button-ghost">Mark missed</button>' : ''}</div>`)}
        ${card('Officer Decision', `<div class="flex flex-wrap gap-3">${application.status === 'INTERVIEW_SCHEDULED' && interview?.status === 'COMPLETED' ? '<button id="forward-button" class="button-primary">Forward to Police</button>' : ''}${['SUBMITTED', 'DOCUMENT_VERIFICATION', 'INTERVIEW_SCHEDULED'].includes(application.status) ? '<button id="reject-button" class="button-ghost">Reject application</button>' : ''}</div>`)}
    `;
    bindActions(application);
}

function showMessage(message, type = 'error') { const element = document.getElementById('action-message'); element.textContent = message; element.className = `message ${type}`; }

async function bindActions(application) {
    document.querySelectorAll('[data-verify]').forEach((button) => button.addEventListener('click', async () => { try { await post(`/api/officer/applications/${applicationId}/documents/${button.dataset.verify}/verify`); await loadApplication(); } catch (error) { showMessage(error.message); } }));
    document.querySelectorAll('[data-reject]').forEach((button) => button.addEventListener('click', async () => { const reason = window.prompt('Enter a meaningful rejection reason'); if (!reason) return; try { await post(`/api/officer/applications/${applicationId}/documents/${button.dataset.reject}/reject`, { reason }); await loadApplication(); } catch (error) { showMessage(error.message); } }));
    document.getElementById('schedule-button')?.addEventListener('click', async () => { const scheduled_date = window.prompt('Interview date (YYYY-MM-DD)'); const scheduled_time = window.prompt('Interview time (HH:MM)'); const location = window.prompt('Interview location'); const officer_remarks = window.prompt('Instructions or remarks') || ''; try { await post(`/api/officer/applications/${applicationId}/interview`, { scheduled_date, scheduled_time, location, officer_remarks }); await loadApplication(); } catch (error) { showMessage(error.message); } });
    document.getElementById('complete-button')?.addEventListener('click', () => completeInterview('COMPLETED'));
    document.getElementById('missed-button')?.addEventListener('click', () => completeInterview('MISSED'));
    document.getElementById('forward-button')?.addEventListener('click', async () => { try { await post(`/api/officer/applications/${applicationId}/forward-to-police`); await loadApplication(); } catch (error) { showMessage(error.message); } });
    document.getElementById('reject-button')?.addEventListener('click', async () => { const reason = window.prompt('Enter a meaningful application rejection reason'); if (!reason) return; try { await post(`/api/officer/applications/${applicationId}/reject`, { reason }); await loadApplication(); } catch (error) { showMessage(error.message); } });
}

async function completeInterview(status) { const officer_remarks = window.prompt('Officer remarks') || ''; try { await post(`/api/officer/applications/${applicationId}/interview/complete`, { status, officer_remarks }); await loadApplication(); } catch (error) { showMessage(error.message); } }
async function loadApplication() { if (!applicationId) { window.location.href = '/officer-applications.html'; return; } try { const response = await apiRequest(`/api/officer/applications/${applicationId}`); render(response.data); } catch (error) { root.innerHTML = `<div class="message error">${esc(error.message)}</div>`; } }
document.getElementById('logout-button')?.addEventListener('click', async () => { await apiRequest('/api/auth/logout', { method: 'POST' }).catch(() => {}); window.location.href = '/login.html'; });
loadApplication();
