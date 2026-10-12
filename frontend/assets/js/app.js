const API_BASE = "http://127.0.0.1:5000";

async function fetchJSON(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        credentials: "include",
        ...options
    });

    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }

    return response.json();
}

// Set a dashboard count based on the API response.
function setCount(elementId, data) {
    const element = document.getElementById(elementId);
    if (!element) return;

    if (Array.isArray(data)) {
        element.textContent = data.length;
    } else if (data && Array.isArray(data.students)) {
        element.textContent = data.students.length;
    } else if (data && Array.isArray(data.problems)) {
        element.textContent = data.problems.length;
    } else if (data && Array.isArray(data.submissions)) {
        element.textContent = data.submissions.length;
    } else if (data && typeof data.count === "number") {
        element.textContent = data.count;
    } else {
        element.textContent = "--";
    }
}

// Load the currently logged-in student's name and initials.
async function loadStudentProfile() {
    try {
        const student = await fetchJSON("/auth/me");

        const name = student.student_name || "Student";
        const initials = name
            .trim()
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map(part => part.charAt(0).toUpperCase())
            .join("") || "ST";

        // Update the sidebar profile name.
        document.querySelectorAll(".profile-text strong").forEach(element => {
            element.textContent = `${name}'s Workspace`;
        });

        // Update profile/avatar initials.
        document.querySelectorAll(".profile-avatar, .avatar, .user-avatar").forEach(element => {
            element.textContent = initials;
        });

        // Update common student-name placeholders if present.
        document.querySelectorAll("[data-student-name]").forEach(element => {
            element.textContent = name;
        });

    } catch (error) {
        console.warn("Student profile could not be loaded:", error.message);
    }
}

// Check whether the Flask backend is running.
async function checkBackend() {
    const statusText = document.getElementById("connectionStatus");
    const statusDot = document.querySelector(".status-dot");
    const backendValue = document.getElementById("backendValue");
    const backendFoot = document.getElementById("backendFoot");

    try {
        const result = await fetchJSON("/health");

        if (result.status !== "healthy") {
            throw new Error("Backend health check was unsuccessful");
        }

        if (statusText) statusText.textContent = "Backend online";

        if (statusDot) {
            statusDot.classList.add("online");
            statusDot.classList.remove("offline");
        }

        if (backendValue) backendValue.textContent = "Online";
        if (backendFoot) backendFoot.textContent = "Flask API is responding";

    } catch (error) {
        if (statusText) statusText.textContent = "Backend offline";

        if (statusDot) {
            statusDot.classList.add("offline");
            statusDot.classList.remove("online");
        }

        if (backendValue) backendValue.textContent = "Offline";
        if (backendFoot) backendFoot.textContent = "Start Flask to connect";

        console.warn("Backend health check failed:", error.message);
    }
}

// Check the MySQL connection.
async function checkDatabase() {
    try {
        const result = await fetchJSON("/db-health");

        if (result.status === "success") {
            console.info("MySQL connection confirmed.");
        } else {
            console.warn("The backend could not confirm the database connection.");
        }
    } catch (error) {
        console.warn("Database health check failed:", error.message);
    }
}

// Load student, problem and submission counts and recent activity.
async function loadDashboardCounts() {
    const endpoints = [
        { path: "/students", element: "studentCount" },
        { path: "/problems", element: "problemCount" },
        { path: "/submissions", element: "submissionCount" }
    ];

    for (const item of endpoints) {
        try {
            const data = await fetchJSON(item.path);
            setCount(item.element, data);
        } catch (error) {
            const element = document.getElementById(item.element);
            if (element) element.textContent = "--";

            console.warn(`${item.path} could not be loaded:`, error.message);
        }
    }

    const activityTitle = document.getElementById("activityTitle");
    const activityMessage = document.getElementById("activityMessage");

    if (!activityTitle || !activityMessage) return;

    try {
        const data = await fetchJSON("/submissions");

        const submissions = Array.isArray(data)
            ? data
            : Array.isArray(data.submissions)
                ? data.submissions
                : [];

        if (submissions.length > 0) {
            activityTitle.textContent =
                `${submissions.length} submission record(s) found`;

            activityMessage.textContent =
                "Your submission records are available. Keep practising to build your coding skills.";
        } else {
            activityTitle.textContent = "No submissions recorded yet";

            activityMessage.textContent =
                "Start a practice session and submit your first coding attempt.";
        }
    } catch (error) {
        activityTitle.textContent = "Activity is not available";

        activityMessage.textContent =
            "Check that Flask is running and the submissions API is responding.";
    }
}

// Set up mobile sidebar navigation.
function setupNavigation() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const menuButton = document.getElementById("menuButton");

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove("open");
        if (overlay) overlay.classList.remove("show");
    }

    if (menuButton && sidebar && overlay) {
        menuButton.addEventListener("click", () => {
            sidebar.classList.toggle("open");
            overlay.classList.toggle("show");
        });

        overlay.addEventListener("click", closeSidebar);
    }

    document.querySelectorAll(".nav-link").forEach(link => {
        link.addEventListener("click", () => {
            if (window.innerWidth <= 850) closeSidebar();
        });
    });
}

// Refresh dashboard information.
async function refreshDashboard() {
    await Promise.all([
        checkBackend(),
        checkDatabase(),
        loadStudentProfile(),
        loadDashboardCounts()
    ]);
}
async function logoutStudent() {
    const button = document.getElementById("logoutButton");
    if (button) button.disabled = true;

    try {
        await fetchJSON("/auth/logout", {
            method: "POST"
        });

        window.location.href = "../login.html";
    } catch (error) {
        console.error("Logout failed:", error);
        if (button) button.disabled = false;
        alert("Unable to log out. Please check that the backend is running.");
    }
}
document.addEventListener("DOMContentLoaded", () => {
    setupNavigation();
    refreshDashboard();

     const logoutButton = document.getElementById("logoutButton");

    if (logoutButton) {
        logoutButton.addEventListener("click", logoutStudent);
    }
});
