/* ══════════════════════════════════════════════
   moodboard v4 — app logic
   ══════════════════════════════════════════════ */

let pickedMood = null;
let pickedEmoji = null;
let chatBusy = false;
let threadId = localStorage.getItem('mb4_thread') || 't_' + Date.now();
localStorage.setItem('mb4_thread', threadId);

// ─── Init ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    setGreeting();
    loadStats();
    updateLogTime();
    setInterval(updateLogTime, 60000);
});

function setGreeting() {
    const h = new Date().getHours();
    const el = document.getElementById('greeting');
    if (el) {
        if (h < 12) el.textContent = 'Good morning';
        else if (h < 17) el.textContent = 'Good afternoon';
        else el.textContent = 'Good evening';
    }
}

function updateLogTime() {
    const el = document.getElementById('logTime');
    if (el) {
        const now = new Date();
        el.textContent = now.toLocaleDateString('en-US', {
            weekday: 'long', month: 'long', day: 'numeric'
        }) + ' · ' + now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }
}

// ─── Navigation ────────────────────────────────
function go(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const el = document.getElementById('page-' + page);
    if (el) {
        el.classList.remove('active');
        el.offsetHeight;
        el.classList.add('active');
    }
    const nav = document.querySelector(`.nav-item[data-page="${page}"]`);
    if (nav) nav.classList.add('active');

    if (page === 'home') loadStats();
    if (page === 'insights') loadAllInsights();
    if (page === 'journal') loadJournals();
    if (page === 'goals') loadGoals();

    // Close mobile sidebar
    document.getElementById('sidebar')?.classList.remove('open');
}

function toggleSidebar() {
    document.getElementById('sidebar')?.classList.toggle('open');
}

// ─── Stats ─────────────────────────────────────
async function loadStats() {
    try {
        const r = await fetch('/api/stats');
        const d = await r.json();
        if (!d.has_data) return;
        anim('mTotal', d.total);
        anim('mStreak', d.streak);
        document.getElementById('sideStreak').textContent = d.streak;
        document.getElementById('mPositive').textContent = d.positive_pct + '%';
        document.getElementById('mIntensity').textContent = d.avg_intensity + '/10';

        const banner = document.getElementById('trendBanner');
        document.getElementById('trendText').textContent = d.trend;
        banner.classList.remove('positive', 'mixed', 'rough');
        banner.classList.add(d.trend_type);
    } catch (e) { console.error(e); }
}

