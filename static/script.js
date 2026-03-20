/* ═══════════════════════════════════════════════════════════
   MOODBOARD v3.0 — Frontend Engine
   MongoDB-backed, AI-powered
   ═══════════════════════════════════════════════════════════ */

const API = '';

// ─── State ────────────────────────────────────────────────
let selectedMood = null;
let selectedEmoji = null;
let selectedActivities = [];
let chatLoading = false;
let threadId = localStorage.getItem('mb3_thread') || 'thread_' + Date.now();
localStorage.setItem('mb3_thread', threadId);

// ─── Cursor Glow ─────────────────────────────────────────
document.addEventListener('mousemove', (e) => {
    const glow = document.getElementById('cursorGlow');
    if (glow) {
        glow.style.left = e.clientX + 'px';
        glow.style.top = e.clientY + 'px';
    }
});

// ─── Nav Pill Animation ──────────────────────────────────
function updateNavPill() {
    const active = document.querySelector('.nav-pill.active');
    const bg = document.getElementById('navPillBg');
    if (active && bg) {
        const nav = active.parentElement;
        const navRect = nav.getBoundingClientRect();
        const activeRect = active.getBoundingClientRect();
        bg.style.left = (activeRect.left - navRect.left) + 'px';
        bg.style.width = activeRect.width + 'px';
    }
}

// ─── Section Switching ───────────────────────────────────
function switchSection(id) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-pill').forEach(b => b.classList.remove('active'));

    const section = document.getElementById(id);
    if (section) {
        section.classList.add('active');
        section.style.animation = 'none';
        section.offsetHeight;
        section.style.animation = null;
    }

    const btn = document.querySelector(`.nav-pill[data-section="${id}"]`);
    if (btn) btn.classList.add('active');

    requestAnimationFrame(updateNavPill);

    if (id === 'dashboard') loadDashboard();
    if (id === 'insights') loadInsights();
}

// ─── Dashboard Load ──────────────────────────────────────
async function loadDashboard() {
    try {
        const res = await fetch(`${API}/api/stats`);
        const data = await res.json();

        if (!data.has_data) {
            document.getElementById('statTotal').textContent = '0';
            document.getElementById('statStreak').textContent = '0';
            document.getElementById('statSentiment').textContent = '0%';
            document.getElementById('statTopMood').textContent = '—';
            document.getElementById('statIntensity').textContent = '—';
            document.getElementById('navStreak').textContent = '0';
            return;
        }

        animateValue('statTotal', 0, data.total_entries, 800);
        animateValue('statStreak', 0, data.streak_days, 600);
        document.getElementById('statSentiment').textContent = data.sentiment_ratio + '%';
        document.getElementById('navStreak').textContent = data.streak_days;

        // Sentiment ring
        const ring = document.getElementById('ringFill');
        if (ring) {
            setTimeout(() => {
                ring.setAttribute('stroke-dasharray', `${data.sentiment_ratio}, 100`);
            }, 300);
        }

        if (data.top_mood) {
            document.getElementById('statTopMood').textContent =
                data.top_mood.emoji + ' ' + data.top_mood.mood;
        }
        document.getElementById('statIntensity').textContent = data.avg_intensity + '/10';

        // Trend card
        const trendCard = document.getElementById('trendCard');
        const trendIcon = document.getElementById('trendIcon');
        const trendTitle = document.getElementById('trendTitle');
        trendTitle.textContent = data.trend;
        trendCard.classList.remove('positive', 'mixed', 'rough');
        trendCard.classList.add(data.trend_type);
        if (data.trend_type === 'positive') trendIcon.textContent = '📈';
        else if (data.trend_type === 'mixed') trendIcon.textContent = '📊';
        else trendIcon.textContent = '📉';

    } catch (err) {
        console.error('Dashboard load failed:', err);
    }
}

