const applicationId = new URLSearchParams(window.location.search).get('application_id');
const root = document.getElementById('passport-root');

function esc(value) {
    const element = document.createElement('span');
    element.textContent = value ?? '';
    return element.innerHTML;
}

async function loadPassport() {
    if (!applicationId) {
        root.innerHTML = '<div class="message error">Application ID is required.</div>';
        return;
    }
    try {
        const response = await apiRequest(`/api/passports/${applicationId}`);
        const passport = response.data;
        let dispatch = null;
        try {
            dispatch = (await apiRequest(`/api/dispatch/${applicationId}`)).data;
        } catch (dispatchError) {
            if (!dispatchError.message.includes('not been recorded')) throw dispatchError;
        }
        const statusTitle = passport.passport_status === 'PASSPORT_DISPATCHED' ? 'PASSPORT DISPATCHED' : 'PASSPORT GENERATED';
        const dispatchSection = dispatch ? `<section class="mt-6 border-t border-slate-200 pt-6"><h3 class="text-lg font-bold">Dispatch Information</h3><div class="mt-4 grid gap-5 text-sm md:grid-cols-2"><p><strong>Dispatch Date</strong><br>${esc(dispatch.dispatch_date)}</p><p><strong>Courier</strong><br>${esc(dispatch.courier_name)}</p><p><strong>Tracking Number</strong><br>${esc(dispatch.tracking_number)}</p><p><strong>Delivery Method</strong><br>${esc(dispatch.delivery_method)}</p></div></section>` : '<p class="mt-6 border-t border-slate-200 pt-6 text-sm text-slate-500">Passport Generated - Awaiting Dispatch</p>';
        root.innerHTML = `<section class="rounded-3xl border border-teal-200 bg-white p-8 shadow-lg"><p class="text-sm font-semibold uppercase tracking-[0.2em] text-teal-700">Simulated system-generated record</p><h2 class="mt-2 text-3xl font-bold">${statusTitle}</h2><div class="mt-8 grid gap-5 text-sm md:grid-cols-2"><p><strong>Application ID</strong><br>${esc(passport.application_id)}</p><p><strong>Passport Number</strong><br>${esc(passport.passport_number)}</p><p><strong>Issue Date</strong><br>${esc(passport.issue_date)}</p><p><strong>Expiry Date</strong><br>${esc(passport.expiry_date)}</p><p><strong>Application Status</strong><br>${esc(passport.passport_status)}</p><p><strong>Record Created</strong><br>${esc(passport.created_at)}</p></div>${dispatchSection}</section>`;
    } catch (error) {
        root.innerHTML = `<div class="message error">${esc(error.message)}</div>`;
    }
}

loadPassport();