function anim(id, end) {
    const el = document.getElementById(id);
    if (!el) return;
    let start = 0;
    const dur = 600;
    const t0 = performance.now();
    function step(t) {
        const p = Math.min((t - t0) / dur, 1);
        const v = Math.round(start + (end - start) * (1 - Math.pow(1 - p, 3)));
        el.textContent = v;
        if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

// ─── Mood Logging ──────────────────────────────
function pickMood(btn) {
    document.querySelectorAll('.mood-opt').forEach(b => b.classList.remove('picked'));
    btn.classList.add('picked');
    pickedMood = btn.dataset.mood;
    pickedEmoji = btn.dataset.emoji;
    const extras = document.getElementById('logExtras');
    if (extras) extras.classList.add('show');
}

function toggleChip(btn) {
    btn.classList.toggle('on');
}

async function submitMood() {
    if (!pickedMood) { toast('Pick a mood first', 'err'); return; }
    const btn = document.getElementById('submitBtn');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    const acts = [...document.querySelectorAll('#actGroup .chip.on')].map(c => c.dataset.val);
    const body = {
        mood: pickedMood,
        note: document.getElementById('noteInput')?.value || '',
        intensity: parseInt(document.getElementById('intSlider')?.value || 5),
        activities: acts,
        sleep_hours: parseFloat(document.getElementById('sleepInput')?.value || 0),
        water_glasses: parseInt(document.getElementById('waterInput')?.value || 0),
        exercise_mins: parseInt(document.getElementById('exerciseInput')?.value || 0),
    };

    try {
        const r = await fetch('/api/mood', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!r.ok) throw new Error();

        document.getElementById('savedEmoji').textContent = pickedEmoji;
        document.getElementById('savedDetail').textContent =
            `${pickedMood} · intensity ${body.intensity}/10` +
            (acts.length ? ` · ${acts.join(', ')}` : '');
        document.getElementById('savedOverlay').classList.add('show');
        toast(pickedEmoji + ' Mood saved', 'ok');
    } catch (e) {
        toast('Failed to save', 'err');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save entry';
    }
}

function closeSaved() {
    document.getElementById('savedOverlay').classList.remove('show');
    resetLog();
    go('home');
}

function resetLog() {
    document.querySelectorAll('.mood-opt').forEach(b => b.classList.remove('picked'));
    document.querySelectorAll('.chip').forEach(b => b.classList.remove('on'));
    pickedMood = null;
    pickedEmoji = null;
    document.getElementById('intSlider').value = 5;
    document.getElementById('intVal').textContent = '5';
    document.getElementById('noteInput').value = '';
    document.getElementById('charC').textContent = '0';
    document.getElementById('sleepInput').value = '';
    document.getElementById('waterInput').value = '';
    document.getElementById('exerciseInput').value = '';
    document.getElementById('logExtras').classList.remove('show');
}

// ─── Chat ──────────────────────────────────────
function chatKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}
function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 100) + 'px';
}
function sendSugg(txt) {
    document.getElementById('chatInput').value = txt;
    sendMessage();
}
function askFullAnalysis() {
    sendSugg('Give me a comprehensive analysis of all my mood data — every pattern, trigger, correlation, and personalized suggestions');
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg || chatBusy) return;
    chatBusy = true;
    document.getElementById('sendBtn').disabled = true;

    addMsg(msg, 'user');
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('chatSugg').style.display = 'none';

    const tid = showTyping();

    try {
        const r = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg, thread_id: threadId })
        });
        if (!r.ok) throw new Error();
        const d = await r.json();
        removeTyping(tid);
        addMsg(d.reply, 'bot');
    } catch (e) {
        removeTyping(tid);
        addMsg('Something went wrong. Try again?', 'bot');
    } finally {
        chatBusy = false;
        document.getElementById('sendBtn').disabled = false;
        input.focus();
    }
}

function addMsg(text, type) {
    const c = document.getElementById('chatMsgs');
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const avi = type === 'bot' ? '🧠' : '👤';
    let html = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code style="background:var(--accent-bg);padding:1px 5px;border-radius:3px;font-family:var(--mono);font-size:12px;">$1</code>')
        .replace(/\n/g, '<br>');
    c.insertAdjacentHTML('beforeend', `
        <div class="msg ${type}">
            <div class="msg-avi">${avi}</div>
            <div class="msg-body">
                <div class="msg-text">${html}</div>
                <div class="msg-ts">${time}</div>
            </div>
        </div>
    `);
    c.scrollTop = c.scrollHeight;
}

function showTyping() {
    const c = document.getElementById('chatMsgs');
    const id = 'typ_' + Date.now();
    c.insertAdjacentHTML('beforeend', `
        <div class="msg bot" id="${id}">
            <div class="msg-avi">🧠</div>
            <div class="msg-body">
                <div class="msg-text"><div class="typing-anim"><span></span><span></span><span></span></div></div>
            </div>
        </div>
    `);
    c.scrollTop = c.scrollHeight;
    return id;
}

function removeTyping(id) {
    document.getElementById(id)?.remove();
}

function clearChat() {
    if (!confirm('Clear chat history?')) return;
    document.getElementById('chatMsgs').innerHTML = `
        <div class="msg bot">
            <div class="msg-avi">🧠</div>
            <div class="msg-body">
                <div class="msg-text">Fresh start! What do you want to know about your mood patterns?</div>
                <div class="msg-ts">just now</div>
            </div>
        </div>
    `;
    threadId = 't_' + Date.now();
    localStorage.setItem('mb4_thread', threadId);
    document.getElementById('chatSugg').style.display = 'flex';
    toast('Chat cleared', 'info');
}

// ─── Insights ──────────────────────────────────
async function loadAllInsights() {
    loadDistChart();
    loadWeeklyChart();
    loadHourlyChart();
    loadActChart();
    loadTrendChart();
}