function animateValue(elemId, start, end, duration) {
    const el = document.getElementById(elemId);
    if (!el) return;
    const range = end - start;
    const startTime = performance.now();
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(start + range * eased);
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

// ─── Mood Selection ──────────────────────────────────────
function selectMood(btn) {
    document.querySelectorAll('.hex-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    selectedMood = btn.dataset.mood;
    selectedEmoji = btn.dataset.emoji;

    showStep('step2', 100);
    showStep('step3', 200);
    showStep('step4', 300);
    showStep('step5', 400);
}

function showStep(id, delay) {
    setTimeout(() => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.remove('hidden');
            el.style.animation = 'sectionIn 0.4s var(--ease)';
        }
    }, delay);
}

// ─── Intensity ───────────────────────────────────────────
function updateIntensity(val) {
    const orbVal = document.getElementById('orbValue');
    const orb = document.getElementById('intensityOrb');
    if (orbVal) orbVal.textContent = val;

    const hue = 270 - (val - 1) * 15;
    if (orb) {
        orb.style.borderColor = `hsl(${hue}, 70%, 60%)`;
        orb.style.boxShadow = `0 0 ${val * 4}px hsla(${hue}, 70%, 60%, 0.3)`;
    }
}

// ─── Activities ──────────────────────────────────────────
function toggleActivity(btn) {
    const act = btn.dataset.activity;
    btn.classList.toggle('selected');
    if (selectedActivities.includes(act)) {
        selectedActivities = selectedActivities.filter(a => a !== act);
    } else {
        selectedActivities.push(act);
    }
}

// ─── Character Count ─────────────────────────────────────
function updateCharCount() {
    const note = document.getElementById('moodNote');
    const count = document.getElementById('charCount');
    if (note && count) count.textContent = note.value.length;
}

// ─── Submit Mood ─────────────────────────────────────────
async function submitMood() {
    if (!selectedMood) {
        showToast('Pick a mood first! 🤨', 'error');
        return;
    }

    const btn = document.getElementById('submitBtn');
    const loader = document.getElementById('submitLoader');
    const text = btn.querySelector('.submit-text');
    const arrow = btn.querySelector('.submit-arrow');

    btn.disabled = true;
    text.textContent = 'Saving...';
    arrow.style.display = 'none';
    loader.style.display = 'block';

    const intensity = parseInt(document.getElementById('intensitySlider').value);
    const note = document.getElementById('moodNote')?.value || '';

    try {
        const res = await fetch(`${API}/api/mood`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mood: selectedMood,
                note,
                intensity,
                activities: selectedActivities,
                tags: [],
            })
        });

        if (!res.ok) throw new Error('Save failed');

        // Success screen
        const screen = document.getElementById('successScreen');
        document.getElementById('successEmoji').textContent = selectedEmoji;
        document.getElementById('successDetail').textContent =
            `${selectedMood} at intensity ${intensity}/10` +
            (selectedActivities.length ? ` • ${selectedActivities.join(', ')}` : '');
        screen.classList.add('show');

        createBurst();
        showToast(`${selectedEmoji} Vibe logged!`, 'success');

    } catch (err) {
        showToast('Failed to save. Try again.', 'error');
    } finally {
        btn.disabled = false;
        text.textContent = 'Lock It In';
        arrow.style.display = '';
        loader.style.display = 'none';
    }
}

function closeSuccess() {
    document.getElementById('successScreen').classList.remove('show');
    resetMoodForm();
    switchSection('dashboard');
}

function resetMoodForm() {
    document.querySelectorAll('.hex-btn').forEach(b => b.classList.remove('selected'));
    document.querySelectorAll('.act-chip').forEach(b => b.classList.remove('selected'));
    selectedMood = null;
    selectedEmoji = null;
    selectedActivities = [];
    const slider = document.getElementById('intensitySlider');
    if (slider) slider.value = 5;
    updateIntensity(5);
    const note = document.getElementById('moodNote');
    if (note) note.value = '';
    const count = document.getElementById('charCount');
    if (count) count.textContent = '0';
    ['step2','step3','step4','step5'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });
}

