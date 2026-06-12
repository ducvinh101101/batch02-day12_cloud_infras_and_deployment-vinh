/**
 * Medical Research AI Agent — Frontend Application
 * Handles chat, file upload, chart rendering, and session management.
 */

// ── State ──────────────────────────────────────────────────────
const state = {
    sessionId: null,
    apiKey: localStorage.getItem("medicalAgentApiKey") || "dev-key-change-me",
    isProcessing: false,
    currentDataset: null,
    chartHistory: [],
};

// ── DOM Elements ───────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const els = {
    chatContainer: $("#chatContainer"),
    messages: $("#messages"),
    welcomeScreen: $("#welcomeScreen"),
    chatInput: $("#chatInput"),
    sendBtn: $("#sendBtn"),
    fileInput: $("#fileInput"),
    uploadZone: $("#uploadZone"),
    uploadContent: $("#uploadContent"),
    uploadProgress: $("#uploadProgress"),
    progressFill: $("#progressFill"),
    uploadStatus: $("#uploadStatus"),
    datasetInfo: $("#datasetInfo"),
    chartHistory: $("#chartHistory"),
    resetBtn: $("#resetBtn"),
    statusDot: $("#statusDot"),
    statusText: $("#statusText"),
    chartModal: $("#chartModal"),
    modalImage: $("#modalImage"),
    modalClose: $("#modalClose"),
    sidebarToggleBtn: $("#sidebarToggleBtn"),
    sidebar: $("#sidebar"),
    apiKeyInput: $("#apiKeyInput"),
    saveApiKeyBtn: $("#saveApiKeyBtn"),
};

function apiHeaders(extra = {}) {
    return {
        "X-API-Key": state.apiKey,
        ...(state.sessionId ? { "X-Session-ID": state.sessionId } : {}),
        ...extra,
    };
}

// ── Initialization ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    els.apiKeyInput.value = state.apiKey;
    initEventListeners();
    checkHealth();
});

function initEventListeners() {
    // Chat input
    els.chatInput.addEventListener("keydown", handleChatKeydown);
    els.chatInput.addEventListener("input", autoResizeTextarea);
    els.sendBtn.addEventListener("click", sendMessage);

    // File upload
    els.uploadZone.addEventListener("click", () => els.fileInput.click());
    els.fileInput.addEventListener("change", handleFileSelect);
    els.uploadZone.addEventListener("dragover", handleDragOver);
    els.uploadZone.addEventListener("dragleave", handleDragLeave);
    els.uploadZone.addEventListener("drop", handleDrop);

    // Modal
    els.modalClose.addEventListener("click", closeModal);
    els.chartModal.addEventListener("click", (e) => {
        if (e.target === els.chartModal) closeModal();
    });
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeModal();
    });

    // Sidebar
    els.sidebarToggleBtn.addEventListener("click", toggleSidebar);
    els.resetBtn.addEventListener("click", resetSession);
    els.saveApiKeyBtn.addEventListener("click", () => {
        state.apiKey = els.apiKeyInput.value.trim();
        localStorage.setItem("medicalAgentApiKey", state.apiKey);
        checkHealth();
    });
}

// ── Health Check ───────────────────────────────────────────────
async function checkHealth() {
    try {
        const res = await fetch("/api/health", { headers: apiHeaders() });
        const data = await res.json();
        if (data.agent_ready) {
            els.statusDot.classList.add("connected");
            els.statusText.textContent = `Online • ${data.model}`;
            state.sessionId = data.session_id;
        } else {
            els.statusText.textContent = "API Key missing";
        }
    } catch (e) {
        els.statusText.textContent = "Disconnected";
    }
}

// ── Chat ───────────────────────────────────────────────────────
function handleChatKeydown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResizeTextarea() {
    const el = els.chatInput;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 150) + "px";
}