async function loadDistChart() {
    try {
        const r = await fetch('/api/stats');
        const d = await r.json();
        const el = document.getElementById('distChart');
        if (!d.has_data || !d.distribution?.length) {
            el.innerHTML = '<p class="muted">No data yet</p>';
            return;
        }
        const max = Math.max(...d.distribution.map(x => x.count));
        el.innerHTML = d.distribution.map(x => `
            <div class="bar-item">
                <span class="bar-name">${x.emoji} ${x.mood}</span>
                <div class="bar-track"><div class="bar-fill" style="width:0%;background:${x.cat==='positive'?'var(--green)':x.cat==='negative'?'var(--red)':'var(--accent)'};" data-w="${Math.max(Math.round(x.count/max*100),4)}"></div></div>
                <span class="bar-count">${x.count}</span>
            </div>
        `).join('');
        setTimeout(() => {
            el.querySelectorAll('.bar-fill').forEach((b, i) => {
                setTimeout(() => b.style.width = b.dataset.w + '%', i * 60);
            });
        }, 100);
    } catch (e) { console.error(e); }
}

async function loadWeeklyChart() {
    try {
        const r = await fetch('/api/analytics/weekly');
        const d = await r.json();
        const el = document.getElementById('weeklyChart');
        if (!d.length) { el.innerHTML = '<p class="muted">No data</p>'; return; }
        const max = Math.max(...d.map(x => x.count));
        el.innerHTML = d.map(x => {
            const pos = x.positive || 0;
            const neg = x.negative || 0;
            return `
                <div class="wk-row">
                    <span class="wk-day">${(x._id||'').substring(0,3)}</span>
                    <div class="wk-blocks">
                        <div class="wk-block" style="background:var(--green);opacity:${0.2+pos/Math.max(max,1)*0.8};flex:${pos||1};" title="Positive: ${pos}"></div>
                        <div class="wk-block" style="background:var(--red);opacity:${0.2+neg/Math.max(max,1)*0.8};flex:${neg||1};" title="Negative: ${neg}"></div>
                    </div>
                    <span class="wk-count">${x.count}</span>
                </div>
            `;
        }).join('');
    } catch (e) { console.error(e); }
}

async function loadHourlyChart() {
    try {
        const r = await fetch('/api/analytics/hourly');
        const d = await r.json();
        const el = document.getElementById('hourlyChart');
        if (!d.length) { el.innerHTML = '<p class="muted">No data</p>'; return; }
        const map = {};
        d.forEach(h => map[h._id] = h);
        const max = Math.max(...d.map(x => x.count));
        let html = '<div class="hourly-bars">';
        for (let h = 0; h < 24; h++) {
            const item = map[h];
            const pct = item ? Math.max((item.count / max) * 100, 3) : 3;
            const pos = item ? (item.positive || 0) / Math.max(item.count, 1) : 0;
            const bg = pos > 0.6 ? 'var(--green)' : pos > 0.3 ? 'var(--accent)' : 'var(--red)';
            html += `<div class="hr-bar" style="height:${pct}%;background:${item ? bg : 'var(--bg3)'};" title="${h}:00 — ${item?.count || 0} entries"></div>`;
        }
        html += '</div>';
        el.innerHTML = html;
    } catch (e) { console.error(e); }
}

async function loadActChart() {
    try {
        const r = await fetch('/api/analytics/activities');
        const d = await r.json();
        const el = document.getElementById('actChart');
        if (!d.length) {
            el.innerHTML = '<p class="muted">Log moods with activities to see correlations</p>';
            return;
        }
        el.innerHTML = '<div class="act-list">' + d.map(a => `
            <div class="act-item">
                <div class="act-name">${a._id}</div>
                <div class="act-stats">
                    <span class="act-num ${a.positive_pct>50?'act-good':'act-bad'}">${Math.round(a.positive_pct)}% pos</span>
                    <span>${a.count}x</span>
                    <span>avg ${a.avg_intensity.toFixed(1)}</span>
                </div>
            </div>
        `).join('') + '</div>';
    } catch (e) { console.error(e); }
}

async function loadTrendChart() {
    try {
        const r = await fetch('/api/analytics/trend?days=30');
        const d = await r.json();
        const el = document.getElementById('trendChart');
        if (!d.length) { el.innerHTML = '<p class="muted">Need more data</p>'; return; }
        let html = '<div class="trend-bars">';
        d.forEach(t => {
            const pct = Math.max((t.avg_intensity / 10) * 100, 5);
            const pos = t.positive / Math.max(t.count, 1);
            const bg = pos > 0.6 ? 'var(--green)' : pos > 0.3 ? 'var(--accent)' : 'var(--red)';
            html += `<div class="tr-bar" style="height:${pct}%;background:${bg};opacity:0.7;" title="${t._id}: avg ${t.avg_intensity}"></div>`;
        });
        html += '</div>';
        el.innerHTML = html;
    } catch (e) { console.error(e); }
}

