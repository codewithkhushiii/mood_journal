/* ═══════════════════════════════════════════════════════════════
   MOODBOARD — Frontend Logic
   ═══════════════════════════════════════════════════════════════ */

const API_BASE = '';

// ─── State ────────────────────────────────────────────────────
let selectedMood = null;
let selectedEmoji = null;
let isLoading = false;
let threadId = localStorage.getItem('moodboard_thread') || 'thread_' + Date.now();
localStorage.setItem('moodboard_thread', threadId);

// ─── Section Navigation ──────────────────────────────────────
function switchSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    // Show selected
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.add('active');
        // Re-trigger animation
        section.style.animation = 'none';
        section.offsetHeight; // force reflow
        section.style.animation = null;
    }

    const btn = document.querySelector(`.nav-btn[data-section="${sectionId}"]`);
    if (btn) btn.classList.add('active');

    // Load data for specific sections
    if (sectionId === 'dashboard' || sectionId === 'stats') {
        loadStats();
    }
    if (sectionId === 'stats') {
        loadAnalytics();
    }
}

// ─── Mood Selection ──────────────────────────────────────────
function selectMood(btn) {
    // Remove previous selection
    document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));

    // Select new
    btn.classList.add('selected');
    selectedMood = btn.dataset.mood;
    selectedEmoji = btn.dataset.emoji;

    // Show next sections with animation
    const intensitySection = document.getElementById('intensitySection');
    const noteSection = document.getElementById('noteSection');
    const submitSection = document.getElementById('submitSection');

    intensitySection.style.display = 'block';
    setTimeout(() => noteSection.style.display = 'block', 150);
    setTimeout(() => submitSection.style.display = 'block', 300);

    // Haptic feedback simulation (visual)
    btn.style.transform = 'translateY(-4px) scale(1.1)';
    setTimeout(() => {
        btn.style.transform = 'translateY(-4px) scale(1.05)';
    }, 150);
}

// ─── Intensity Slider ────────────────────────────────────────
function updateIntensity(value) {
    document.getElementById('intensityDisplay').textContent = value;
    document.getElementById('intensityFill').style.width = (value * 10) + '%';

    // Color shift based on intensity
    const fill = document.getElementById('intensityFill');
    if (value <= 3) {
        fill.style.background = 'linear-gradient(135deg, #55efc4, #00cec9)';
    } else if (value <= 6) {
        fill.style.background = 'linear-gradient(135deg, #6c5ce7, #a29bfe)';
    } else if (value <= 8) {
        fill.style.background = 'linear-gradient(135deg, #fdcb6e, #e17055)';
    } else {
        fill.style.background = 'linear-gradient(135deg, #fd79a8, #e84393)';
    }
}

// ─── Character Count ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const noteInput = document.getElementById('moodNote');
    if (noteInput) {
        noteInput.addEventListener('input', () => {
            document.getElementById('charCount').textContent = noteInput.value.length;
        });
    }
    loadStats();
});

// ─── Submit Mood ─────────────────────────────────────────────
async function submitMood() {
    if (!selectedMood) {
        showToast('Pick a mood first! 🤨', 'error');
        return;
    }

    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;
    submitBtn.querySelector('.submit-text').textContent = 'Saving...';

    const note = document.getElementById('moodNote').value;
    const intensity = parseInt(document.getElementById('intensitySlider').value);

    try {
        const res = await fetch(`${API_BASE}/api/mood`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mood: selectedMood,
                note: note,
                intensity: intensity
            })
        });

        if (!res.ok) throw new Error('Failed to save');

        const data = await res.json();

        // Show success overlay
        const overlay = document.getElementById('successOverlay');
        const successEmoji = document.getElementById('successEmoji');
        const successMsg = document.getElementById('successMsg');
        successEmoji.textContent = selectedEmoji;
        successMsg.textContent = `Feeling ${selectedMood} at intensity ${intensity}/10`;
        overlay.classList.add('show');

        // Reset form
        setTimeout(() => {
            overlay.classList.remove('show');
            resetMoodForm();
            switchSection('dashboard');
        }, 2000);

        showToast(`${selectedEmoji} Vibe logged!`, 'success');

    } catch (err) {
        showToast('Failed to save mood. Try again.', 'error');
        console.error(err);
    } finally {
        submitBtn.disabled = false;
        submitBtn.querySelector('.submit-text').textContent = 'Lock It In';
    }
}

