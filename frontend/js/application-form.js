const params = new URLSearchParams(window.location.search);
const applicationId = params.get('application_id');

async function loadApplication() {
    if (!applicationId) {
        window.location.href = '/dashboard.html';
        return;
    }

    try {
        const response = await apiRequest(`/api/applications/${applicationId}`);
        const application = response.data;
        const root = document.getElementById('application-form-root');

        root.innerHTML = `
            <div class="space-y-6">
                <div>
                    <h2 class="text-2xl font-bold">Personal Details</h2>
                    <p class="mt-2 text-slate-600">Complete your profile details to continue the application.</p>
                </div>
                <form id="application-form" class="grid gap-5 md:grid-cols-2">
                    <label class="field-label">Full Name<input class="field-input" name="full_name" value="${application.personal_details?.full_name || ''}" required></label>
                    <label class="field-label">Date of Birth<input class="field-input" name="date_of_birth" type="date" value="${application.personal_details?.date_of_birth || ''}" required></label>
                    <label class="field-label">Gender<select class="field-input" name="gender"><option value="">Select</option><option value="Male" ${application.personal_details?.gender === 'Male' ? 'selected' : ''}>Male</option><option value="Female" ${application.personal_details?.gender === 'Female' ? 'selected' : ''}>Female</option><option value="Other" ${application.personal_details?.gender === 'Other' ? 'selected' : ''}>Other</option></select></label>
                    <label class="field-label">Place of Birth<input class="field-input" name="place_of_birth" value="${application.personal_details?.place_of_birth || ''}" required></label>
                    <label class="field-label">Father's Name<input class="field-input" name="father_name" value="${application.personal_details?.father_name || ''}" required></label>
                    <label class="field-label">Mother's Name<input class="field-input" name="mother_name" value="${application.personal_details?.mother_name || ''}" required></label>
                    <label class="field-label">Marital Status<select class="field-input" name="marital_status"><option value="">Select</option><option value="Single" ${application.personal_details?.marital_status === 'Single' ? 'selected' : ''}>Single</option><option value="Married" ${application.personal_details?.marital_status === 'Married' ? 'selected' : ''}>Married</option><option value="Divorced" ${application.personal_details?.marital_status === 'Divorced' ? 'selected' : ''}>Divorced</option><option value="Widowed" ${application.personal_details?.marital_status === 'Widowed' ? 'selected' : ''}>Widowed</option></select></label>
                    <label class="field-label">Nationality<input class="field-input" name="nationality" value="${application.personal_details?.nationality || ''}" required></label>
                    <label class="field-label">Mobile Number<input class="field-input" name="mobile_number" value="${application.personal_details?.mobile_number || ''}" required></label>
                    <label class="field-label md:col-span-2">Email<input class="field-input" name="email" type="email" value="${application.personal_details?.email || ''}" required></label>
                    <div class="md:col-span-2 flex justify-end">
                        <button type="submit" class="button-primary">Save and continue</button>
                    </div>
                </form>
            </div>
        `;

        document.getElementById('application-form').addEventListener('submit', async (event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const payload = {
                personal_details: {
                    full_name: form.get('full_name'),
                    date_of_birth: form.get('date_of_birth'),
                    gender: form.get('gender'),
                    place_of_birth: form.get('place_of_birth'),
                    father_name: form.get('father_name'),
                    mother_name: form.get('mother_name'),
                    marital_status: form.get('marital_status'),
                    nationality: form.get('nationality'),
                    mobile_number: form.get('mobile_number'),
                    email: form.get('email'),
                },
            };

            try {
                await apiRequest(`/api/applications/${applicationId}`, {
                    method: 'PUT',
                    body: JSON.stringify(payload),
                });
                window.location.href = `/application-form.html?application_id=${applicationId}`;
            } catch (error) {
                alert(error.message);
            }
        });
    } catch (error) {
        alert(error.message);
    }
}

loadApplication();
