const typeOptions = [
    { value: 'NEW', title: 'NEW PASSPORT', description: 'For applicants applying for a passport for the first time.', icon: '🛂' },
    { value: 'RENEWAL', title: 'RENEW PASSPORT', description: 'For renewal of an existing passport.', icon: '🔄' },
    { value: 'REISSUE', title: 'REISSUE PASSPORT', description: 'For replacement or reissue of an existing passport.', icon: '📝' },
];

let selectedType = '';

function showMessage(message, type = 'error') {
    const element = document.getElementById('form-message');
    if (!element) return;
    element.textContent = message;
    element.className = `message ${type}`;
    element.classList.remove('hidden');
}

function renderTypeOptions() {
    const container = document.getElementById('application-type-grid');
    if (!container) return;

    container.innerHTML = typeOptions.map((entry) => `
        <button class="application-type-card rounded-2xl border p-6 text-left transition ${selectedType === entry.value ? 'border-blue-900 bg-blue-50 shadow-md' : 'border-slate-200 bg-white'}" data-type="${entry.value}">
            <div class="flex items-center justify-between">
                <div class="text-3xl">${entry.icon}</div>
                <span class="rounded-full ${selectedType === entry.value ? 'bg-blue-900 text-white' : 'bg-slate-100 text-slate-700'} px-2 py-1 text-xs font-semibold">${selectedType === entry.value ? 'Selected' : 'Choose'}</span>
            </div>
            <h2 class="mt-5 text-xl font-bold uppercase text-slate-900">${entry.title}</h2>
            <p class="mt-3 text-sm leading-6 text-slate-600">${entry.description}</p>
        </button>
    `).join('');

    container.querySelectorAll('.application-type-card').forEach((button) => {
        button.addEventListener('click', () => {
            selectedType = button.dataset.type;
            renderTypeOptions();
            createApplication();
        });
    });
}

async function createApplication() {
    if (!selectedType) return;
    try {
        const response = await apiRequest('/api/applications', {
            method: 'POST',
            body: JSON.stringify({ application_type: selectedType }),
        });
        const application = response.data;
        window.location.href = `/application-form.html?application_id=${application.application_id}`;
    } catch (error) {
        showMessage(error.message, 'error');
    }
}

renderTypeOptions();