async function sendMessage() {
    const message = els.chatInput.value.trim();
    if (!message || state.isProcessing) return;

    state.isProcessing = true;
    els.sendBtn.disabled = true;

    // Hide welcome screen
    els.welcomeScreen.classList.add("hidden");

    // Add user message
    addMessage("user", message);

    // Clear input
    els.chatInput.value = "";
    els.chatInput.style.height = "auto";

    // Show typing indicator
    const typingEl = showTypingIndicator();

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: apiHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({ message }),
        });

        const data = await res.json();
        removeTypingIndicator(typingEl);

        if (data.success && data.response) {
            const resp = data.response;
            addAssistantMessage(resp);

            // Update chart history
            if (resp.chart_id) {
                loadChartHistory();
            }
        } else {
            addMessage("assistant", `❌ Lỗi: ${data.detail || "Không thể xử lý yêu cầu."}`);
        }
    } catch (err) {
        removeTypingIndicator(typingEl);
        addMessage("assistant", `❌ Lỗi kết nối: ${err.message}`);
    }

    state.isProcessing = false;
    els.sendBtn.disabled = false;
    els.chatInput.focus();
}

// ── File Upload ────────────────────────────────────────────────
function handleDragOver(e) {
    e.preventDefault();
    els.uploadZone.classList.add("drag-over");
}

function handleDragLeave(e) {
    e.preventDefault();
    els.uploadZone.classList.remove("drag-over");
}

function handleDrop(e) {
    e.preventDefault();
    els.uploadZone.classList.remove("drag-over");
    const files = e.dataTransfer.files;
    if (files.length > 0) uploadFile(files[0]);
}

function handleFileSelect(e) {
    if (e.target.files.length > 0) uploadFile(e.target.files[0]);
}

async function uploadFile(file) {
    if (!file.name.endsWith(".csv")) {
        alert("Chỉ hỗ trợ file CSV.");
        return;
    }

    state.isProcessing = true;
    els.sendBtn.disabled = true;

    // Show progress
    els.uploadContent.hidden = true;
    els.uploadProgress.hidden = false;
    els.progressFill.style.width = "30%";
    els.uploadStatus.textContent = `Đang upload ${file.name}...`;

    // Hide welcome
    els.welcomeScreen.classList.add("hidden");

    const formData = new FormData();
    formData.append("file", file);

    try {
        els.progressFill.style.width = "60%";
        els.uploadStatus.textContent = "Đang phân tích dữ liệu...";

        const res = await fetch("/api/upload", {
            method: "POST",
            headers: apiHeaders(),
            body: formData,
        });

        els.progressFill.style.width = "100%";

        const data = await res.json();

        if (data.success) {
            // Update dataset info in sidebar
            if (data.response.schema) {
                updateDatasetInfo(data.response.schema, file.name);
            }

            // Show response
            addAssistantMessage(data.response);

            els.uploadStatus.textContent = "✅ Upload thành công!";
        } else {
            addMessage("assistant", `❌ Lỗi upload: ${data.detail || "Unknown error"}`);
            els.uploadStatus.textContent = "❌ Upload thất bại";
        }
    } catch (err) {
        addMessage("assistant", `❌ Lỗi upload: ${err.message}`);
        els.uploadStatus.textContent = "❌ Upload thất bại";
    }

    // Reset upload zone after delay
    setTimeout(() => {
        els.uploadContent.hidden = false;
        els.uploadProgress.hidden = true;
        els.progressFill.style.width = "0%";
    }, 2000);

    state.isProcessing = false;
    els.sendBtn.disabled = false;
    els.fileInput.value = "";
}

