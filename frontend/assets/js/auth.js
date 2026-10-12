
const API_BASE = "http://127.0.0.1:5000";

async function authRequest(endpoint, data) {
    const response = await fetch(`${API_BASE}/auth/${endpoint}`, {
        method: "POST",
        credentials: "include",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });

    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.error || "Something went wrong");
    }

    return result;
}

async function signupStudent(studentName, email, password) {
    return authRequest("signup", {
        student_name: studentName.trim(),
        email: email.trim(),
        password: password
    });
}

async function loginStudent(email, password) {
    return authRequest("login", {
        email: email.trim(),
        password: password
    });
}

async function logoutStudent() {
    return authRequest("logout", {});
}

async function getLoggedInStudent() {
    const response = await fetch(`${API_BASE}/auth/me`, {
        credentials: "include"
    });

    if (!response.ok) {
        return null;
    }

    return response.json();
}
