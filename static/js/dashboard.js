// ---------------------------------------------------------------------------
// Dashboard interactivity: tab switching + API calls + rendering
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    setupTabs();
    loadToday();
    loadNextClass();
    loadWeek();
    loadExams();
    setupChat();
});

function setupTabs() {
    const buttons = document.querySelectorAll(".tab-btn");
    buttons.forEach((btn) => {
        btn.addEventListener("click", () => {
            buttons.forEach((b) => b.classList.remove("active"));
            document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
        });
    });
}

function statusClass(status) {
    if (status === "Cancelled") return "status-cancelled";
    if (status === "Extra") return "status-extra";
    return "status-scheduled";
}

function renderClassCard(c) {
    const cancelled = c.status === "Cancelled" ? "cancelled" : "";
    return `
        <div class="class-card ${cancelled}">
            <div class="class-time">${c.start_time}<br>${c.end_time}</div>
            <div class="class-info">
                <div class="subject">${c.subject}</div>
                <div class="meta">Room ${c.room} &middot; ${c.faculty}</div>
            </div>
            <div class="class-status ${statusClass(c.status)}">${c.status}</div>
        </div>
    `;
}

async function loadToday() {
    const res = await fetch("/api/timetable/today");
    const data = await res.json();
    document.getElementById("today-date").textContent = data.date;
    const container = document.getElementById("today-classes");
    if (!data.classes.length) {
        container.innerHTML = `<div class="empty-state">No classes scheduled today. Enjoy the break!</div>`;
        return;
    }
    container.innerHTML = data.classes.map(renderClassCard).join("");
}

async function loadNextClass() {
    const res = await fetch("/api/timetable/next-class");
    const data = await res.json();
    const banner = document.getElementById("next-class-banner");
    if (data.found) {
        const c = data.class;
        const when = data.when === "today" ? "today" : `on ${data.when}`;
        banner.innerHTML = `⏰ Next up ${when}: <strong>${c.subject}</strong> at ${c.start_time} in Room ${c.room} with ${c.faculty}`;
        banner.classList.add("show");
    }
}

async function loadWeek() {
    const res = await fetch("/api/timetable/week");
    const data = await res.json();
    const grid = document.getElementById("week-grid");
    const days = Object.keys(data);
    grid.innerHTML = days.map((day) => {
        const classes = data[day];
        const body = classes.length
            ? classes.map(renderClassCard).join("")
            : `<div class="empty-state">No classes</div>`;
        return `<div class="day-column"><h3>${day}</h3>${body}</div>`;
    }).join("");
}

async function loadExams() {
    const res = await fetch("/api/exams");
    const data = await res.json();
    const container = document.getElementById("exam-list");
    if (!data.length) {
        container.innerHTML = `<div class="empty-state">No exam schedule available yet.</div>`;
        return;
    }
    container.innerHTML = data.map((e) => `
        <div class="class-card">
            <div class="class-time">${e.date}</div>
            <div class="class-info">
                <div class="subject">${e.title}</div>
                <div class="meta">${e.details || ""}</div>
            </div>
            <div class="class-status status-extra">Exam</div>
        </div>
    `).join("");
}

function setupChat() {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const window_ = document.getElementById("chat-window");

    addChatMessage(window_, "bot", "Hi! Ask me about today's classes, your weekly timetable, free periods, cancellations, or exams.");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const query = input.value.trim();
        if (!query) return;
        addChatMessage(window_, "user", query);
        input.value = "";

        const res = await fetch("/api/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query }),
        });
        const data = await res.json();
        addChatMessage(window_, "bot", data.answer);
    });
}

function addChatMessage(container, sender, text) {
    const div = document.createElement("div");
    div.className = `chat-msg ${sender}`;
    div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}