// ── Message Rendering ──────────────────────────────────────────
function addMessage(role, text) {
    const msgEl = document.createElement("div");
    msgEl.className = `message ${role}`;

    const avatar = role === "user" ? "👤" : "🔬";

    msgEl.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-bubble">
            <div class="message-text">${formatMarkdown(text)}</div>
        </div>
    `;

    els.messages.appendChild(msgEl);
    scrollToBottom();
}

function addAssistantMessage(resp) {
    const msgEl = document.createElement("div");
    msgEl.className = "message assistant";

    let html = `
        <div class="message-avatar">🔬</div>
        <div class="message-bubble">
            <div class="message-text">${formatMarkdown(resp.text || "")}</div>
    `;

    // Chart image
    if (resp.chart_path) {
        const chartUrl = `/api/chart/${resp.chart_path}`;
        html += `
            <div class="chart-display" onclick="openModal('${chartUrl}')">
                <img src="${chartUrl}" alt="Medical Chart" loading="lazy">
                <span class="zoom-hint">🔍 Click để phóng to</span>
            </div>
        `;
    }

    // Code block
    if (resp.code) {
        const codeId = "code-" + Date.now();
        html += `
            <div class="code-block-wrapper">
                <button class="code-toggle-btn" onclick="toggleCode('${codeId}')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
                    Xem Code Python
                </button>
                <div class="code-block hidden" id="${codeId}">
                    <div class="code-header">
                        <span>Python</span>
                        <button class="code-copy-btn" onclick="copyCode('${codeId}')">📋 Copy</button>
                    </div>
                    <pre class="code-content">${escapeHtml(resp.code)}</pre>
                </div>
            </div>
        `;
    }

    // Action buttons
    html += `
            <div class="message-actions">
    `;
    if (resp.chart_path) {
        const chartUrl = `/api/chart/${resp.chart_path}`;
        html += `<button class="msg-action-btn" onclick="downloadChart('${chartUrl}')">📥 Tải PNG</button>`;
    }
    if (resp.code) {
        html += `<button class="msg-action-btn" onclick="downloadCode(\`${btoa(unescape(encodeURIComponent(resp.code)))}\`)">💾 Tải Code</button>`;
    }
    html += `
            </div>
        </div>
    `;

    msgEl.innerHTML = html;
    els.messages.appendChild(msgEl);
    scrollToBottom();
}

// ── Typing Indicator ───────────────────────────────────────────
function showTypingIndicator() {
    const el = document.createElement("div");
    el.className = "typing-indicator";
    el.id = "typingIndicator";
    el.innerHTML = `
        <div class="message-avatar" style="background: linear-gradient(135deg, #00bcd4, #00838f);">🔬</div>
        <div class="typing-dots">
            <span></span><span></span><span></span>
        </div>
        <span class="typing-text">Đang phân tích...</span>
    `;
    els.messages.appendChild(el);
    scrollToBottom();
    return el;
}

function removeTypingIndicator(el) {
    if (el && el.parentNode) {
        el.parentNode.removeChild(el);
    }
}

// ── Sidebar Updates ────────────────────────────────────────────
function updateDatasetInfo(schema, filename) {
    state.currentDataset = schema;

    const cols = schema.columns || [];
    const roleIcons = {
        identifier: "🔑", demographic: "👤", biomarker: "🧬",
        outcome: "🎯", time_variable: "⏰", grouping: "📊",
        confounding: "⚙️", unknown: "❓",
    };

    let colsHtml = cols.slice(0, 8).map(c => {
        const icon = roleIcons[c.medical_role] || "❓";
        return `<span>${icon} ${c.name}</span>`;
    }).join("");
    if (cols.length > 8) {
        colsHtml += `<span style="color:var(--text-muted)">+${cols.length - 8} more</span>`;
    }

    els.datasetInfo.innerHTML = `
        <div class="dataset-card">
            <div class="file-name">📄 ${filename || schema.filename}</div>
            <div class="file-meta">
                <span>📊 ${schema.row_count} rows</span>
                <span>📋 ${schema.col_count} cols</span>
            </div>
            <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:4px;font-size:0.72rem;color:var(--text-secondary)">
                ${colsHtml}
            </div>
        </div>
    `;
}

async function loadChartHistory() {
    try {
        const res = await fetch("/api/history", { headers: apiHeaders() });
        const data = await res.json();

        if (data.charts && data.charts.length > 0) {
            state.chartHistory = data.charts;
            els.chartHistory.innerHTML = data.charts.map(c => {
                const chartType = c.chart_type.replace(/_/g, " ");
                const time = new Date(c.created_at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
                return `
                    <div class="chart-history-item" onclick="viewHistoryChart('${c.chart_id}')">
                        <div class="chart-title">#${c.iteration} ${c.title || chartType}</div>
                        <div class="chart-meta">
                            <span class="chart-type-badge">${chartType}</span>
                            <span>${time}</span>
                        </div>
                    </div>
                `;
            }).join("");
        }
    } catch (e) {
        console.error("Failed to load chart history:", e);
    }
}

// ── Modal ──────────────────────────────────────────────────────
function openModal(imageUrl) {
    els.modalImage.src = imageUrl;
    els.chartModal.hidden = false;
}

function closeModal() {
    els.chartModal.hidden = true;
    els.modalImage.src = "";
}

// ── Code Toggle & Copy ─────────────────────────────────────────
function toggleCode(codeId) {
    const el = document.getElementById(codeId);
    if (el) el.classList.toggle("hidden");
}

function copyCode(codeId) {
    const el = document.getElementById(codeId);
    if (!el) return;
    const code = el.querySelector(".code-content")?.textContent || "";
    navigator.clipboard.writeText(code).then(() => {
        const btn = el.querySelector(".code-copy-btn");
        if (btn) {
            btn.textContent = "✅ Copied!";
            setTimeout(() => { btn.textContent = "📋 Copy"; }, 2000);
        }
    });
}

// ── Downloads ──────────────────────────────────────────────────
function downloadChart(url) {
    const a = document.createElement("a");
    a.href = url;
    a.download = "medical_chart.png";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function downloadCode(base64Code) {
    try {
        const code = decodeURIComponent(escape(atob(base64Code)));
        const blob = new Blob([code], { type: "text/python" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "medical_chart.py";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (e) {
        console.error("Download failed:", e);
    }
}

// ── Session ────────────────────────────────────────────────────
async function resetSession() {
    if (!confirm("Bạn có chắc muốn reset phiên làm việc? Tất cả dữ liệu sẽ bị xóa.")) return;

    try {
        const res = await fetch("/api/session", { method: "DELETE", headers: apiHeaders() });
        const data = await res.json();
        state.sessionId = data.new_session_id;
        els.messages.innerHTML = "";
        els.welcomeScreen.classList.remove("hidden");
        els.datasetInfo.innerHTML = '<p class="empty-state">Chưa có dataset nào được tải lên</p>';
        els.chartHistory.innerHTML = '<p class="empty-state">Chưa có biểu đồ nào</p>';
        state.currentDataset = null;
        state.chartHistory = [];
        checkHealth();
    } catch (e) {
        alert("Lỗi khi reset session: " + e.message);
    }
}

function toggleSidebar() {
    els.sidebar.classList.toggle("collapsed");
}

// ── View History Chart ─────────────────────────────────────────
async function viewHistoryChart(chartId) {
    try {
        const res = await fetch(`/api/code/${chartId}`, { headers: apiHeaders() });
        const data = await res.json();
        if (data.chart_config) {
            const imgPath = data.chart_config.image_path;
            if (imgPath) {
                const filename = imgPath.split("/").pop().split("\\").pop();
                openModal(`/api/chart/${filename}`);
            }
        }
    } catch (e) {
        console.error("Failed to view chart:", e);
    }
}

// ── Helpers ────────────────────────────────────────────────────
function scrollToBottom() {
    requestAnimationFrame(() => {
        els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
    });
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatMarkdown(text) {
    if (!text) return "";

    // Escape HTML first
    let html = escapeHtml(text);

    // Bold: **text**
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

    // Italic: *text*
    html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");

    // Inline code: `text`
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Headers: ### text
    html = html.replace(/^### (.+)$/gm, "<h4>$1</h4>");
    html = html.replace(/^## (.+)$/gm, "<h3>$1</h3>");

    // Unordered lists: - item or • item
    html = html.replace(/^[\-•] (.+)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`);

    // Ordered lists: 1. item
    html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");

    // Horizontal rule: ---
    html = html.replace(/^---$/gm, "<hr>");

    // Line breaks
    html = html.replace(/\n\n/g, "</p><p>");
    html = html.replace(/\n/g, "<br>");

    // Wrap in paragraph
    html = "<p>" + html + "</p>";

    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, "");
    html = html.replace(/<p><h/g, "<h");
    html = html.replace(/<\/h\d><\/p>/g, (m) => m.replace("</p>", ""));
    html = html.replace(/<p><ul>/g, "<ul>");
    html = html.replace(/<\/ul><\/p>/g, "</ul>");
    html = html.replace(/<p><hr><\/p>/g, "<hr>");

    return html;
}