function createBurst() {
    const container = document.getElementById('successBurst');
    if (!container) return;
    container.innerHTML = '';
    const emojis = ['✨','🎉','💫','⭐','🌟','💖','🔥','🎊'];
    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('div');
        particle.textContent = emojis[Math.floor(Math.random() * emojis.length)];
        particle.style.cssText = `
            position: absolute;
            font-size: ${Math.random() * 20 + 14}px;
            left: 50%;
            top: 50%;
            animation: burstParticle ${Math.random() * 1 + 0.8}s ease-out forwards;
            --angle: ${Math.random() * 360}deg;
            --dist: ${Math.random() * 200 + 100}px;
        `;
        container.appendChild(particle);
    }

    const style = document.createElement('style');
    style.textContent = `
        @keyframes burstParticle {
            0% { transform: translate(-50%, -50%) scale(0); opacity: 1; }
            100% {
                transform: translate(
                    calc(-50% + cos(var(--angle)) * var(--dist)),
                    calc(-50% + sin(var(--angle)) * var(--dist))
                ) scale(1);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

// ─── Chat Functions ──────────────────────────────────────
function handleChatKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResizeChat(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 100) + 'px';
}

function sendSuggestion(text) {
    document.getElementById('chatInput').value = text;
    sendMessage();
}

function requestFullAnalysis() {
    sendSuggestion('Give me a comprehensive analysis of ALL my mood data — patterns, triggers, trends, and personalized suggestions');
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message || chatLoading) return;

    chatLoading = true;
    document.getElementById('sendBtn').disabled = true;

    addMsg(message, 'user');
    input.value = '';
    input.style.height = 'auto';

    const chips = document.getElementById('chatChips');
    if (chips) chips.style.display = 'none';

    const typingId = showTyping();

    try {
        const res = await fetch(`${API}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                thread_id: threadId,
                user_id: 'default_user',
                include_analysis: true,
            })
        });

        if (!res.ok) throw new Error('Chat failed');
        const data = await res.json();
        removeTyping(typingId);
        addMsg(data.reply, 'bot');

    } catch (err) {
        removeTyping(typingId);
        addMsg('My brain glitched 😵‍💫 Try again?', 'bot');
    } finally {
        chatLoading = false;
        document.getElementById('sendBtn').disabled = false;
        input.focus();
    }
}

function addMsg(text, type) {
    const container = document.getElementById('chatMessages');
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const avatar = type === 'bot' ? '🧠' : '👤';

    let formatted = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code style="background:rgba(124,92,252,0.12);padding:2px 6px;border-radius:4px;font-family:JetBrains Mono,monospace;font-size:12px;">$1</code>')
        .replace(/\n/g, '<br>');

    container.insertAdjacentHTML('beforeend', `
        <div class="msg msg-${type}">
            <div class="msg-avatar">${avatar}</div>
            <div class="msg-wrap">
                <div class="msg-bubble">${formatted}</div>
                <div class="msg-time">${time}</div>
            </div>
        </div>
    `);
    container.scrollTop = container.scrollHeight;
}

