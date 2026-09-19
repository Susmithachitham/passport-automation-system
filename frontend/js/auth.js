function showMessage(message, type = "error") {
    const element = document.getElementById("form-message");
    if (!element) return;
    element.textContent = message;
    element.className = `message ${type}`;
}

function formDataToObject(form) {
    return Object.fromEntries(new FormData(form).entries());
}

async function loginUser(event) {
    event.preventDefault();
    try {
        const response = await apiRequest("/api/auth/login", {
            method: "POST",
            body: JSON.stringify(formDataToObject(event.currentTarget)),
        });
        showMessage(`Logged in as ${response.user.role}.`, "success");
        const redirectTarget = response.user.role === "applicant" ? "/dashboard.html" : "/";
        window.setTimeout(() => { window.location.href = redirectTarget; }, 700);
    } catch (error) {
        showMessage(error.message);
    }
}

async function registerUser(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.checkValidity()) {
        showMessage("Please complete all fields with valid information.");
        return;
    }
    try {
        await apiRequest("/api/auth/register", {
            method: "POST",
            body: JSON.stringify(formDataToObject(form)),
        });
        showMessage("Registration successful. Redirecting to login...", "success");
        window.setTimeout(() => { window.location.href = "/login.html"; }, 900);
    } catch (error) {
        showMessage(error.message);
    }
}

async function getCurrentUser() {
    return apiRequest("/api/auth/me");
}

async function logoutUser() {
    return apiRequest("/api/auth/logout", { method: "POST" });
}

document.getElementById("login-form")?.addEventListener("submit", loginUser);
document.getElementById("register-form")?.addEventListener("submit", registerUser);