function resetMoodForm() {
    document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
    selectedMood = null;
    selectedEmoji = null;
    document.getElementById('intensitySlider').value = 5;
    updateIntensity(5);
    document.getElementById('moodNote').value = '';
    document.getElementById('charCount').textContent = '0';
    document.getElementById('intensitySection').style.display = 'none';
    document.getElementById('noteSection').style.display = 'none';
    document.getElementById('submitSection').style.display = 'none';
}

// ─── Load Stats ──────────────────────────────────────────────
async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/api/stats`);
        const data = await res.json();

        if (data.message) {
            // No data
            document.getElementById('statTotal').textContent = '0';
            document.getElementById('statStreak').textContent = '0';
            document.getElementById('statTopMood').textContent = '—';
            document.getElementById('statIntensity').textContent = '—';
            document.getElementById('trendBanner').querySelector('.trend-text').textContent = '🌱 Start logging moods to see your vibe report!';
            return;
        }

        document.getElementById('statTotal').textContent = data.total_entries;
        document.getElementById('statStreak').textContent = data.streak_days;
        document.getElementById('statTopMood').textContent = data.most_frequent_mood;
        document.getElementById('statIntensity').textContent = data.avg_intensity + '/10';

        const banner = document.getElementById('trendBanner');
        const trendText = banner.querySelector('.trend-text');
        trendText.textContent = data.recent_trend;

        banner.classList.remove('positive', 'mixed', 'rough');
        if (data.recent_trend.includes('📈')) banner.classList.add('positive');
        else if (data.recent_trend.includes('📊')) banner.classList.add('mixed');
        else banner.classList.add('rough');

    } catch (err) {
        console.error('Failed to load stats:', err);
    }
}

// ─── Load Analytics ──────────────────────────────────────────
async function loadAnalytics() {
    try {
        const res = await fetch(`${API_BASE}/api/stats`);
        const data = await res.json();

        if (data.message) {
            document.getElementById('moodChart').innerHTML = '<p class="loading-text">No data to visualize yet.</p>';
            document.getElementById('statsList').innerHTML = '<p class="loading-text">Start tracking to unlock analytics.</p>';
            return;
        }

        // Build chart
        const chartContainer = document.getElementById('moodChart');
        const distribution = data.mood_distribution;
        const maxCount = Math.max(...Object.values(distribution));

        const moodColors = {
            happy: '#fdcb6e', sad: '#74b9ff', angry: '#ff7675',
            anxious: '#fd79a8', excited: '#e17055', calm: '#55efc4',
            tired: '#636e72', loved: '#e84393', confused: '#a29bfe',
            productive: '#00cec9', creative: '#6c5ce7', grateful: '#ffeaa7'
        };

        let chartHTML = '';
        for (const [mood, count] of Object.entries(distribution)) {
            const pct = Math.round((count / maxCount) * 100);
            const color = moodColors[mood] || '#6c5ce7';
            chartHTML += `
                <div class="chart-bar-item">
                    <span class="chart-bar-label">${mood}</span>
                    <div class="chart-bar-wrapper">
                        <div class="chart-bar-fill" data-count="${count}"
                             style="width: 0%; background: linear-gradient(90deg, ${color}88, ${color});">
                        </div>
                    </div>
                </div>
            `;
        }
        chartContainer.innerHTML = chartHTML;

        // Animate bars
        setTimeout(() => {
            const bars = chartContainer.querySelectorAll('.chart-bar-fill');
            bars.forEach((bar, i) => {
                const count = parseInt(bar.dataset.count);
                const pct = Math.round((count / maxCount) * 100);
                setTimeout(() => {
                    bar.style.width = Math.max(pct, 8) + '%';
                }, i * 100);
            });
        }, 100);

        // Build stats list
        const statsList = document.getElementById('statsList');
        statsList.innerHTML = `
            <div class="stat-row">
                <span class="stat-row-label">Total Entries</span>
                <span class="stat-row-value">${data.total_entries}</span>
            </div>
            <div class="stat-row">
                <span class="stat-row-label">Top Mood</span>
                <span class="stat-row-value">${data.most_frequent_mood} (${data.most_frequent_count}x)</span>
            </div>
            <div class="stat-row">
                <span class="stat-row-label">Day Streak</span>
                <span class="stat-row-value">🔥 ${data.streak_days}</span>
            </div>
            <div class="stat-row">
                <span class="stat-row-label">Avg Intensity</span>
                <span class="stat-row-value">⚡ ${data.avg_intensity}/10</span>
            </div>
            <div class="stat-row">
                <span class="stat-row-label">Unique Moods</span>
                <span class="stat-row-value">${Object.keys(data.mood_distribution).length}</span>
            </div>
            <div class="stat-row">
                <span class="stat-row-label">Trend</span>
                <span class="stat-row-value">${data.recent_trend.substring(0, 2)}</span>
            </div>
        `;

    } catch (err) {
        console.error('Failed to load analytics:', err);
    }
}

// ─── Chat Functions ──────────────────────────────────────────
function handleChatKey(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function sendSuggestion(text) {
    document.getElementById('chatInput').value = text;
    sendMessage();
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message || isLoading) return;

    isLoading = true;
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    // Add user message
    addChatMessage(message, 'user');
    input.value = '';
    input.style.height = 'auto';

    // Hide suggestions after first message
    document.getElementById('chatSuggestions').style.display = 'none';

    // Show typing indicator
    const typingId = showTypingIndicator();

    try {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                thread_id: threadId,
                user_id: 'web_user',
                include_mood_context: true
            })
        });

        if (!res.ok) throw new Error('Chat request failed');

        const data = await res.json();

        // Remove typing indicator
        removeTypingIndicator(typingId);

        // Add bot message
        addChatMessage(data.reply, 'bot');

    } catch (err) {
        removeTypingIndicator(typingId);
        addChatMessage('Oof, something broke on my end. Try again? 😅', 'bot');
        console.error(err);
    } finally {
        isLoading = false;
        sendBtn.disabled = false;
        input.focus();
    }
}

function addChatMessage(text, type) {
    const container = document.getElementById('chatMessages');
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const avatarContent = type === 'bot' ? '◉' : '◎';

    // Process markdown-like formatting
    let formattedText = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code style="background:rgba(108,92,231,0.15);padding:2px 6px;border-radius:4px;font-family:JetBrains Mono,monospace;font-size:12px;">$1</code>')
        .replace(/\n/g, '<br>');

    const msgHTML = `
        <div class="message ${type}-message">
            <div class="message-avatar">${avatarContent}</div>
            <div class="message-content">
                <div class="message-bubble">${formattedText}</div>
                <div class="message-time">${time}</div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', msgHTML);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById('chatMessages');
    const id = 'typing_' + Date.now();

    const html = `
        <div class="message bot-message" id="${id}">
            <div class="message-avatar">◉</div>
            <div class="message-content">
                <div class="message-bubble">
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', html);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function clearChat() {
    if (!confirm('Clear chat history? Memory resets too.')) return;

    const container = document.getElementById('chatMessages');
    container.innerHTML = `
        <div class="message bot-message appear">
            <div class="message-avatar">◉</div>
            <div class="message-content">
                <div class="message-bubble">
                    Fresh start! What's on your mind? 🧠
                </div>
                <div class="message-time">Just now</div>
            </div>
        </div>
    `;

    // New thread for fresh memory
    threadId = 'thread_' + Date.now();
    localStorage.setItem('moodboard_thread', threadId);

    document.getElementById('chatSuggestions').style.display = 'flex';
    showToast('Chat cleared ✨', 'info');
}

// ─── Clear All Data ──────────────────────────────────────────
async function clearAllData() {
    if (!confirm('⚠️ Delete ALL mood data? This is irreversible!')) return;
    if (!confirm('Seriously? Last chance to back out...')) return;

    try {
        const res = await fetch(`${API_BASE}/api/moods`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete');

        showToast('💣 All data nuked. Fresh start!', 'info');

        setTimeout(() => {
            window.location.reload();
        }, 1500);

    } catch (err) {
        showToast('Failed to clear data.', 'error');
        console.error(err);
    }
}

// ─── Toast Notifications ─────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const icons = { success: '✓', error: '✕', info: 'ℹ' };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span> ${message}`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}