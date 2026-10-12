
const API_BASE = "http://127.0.0.1:5000";

let editor = null;
let problems = [];
let selectedProblem = null;
let selectedStudent = null;

let attemptCount = 0;
let executionCount = 0;
let errorCount = 0;
let startedAt = Date.now();

let latestSubmissionId = null;
let latestSubmittedCode = null;

const $ = id => document.getElementById(id);

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...(options.headers || {})
        }
    });

    const text = await response.text();
    let data = {};

    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        throw new Error(`Invalid server response (${response.status}).`);
    }

    if (!response.ok) {
        throw new Error(
            data.error || data.message || `Request failed (${response.status}).`
        );
    }

    return data;
}


async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...(options.headers || {})
        }
    });

    const text = await response.text();
    let data = {};

    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        throw new Error(`Invalid server response (${response.status}).`);
    }

    if (!response.ok) {
        throw new Error(
            data.error || data.message || `Request failed (${response.status}).`
        );
    }

    return data;
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
    const avatar = document.getElementById("userInitials");

    // Display the name saved during login.
    const savedName = localStorage.getItem("studentName");

    if (savedName && avatar) {
        avatar.textContent = getUserInitials(savedName);
    }

    // Try refreshing the name from the backend.
    try {
        const student = await apiRequest("/auth/me");
        const name = student.student_name || savedName || "Student";

        localStorage.setItem("studentName", name);

        if (avatar) {
            avatar.textContent = getUserInitials(name);
        }
    } catch (error) {
        console.warn(
            "Using the saved student name:",
            error.message
        );
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

 
function getUserInitials(name) {
    if (!name || typeof name !== "string") {
        return "ST";
    }

    const parts = name.trim().split(/\s+/).filter(Boolean);

    if (parts.length === 0) {
        return "ST";
    }

    if (parts.length === 1) {
        return parts[0].charAt(0).toUpperCase();
    }

    return (
        parts[0].charAt(0) +
        parts[parts.length - 1].charAt(0)
    ).toUpperCase();
}


async function loadStudentProfile() {
    try {
        const student = await apiRequest("/auth/me");
        const name = student.student_name || "Student";
        const initials = getUserInitials(name);

        const avatar = document.getElementById("userInitials");
        if (avatar) avatar.textContent = initials;
    } catch (error) {
        console.warn("Could not load student profile:", error.message);
    }
}

function getList(data, keys) {
    if (Array.isArray(data)) return data;

    for (const key of keys) {
        if (Array.isArray(data?.[key])) return data[key];
    }

    return [];
}

function showMessage(id, message) {
    const element = $(id);
    if (element) element.textContent = String(message);
}

function updateMetrics() {
    showMessage("attemptCount", attemptCount);
    showMessage("executionCount", executionCount);
    showMessage("errorCount", errorCount);
}

function updateConnection(online) {
    showMessage(
        "connectionStatus",
        online ? "Backend online" : "Backend offline"
    );

    const dot = document.querySelector(".status-dot");

    if (dot) {
        dot.classList.toggle("online", online);
        dot.classList.toggle("offline", !online);
    }
}

function problemId(problem) {
    return problem?.problem_id ?? problem?.id;
}

function studentId(student) {
    return student?.student_id ?? student?.id;
}

async function checkBackend() {
    try {
        const result = await apiRequest("/health");

        if (result.status !== "healthy") {
            throw new Error("Backend health check failed.");
        }

        updateConnection(true);
    } catch (error) {
        updateConnection(false);
        console.error("Backend connection:", error.message);
    }
}

/* -------------------- Problem management -------------------- */

function renderProblem(problem) {
    selectedProblem = problem || null;

    latestSubmissionId = null;
    latestSubmittedCode = null;

    if (!problem) {
        showMessage("problemTitle", "No problem selected");
        showMessage(
            "problemDescription",
            "Choose a saved problem or create your own."
        );
        showMessage("difficultyLabel", "Difficulty: —");
        return;
    }

    showMessage(
        "problemTitle",
        problem.problem_title ?? problem.title ?? "Coding problem"
    );

    showMessage(
        "problemDescription",
        problem.problem_description ??
            problem.description ??
            "No description available."
    );

    showMessage(
        "difficultyLabel",
        `Difficulty: ${problem.difficulty ?? "Not specified"}`
    );

    showMessage(
        "problemStatus",
        `Concept: ${problem.concept || "Not specified"}. Work on your solution in the editor.`
    );
}

function addProblemToDropdown(problem) {
    const id = problemId(problem);
    if (id == null) return;

    const select = $("problemSelect");

    let option = [...select.options].find(
        item => item.value === String(id)
    );

    if (!option) {
        option = new Option(
            `${id} — ${problem.problem_title ?? problem.title}`,
            String(id)
        );
        select.add(option);
    }

    select.value = String(id);
    renderProblem(problem);
}

async function loadProblems() {
    const select = $("problemSelect");

    try {
        problems = getList(
            await apiRequest("/problems"),
            ["problems", "data", "results"]
        );

        select.replaceChildren();

        if (!problems.length) {
            select.add(new Option("No saved problems yet", ""));
            renderProblem(null);
            return;
        }

        select.add(new Option("Select a saved problem...", ""));

        problems.forEach(problem => {
            const id = problemId(problem);

            if (id != null) {
                select.add(
                    new Option(
                        `${id} — ${problem.problem_title ?? problem.title}`,
                        String(id)
                    )
                );
            }
        });

        select.addEventListener("change", () => {
            const problem = problems.find(
                item => String(problemId(item)) === select.value
            );

            renderProblem(problem);

            showMessage(
                "predictionResult",
                "Submit an attempt for this problem before requesting a prediction."
            );
        });

        select.value = String(problemId(problems[0]));
        renderProblem(problems[0]);
    } catch (error) {
        select.replaceChildren(new Option("Could not load problems", ""));
        renderProblem(null);
        showMessage("problemStatus", error.message);
    }
}

async function loadStudents() {
    try {
        const data = await apiRequest("/students");
        const students = getList(data, ["students", "data", "results"]);

        selectedStudent =
            students.find(student => studentId(student) != null) ?? null;

        if (!selectedStudent) {
            showMessage(
                "submissionResult",
                "No registered student found. Create a student record before submitting."
            );
        }
    } catch (error) {
        selectedStudent = null;
        console.error("Students API:", error.message);

        showMessage(
            "submissionResult",
            "Could not load students. Check the Students API."
        );
    }
}

/* -------------------- Monaco editor -------------------- */

function setupEditor() {
    if (typeof require === "undefined") {
        showMessage(
            "submissionResult",
            "Monaco Editor did not load. Check your internet connection."
        );
        return;
    }

    require.config({
        paths: {
            vs: "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs"
        }
    });

    require(["vs/editor/editor.main"], () => {
        editor = monaco.editor.create($("editor"), {
            value: 'print("Hello from Python!")\n',
            language: "python",
            theme: "vs-dark",
            automaticLayout: true,
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            padding: { top: 14 }
        });

        $("languageSelect").addEventListener("change", event => {
            const languages = {
                python: "python",
                java: "java",
                javascript: "javascript",
                c: "c"
            };

            monaco.editor.setModelLanguage(
                editor.getModel(),
                languages[event.target.value] || "plaintext"
            );
            

const starterCode = {
    python: 'print("Hello from Python!")',

    java: `public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");
    }
}`,

    javascript: 'console.log("Hello from JavaScript!");',

    c: `#include <stdio.h>
int main(void) {
    printf("Hello from C!\\n");
    return 0;
}`
};



const currentLanguage = event.target.value;

if (starterCode[currentLanguage]) {
    editor.setValue(starterCode[currentLanguage]);
}

            const language = event.target.value;
            const isSupported = ["python", "java", "javascript", "c"].includes(language);
            $("runCodeButton").disabled = !isSupported;

            
showConsoleStatus(
    isSupported ? "Ready" : "Language not supported",
    isSupported ? "" : "error"
);

if (!isSupported) {
    showMessage(
        "consoleOutput",
        "Python, Java, and JavaScript execution are currently supported."
    );
    showMessage("consoleMeta", "Execution time: —");
}

        });
    }, error => {
        console.error("Monaco Editor:", error);
        showMessage("submissionResult", "Could not initialise the code editor.");
    });
}

function showConsoleStatus(message, type = "") {
    const status = $("consoleStatus");
    if (!status) return;

    status.textContent = message;
    status.className = `console-status ${type}`.trim();
}

/* -------------------- Execution history -------------------- */

async function loadExecutionHistory() {
    const status = $("executionHistoryStatus");
    const list = $("executionHistoryList");

    if (!status || !list) return;

    status.textContent = "Loading execution history...";

    try {
        const data = await apiRequest("/executions?limit=50");
        const executions = Array.isArray(data.executions)
            ? data.executions
            : [];

        list.replaceChildren();

        if (executions.length === 0) {
            status.textContent = "No saved executions yet.";
            const empty = document.createElement("p");
            empty.textContent = "Run some Python code to build your history.";
            list.appendChild(empty);
            return;
        }

        status.textContent =
            `Showing ${executions.length} recent execution(s).`;

        executions.forEach(item => {
            const card = document.createElement("article");
            card.className = "execution-history-item";

            const heading = document.createElement("h4");
            heading.textContent =
                `Execution #${item.execution_id} — ` +
                String(item.event_type || "Unknown event")
                    .replaceAll("_", " ");

            card.appendChild(heading);

            const details = document.createElement("p");
            details.className = "execution-history-details";

            const duration = item.execution_time_ms == null
                ? "Not available"
                : `${item.execution_time_ms} ms`;

            details.textContent =
                `Date: ${item.created_at || "Unknown"} | ` +
                `Duration: ${duration} | ` +
                `Timed out: ${item.timed_out ? "Yes" : "No"} | ` +
                `Submission: ${item.submission_id ?? "Not linked"}`;

            card.appendChild(details);

            const output = document.createElement("pre");
            output.className = "execution-history-output";

            const stdout = item.stdout || "";
            const stderr = item.stderr || "";

            output.textContent = [
                stdout ? `Output:\n${stdout}` : "",
                stderr ? `Error:\n${stderr}` : ""
            ].filter(Boolean).join("\n\n") || "No output recorded.";

            card.appendChild(output);
            list.appendChild(card);
        });
    } catch (error) {
        status.textContent =
            `Could not load execution history: ${error.message}`;
    }
}

/* -------------------- Run Python code -------------------- */


async function runCode() {
    if (!editor) {
        showMessage("consoleOutput", "The editor is not ready yet.");
        return;
    }

    const language = $("languageSelect").value;

    if (!["python", "java", "javascript", "c"].includes(language)) {
        showConsoleStatus("Language not supported", "error");
        showMessage(
            "consoleOutput",
            "Python, Java, and JavaScript execution are currently supported."
        );
        return;
    }

    const code = editor.getValue();

    if (!code.trim()) {
        showConsoleStatus("No code", "error");
        showMessage("consoleOutput", `Write some ${language} code first.`);
        return;
    }

    const canLinkToSubmission =
        latestSubmissionId !== null &&
        latestSubmittedCode === code &&
        selectedProblem !== null;

    const button = $("runCodeButton");
    button.disabled = true;
    button.innerHTML = '<i class="bi bi-hourglass-split"></i> Running...';

    showConsoleStatus("Running...");
    showMessage("consoleOutput", `Executing ${language} code...`);
    showMessage("consoleMeta", "Execution time: measuring...");

    let executionWasRecorded = false;

    try {
        const payload = { code };

        if (canLinkToSubmission) {
            payload.submission_id = latestSubmissionId;
        }

        const endpoint = {
    python: "/execute",
    java: "/execute/java",
    javascript: "/execute/javascript",
    c: "/execute/c"
}[language];

        const result = await apiRequest(endpoint, {
            method: "POST",
            body: JSON.stringify(payload)
        });

        executionCount++;

        
const output = [
    result.stdout || result.output || "",
    result.stderr || "",
    result.error || ""
].filter(Boolean).join("\n");

showMessage(
    "consoleOutput",
    output || (
        result.success
            ? "Program finished without producing output."
            : "Execution failed. Check the backend terminal."
    )
);


        $("consoleOutput").classList.toggle(
            "error-output",
            !result.success
        );

        const duration = result.execution_time_ms;

        showMessage(
            "consoleMeta",
            `Execution time: ${duration == null ? "Not provided" : `${duration} ms`}` +
            (result.timed_out ? " · Timed out" : "") +
            (result.output_truncated ? " · Output truncated" : "")
        );

        if (!result.success) {
            errorCount++;
            showConsoleStatus(
                result.timed_out ? "Timed out" : "Finished with errors",
                "error"
            );
        } else {
            showConsoleStatus("Executed successfully", "success");
        }

        updateMetrics();

        executionWasRecorded = result.execution_logged === true;

        if (canLinkToSubmission && executionWasRecorded) {
            showMessage(
                "problemStatus",
                "Execution completed and recorded against your submitted attempt."
            );
        } else {
            showMessage(
                "problemStatus",
                result.success
                    ? `${language} execution completed. Submit this code to associate future runs with an attempt.`
                    : `${language} execution failed or timed out. Review the console, then submit this code to associate future runs with an attempt.`
            );
        }
    } catch (error) {
        showConsoleStatus("Request failed", "error");

        showMessage(
            "consoleOutput",
            `Could not execute ${language} code: ${error.message}`
        );

        showMessage(
            "consoleMeta",
            "Check that Flask is running and the execution endpoint is registered."
        );
    } finally {
        button.disabled = !["python", "java", "javascript", "c"].includes(
    $("languageSelect").value
);
        button.innerHTML = '<i class="bi bi-play-fill"></i> Run Code';

        await loadExecutionHistory();
    }
}

async function recordManualError() {
    errorCount++;
    updateMetrics();

    if (latestSubmissionId === null) {
        showMessage(
            "problemStatus",
            "Error counted locally. Submit your code first to save this event to the database."
        );
        return;
    }

    try {
        await apiRequest(
            `/submissions/${latestSubmissionId}/behaviour`,
            {
                method: "POST",
                body: JSON.stringify({
                    event_type: "error"
                })
            }
        );

        showMessage(
            "problemStatus",
            "Manual error recorded successfully."
        );
    } catch (error) {
        showMessage(
            "problemStatus",
            `Error counted locally, but database logging failed: ${error.message}`
        );
    }
}


/* -------------------- Create custom problem -------------------- */

async function createCustomProblem(event) {
    event.preventDefault();

    const button = $("createProblemButton");
    const message = $("customProblemMessage");

    const title = $("customProblemTitle").value.trim();
    const description = $("customProblemDescription").value.trim();
    const concept = $("customProblemConcept").value.trim();
    const difficulty = $("customProblemDifficulty").value;

    if (!title || !description) {
        message.textContent = "Enter a problem title and description.";
        return;
    }

    button.disabled = true;
    message.textContent = "Saving your problem...";

    try {
        const result = await apiRequest("/problems", {
            method: "POST",
            body: JSON.stringify({
                problem_title: title,
                problem_description: description,
                concept: concept || null,
                difficulty
            })
        });

        if (result.problem_id == null) {
            throw new Error("The server did not return a problem ID.");
        }

        const savedProblem = {
            problem_id: result.problem_id,
            problem_title: result.problem_title ?? title,
            problem_description: result.problem_description ?? description,
            concept: result.concept ?? concept,
            difficulty: result.difficulty ?? difficulty
        };

        problems.unshift(savedProblem);
        addProblemToDropdown(savedProblem);
        $("customProblemForm").reset();

        showMessage(
            "predictionResult",
            "Your problem is saved. You can now submit an attempt."
        );

        message.textContent =
            `Problem saved successfully! ID: ${savedProblem.problem_id}`;
    } catch (error) {
        message.textContent = `Could not save problem: ${error.message}`;
    } finally {
        button.disabled = false;
    }
}

/* -------------------- Submit attempt and prediction -------------------- */

async function submitAttempt() {
    if (!selectedProblem || problemId(selectedProblem) == null) {
        showMessage("submissionResult", "Select or create a problem first.");
        return;
    }

    if (!selectedStudent || studentId(selectedStudent) == null) {
        showMessage("submissionResult", "A registered student is required.");
        return;
    }

    if (!editor) {
        showMessage("submissionResult", "The code editor is not ready yet.");
        return;
    }

    const button = $("submitButton");
    button.disabled = true;

    try {
        const elapsed = Math.max(
            1,
            Math.floor((Date.now() - startedAt) / 1000)
        );

        const nextAttempt = attemptCount + 1;
        const submittedCode = editor.getValue();

        const result = await apiRequest("/submissions", {
            method: "POST",
            body: JSON.stringify({
                student_id: Number(studentId(selectedStudent)),
                problem_id: Number(problemId(selectedProblem)),
                code_text: submittedCode,
                attempt_number: nextAttempt,
                error_count: errorCount,
                execution_count: executionCount,
                time_spent_seconds: elapsed
            })
        });

        const submissionId =
            result.submission_id ??
            result.id ??
            result.submission?.submission_id;

        if (submissionId == null) {
            throw new Error("No submission ID was returned by the server.");
        }

        latestSubmissionId = Number(submissionId);
        latestSubmittedCode = submittedCode;

        attemptCount = nextAttempt;
        updateMetrics();

        showMessage(
            "submissionResult",
            `Submission saved! ID: ${submissionId}. Time recorded: ${elapsed} seconds.`
        );

        showMessage("predictionResult", "Requesting an ML prediction...");
        await requestPrediction(submissionId);

        startedAt = Date.now();
    } catch (error) {
        showMessage("submissionResult", `Submission failed: ${error.message}`);
    } finally {
        button.disabled = false;
    }
}

async function requestPrediction(submissionId) {
    try {
        const result = await apiRequest(`/predictions/${submissionId}`);

        const prediction =
            result.prediction ??
            result.struggle_level ??
            "Unavailable";

        
const percentage = result.no_struggle_percentage ?? "Not available";
const reasons = result.reasons || [];
const model = result.model_type || "Unknown method";

showMessage(
    "predictionResult",
    `Behaviour-based struggle indicator: ${result.struggle_level}. ` +
    `No-struggle indicator: ${percentage}%. ` +
    `Signals: ${reasons.length ? reasons.join(", ") : "No specific signals recorded"}. ` +
    `Method: ${model}. ` +
    `${result.message || ""}`
);

    } catch (error) {
        showMessage(
            "predictionResult",
            `Submission was saved, but prediction failed: ${error.message}`
        );
    }
}

/* -------------------- Navigation and initialization -------------------- */

function setupNavigation() {
    const sidebar = $("sidebar");
    const overlay = $("sidebarOverlay");
    const menu = $("menuButton");

    if (!sidebar || !overlay || !menu) return;

    const close = () => {
        sidebar.classList.remove("open");
        overlay.classList.remove("show");
    };

    menu.addEventListener("click", () => {
        sidebar.classList.toggle("open");
        overlay.classList.toggle("show");
    });

    overlay.addEventListener("click", close);
}



async function initCodingWorkspace() {
    $("customProblemForm").addEventListener("submit", createCustomProblem);
    $("runCodeButton").addEventListener("click", runCode);
    $("recordErrorButton").addEventListener("click", recordManualError);
    $("submitButton").addEventListener("click", submitAttempt);

    $("refreshExecutionHistoryButton")
        .addEventListener("click", loadExecutionHistory);

    setupNavigation();
    setupEditor();
    
    const savedName = localStorage.getItem("studentName");
const avatar = document.getElementById("userInitials");

if (savedName && avatar) {
    avatar.textContent = getUserInitials(savedName);
}
    await checkBackend();
    await loadStudentProfile();
    await loadStudents();
    await loadProblems();
    await loadExecutionHistory();

    updateMetrics();
}

document.addEventListener("DOMContentLoaded", initCodingWorkspace);