function showTyping() {
    const container = document.getElementById('chatMessages');
    const id = 'typing_' + Date.now();
    container.insertAdjacentHTML('beforeend', `
        <div class="msg msg-bot" id="${id}">
            <div class="msg-avatar">🧠</div>
            <div class="msg-wrap">
                <div class="msg-bubble">
                    <div class="typing-dots">
                        <div class="typing-d"></div>
                        <div class="typing-d"></div>
                        <div class="typing-d"></div>
                    </div>
                </div>
            </div>
        </div>
    `);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function clearChat() {
    if (!confirm('Clear chat and reset AI memory?')) return;
    const container = document.getElementById('chatMessages');
    container.innerHTML = `
        <div class="msg msg-bot msg-appear">
            <div class="msg-avatar">🧠</div>
            <div class="msg-wrap">
                <div class="msg-bubble">Memory wiped! Fresh start. What's on your mind? 🧠✨</div>
                <div class="msg-time">Just now</div>
            </div>
        </div>
    `;
    threadId = 'thread_' + Date.now();
    localStorage.setItem('mb3_thread', threadId);
    const chips = document.getElementById('chatChips');
    if (chips) chips.style.display = 'flex';
    showToast('Chat cleared ✨', 'info');
}

// ─── Insights Load ───────────────────────────────────────
async function loadInsights() {
    await loadMoodBars();
    await loadWeeklyHeatmap();
    await loadHourlyChart();
    await loadActivityCorrelations();
    await loadTrendChart();
}

async function loadMoodBars() {
    try {
        const res = await fetch(`${API}/api/stats`);
        const data = await res.json();
        const container = document.getElementById('moodBars');
        if (!data.has_data || !data.distribution) {
            container.innerHTML = '<p class="muted-text">No data yet</p>';
            return;
        }

        const maxCount = Math.max(...data.distribution.map(d => d.count));
        const colors = {
            happy:'#fbbf24', sad:'#60a5fa', angry:'#f87171', anxious:'#f472b6',
            excited:'#fb923c', calm:'#4ade80', tired:'#94a3b8', loved:'#ec4899',
            confused:'#a78bfa', productive:'#2dd4bf', creative:'#7c5cfc',
            grateful:'#fde68a', stressed:'#f87171', hopeful:'#fbbf24',
            motivated:'#f97316', peaceful:'#6ee7b7',
        };

        container.innerHTML = data.distribution.map(d => {
            const pct = Math.round((d.count / maxCount) * 100);
            const color = colors[d.mood] || '#7c5cfc';
            return `
                <div class="bar-row">
                    <span class="bar-label">${d.emoji} ${d.mood}</span>
                    <div class="bar-track">
                        <div class="bar-fill" data-val="${d.count}"
                             style="width: 0%; background: linear-gradient(90deg, ${color}88, ${color});">
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        setTimeout(() => {
            container.querySelectorAll('.bar-fill').forEach((bar, i) => {
                const count = parseInt(bar.dataset.val);
                const pct = Math.max(Math.round((count / maxCount) * 100), 6);
                setTimeout(() => { bar.style.width = pct + '%'; }, i * 80);
            });
        }, 200);
    } catch (err) { console.error(err); }
}

async function loadWeeklyHeatmap() {
    try {
        const res = await fetch(`${API}/api/analytics/weekly`);
        const data = await res.json();
        const container = document.getElementById('weeklyHeatmap');
        if (!data.length) {
            container.innerHTML = '<p class="muted-text">No weekly data</p>';
            return;
        }

        const maxCount = Math.max(...data.map(d => d.count));
        container.innerHTML = data.map(d => {
            const posRatio = d.positive_count / Math.max(d.count, 1);
            const hue = posRatio > 0.6 ? 150 : posRatio > 0.3 ? 45 : 0;
            const sat = 60 + posRatio * 30;
            const light = 30 + (d.count / maxCount) * 30;
            return `
                <div class="heat-row">
                    <span class="heat-day">${d._id?.substring(0, 3) || '?'}</span>
                    <div class="heat-bar-wrap">
                        <div class="heat-block" style="background: hsla(${hue},${sat}%,${light}%,0.7); flex: ${d.positive_count || 1};" title="Positive: ${d.positive_count}"></div>
                        <div class="heat-block" style="background: hsla(0,50%,${25 + (d.negative_count/Math.max(maxCount,1))*25}%,0.7); flex: ${d.negative_count || 1};" title="Negative: ${d.negative_count}"></div>
                    </div>
                    <span class="heat-count">${d.count}</span>
                </div>
            `;
        }).join('');
    } catch (err) { console.error(err); }
}

async function loadHourlyChart() {
    try {
        const res = await fetch(`${API}/api/analytics/hourly`);
        const data = await res.json();
        const container = document.getElementById('hourlyChart');
        if (!data.length) {
            container.innerHTML = '<p class="muted-text">No hourly data</p>';
            return;
        }

        const hourMap = {};
        data.forEach(d => { hourMap[d._id] = d; });
        const maxCount = Math.max(...data.map(d => d.count));

        let html = '';
        for (let h = 0; h < 24; h++) {
            const d = hourMap[h];
            const count = d ? d.count : 0;
            const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
            const intensity = d ? d.avg_intensity : 0;
            const hue = 260 - intensity * 15;
            html += `<div class="hour-bar" data-hour="${h}:00"
                          style="height: ${Math.max(pct, 3)}%;
                                 background: hsla(${hue}, 60%, 55%, ${count > 0 ? 0.6 : 0.1});"></div>`;
        }
        container.innerHTML = html;
    } catch (err) { console.error(err); }
}

async function loadActivityCorrelations() {
    try {
        const res = await fetch(`${API}/api/analytics/activities`);
        const data = await res.json();
        const container = document.getElementById('activityGrid');
        if (!data.length) {
            container.innerHTML = '<p class="muted-text">Log moods with activities to unlock correlations</p>';
            return;
        }

        container.innerHTML = data.map(a => `
            <div class="act-card">
                <div class="act-card-name">${a._id}</div>
                <div class="act-card-stats">
                    <div class="act-stat">
                        <span class="act-stat-val ${a.positive_ratio > 50 ? 'act-pos' : 'act-neg'}">${Math.round(a.positive_ratio)}%</span>
                        <span class="act-stat-label">POSITIVE</span>
                    </div>
                    <div class="act-stat">
                        <span class="act-stat-val">${a.count}x</span>
                        <span class="act-stat-label">TIMES</span>
                    </div>
                    <div class="act-stat">
                        <span class="act-stat-val">${a.avg_intensity.toFixed(1)}</span>
                        <span class="act-stat-label">AVG INT.</span>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (err) { console.error(err); }
}

async function loadTrendChart() {
    try {
        const res = await fetch(`${API}/api/analytics/trend?months=1`);
        const data = await res.json();
        const container = document.getElementById('trendChart');
        if (!data.length) {
            container.innerHTML = '<p class="muted-text">Need more data for trends</p>';
            return;
        }

        container.innerHTML = data.map(d => {
            const pct = (d.avg_intensity / 10) * 100;
            const hue = d.avg_intensity > 6 ? 260 : d.avg_intensity > 4 ? 45 : 0;
            return `<div class="trend-bar" data-date="${d._id}"
                        style="height: ${Math.max(pct, 5)}%;
                               background: hsla(${hue}, 60%, 55%, 0.6);"></div>`;
        }).join('');
    } catch (err) { console.error(err); }
}

// ─── Clear All Data ──────────────────────────────────────
async function clearAllData() {
    if (!confirm('⚠️ Delete ALL mood data permanently?')) return;
    if (!confirm('Last chance. This nukes everything.')) return;

    try {
        const res = await fetch(`${API}/api/moods`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Delete failed');
        showToast('💣 All data wiped. Fresh start.', 'info');
        setTimeout(() => location.reload(), 1500);
    } catch (err) {
        showToast('Failed to delete data.', 'error');
    }
}

// ─── Toast ───────────────────────────────────────────────
function showToast(message, type = 'info') {
    const rail = document.getElementById('toastRail');
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    const toast = document.createElement('div');
    toast.className = `toast-item ${type}`;
    toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span> ${message}`;
    rail.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

// ─── Init ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    updateNavPill();
    loadDashboard();
    window.addEventListener('resize', updateNavPill);
});