async function nukeData() {
    if (!confirm('Delete ALL mood data? This cannot be undone.')) return;
    if (!confirm('Are you absolutely sure?')) return;
    try {
        await fetch('/api/moods', { method: 'DELETE' });
        toast('All data deleted', 'info');
        setTimeout(() => location.reload(), 1000);
    } catch (e) { toast('Failed', 'err'); }
}

// ─── Journal ───────────────────────────────────
function openJournalForm() {
    document.getElementById('journalForm').style.display = 'block';
    document.getElementById('jTitle').focus();
}
function closeJournalForm() {
    document.getElementById('journalForm').style.display = 'none';
    document.getElementById('jTitle').value = '';
    document.getElementById('jContent').value = '';
    document.getElementById('jMoodTag').value = '';
}

async function saveJournal() {
    const title = document.getElementById('jTitle').value.trim();
    const content = document.getElementById('jContent').value.trim();
    const mood = document.getElementById('jMoodTag').value;
    if (!content) { toast('Write something first', 'err'); return; }

    try {
        await fetch('/api/journal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title || 'Untitled', content, mood_tag: mood })
        });
        toast('Journal saved', 'ok');
        closeJournalForm();
        loadJournals();
    } catch (e) { toast('Failed to save', 'err'); }
}

async function loadJournals() {
    try {
        const r = await fetch('/api/journals');
        const d = await r.json();
        const el = document.getElementById('journalList');
        if (!d.entries?.length) {
            el.innerHTML = '<p class="muted">No journal entries yet. Write your first one!</p>';
            return;
        }
        el.innerHTML = d.entries.map(j => `
            <div class="j-entry">
                <div class="j-entry-title">${esc(j.title || 'Untitled')}</div>
                <div class="j-entry-content">${esc(j.content)}</div>
                <div class="j-entry-meta">
                    <span>${j.date}</span>
                    <span>${j.time || ''}</span>
                    <span>${j.word_count || 0} words</span>
                    ${j.mood_tag ? `<span class="j-entry-tag">${j.mood_tag}</span>` : ''}
                </div>
            </div>
        `).join('');
    } catch (e) { console.error(e); }
}

// ─── Goals ─────────────────────────────────────
async function addGoal() {
    const input = document.getElementById('goalInput');
    const text = input.value.trim();
    if (!text) return;
    const cat = document.getElementById('goalCat').value;

    try {
        await fetch('/api/goal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, category: cat })
        });
        input.value = '';
        toast('Goal added', 'ok');
        loadGoals();
    } catch (e) { toast('Failed', 'err'); }
}

async function loadGoals() {
    try {
        const r = await fetch('/api/goals');
        const d = await r.json();
        const el = document.getElementById('goalList');
        if (!d.goals?.length) {
            el.innerHTML = '<p class="muted">No goals yet. Set your first intention!</p>';
            return;
        }

        const catEmojis = {
            wellness: '🧘', fitness: '💪', social: '👥',
            creative: '🎨', learning: '📚', career: '💼'
        };

        el.innerHTML = d.goals.map(g => `
            <div class="goal-row ${g.completed ? 'done' : ''}">
                <button class="goal-check" onclick="toggleGoalUI('${g._id}')">${g.completed ? '✓' : ''}</button>
                <span class="goal-text">${esc(g.text)}</span>
                <span class="goal-cat">${catEmojis[g.category] || '🎯'} ${g.category}</span>
                <button class="goal-del" onclick="delGoal('${g._id}')">×</button>
            </div>
        `).join('');
    } catch (e) { console.error(e); }
}

async function toggleGoalUI(id) {
    try {
        await fetch(`/api/goal/${id}/toggle`, { method: 'PATCH' });
        loadGoals();
    } catch (e) { toast('Failed', 'err'); }
}

async function delGoal(id) {
    try {
        await fetch(`/api/goal/${id}`, { method: 'DELETE' });
        loadGoals();
    } catch (e) { toast('Failed', 'err'); }
}

// ─── Utils ─────────────────────────────────────
function toast(msg, type = 'info') {
    const c = document.getElementById('toasts');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => t.remove(), 3000);
}

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}
