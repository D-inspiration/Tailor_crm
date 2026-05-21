const API_BASE = '';
let currentTab = 'mail';

function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

function showTab(tab) {
    document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('[id^="tab-"]').forEach(el => el.classList.add('hidden'));
    document.getElementById('tab-' + tab).classList.remove('hidden');
    currentTab = tab;
    if (tab === 'mail') loadMail();
    if (tab === 'sent') loadSent();
    if (tab === 'subscribers') loadSubscribers();
    if (tab === 'stats') loadStats();
}

function showSubTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById('subtab-msg-stats').classList.toggle('hidden', tab !== 'msg-stats');
    document.getElementById('subtab-sent-stats').classList.toggle('hidden', tab !== 'sent-stats');
    document.getElementById('subtab-sub-stats').classList.toggle('hidden', tab !== 'sub-stats');
}

function statusBadge(status) {
    const map = { unread: 'badge-unread', read: 'badge-read', archived: 'badge-archived', spam: 'badge-spam', active: 'badge-active', pending: 'badge-pending', unsubscribed: 'badge-unsubscribed', sent: 'badge-read', delivered: 'badge-active', failed: 'badge-spam', queued: 'badge-pending' };
    return '<span class="badge ' + (map[status] || '') + '">' + status + '</span>';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleString();
}

function closeModal() {
    document.getElementById('msg-modal').classList.remove('show');
}

// ============================================================
// STATS
// ============================================================
async function loadStats() {
    try {
        const [mailRes, sentRes, subRes] = await Promise.all([
            fetch(API_BASE + '/dashboard/stats'),
            fetch(API_BASE + '/mail/senders'),  // Get sender groups (no limit)
            fetch(API_BASE + '/subscribers')
        ]);
        const mailData = await mailRes.json();
        const sentData = await sentRes.json();
        const subData = await subRes.json();

        // Calculate total sent from sender groups
        let totalSent = 0;
        if (sentData.by_sender) {
            totalSent = sentData.by_sender.reduce((sum, g) => sum + (g.count || 0), 0);
        }

        document.getElementById('stat-inbox-total').textContent = mailData.messages?.total ?? 0;
        document.getElementById('stat-unread').textContent = mailData.messages?.unread ?? 0;
        document.getElementById('stat-sent').textContent = totalSent;
        document.getElementById('stat-active').textContent = subData.stats?.active ?? 0;

        document.getElementById('msg-stats-json').textContent = JSON.stringify(mailData.messages, null, 2);
        document.getElementById('sent-stats-json').textContent = JSON.stringify({
            total_sent: totalSent,
            by_sender: sentData.by_sender,
            by_domain: sentData.by_domain
        }, null, 2);
        document.getElementById('sub-stats-json').textContent = JSON.stringify(subData.stats, null, 2);
    } catch (e) { showToast('Failed to load stats'); }
}


// ============================================================
// INBOX
// ============================================================
async function loadMail() {
    try {
        const res = await fetch(API_BASE + '/mail/inbox');
        const data = await res.json();
        const tbody = document.getElementById('mail-list');
        if (!data.messages?.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty">No messages yet</td></tr>';
            return;
        }
        tbody.innerHTML = data.messages.map(function(m) {
            return '<tr>' +
                '<td>' + statusBadge(m.status) + '</td>' +
                '<td class="sender">' + escapeHtml(m.sender) + '</td>' +
                '<td class="subject">' + escapeHtml(m.subject || '(no subject)') + '</td>' +
                '<td class="message-preview">' + escapeHtml(m.preview) + '</td>' +
                '<td>' + formatDate(m.received_at) + '</td>' +
                '<td>' +
                    '<button class="btn btn-sm" onclick="viewMessage(' + m.id + ')">View</button>' +
                    (m.status === 'unread' ? ' <button class="btn btn-sm btn-success" onclick="markRead(' + m.id + ')">Read</button>' : '') +
                    ' <button class="btn btn-sm btn-danger" onclick="archiveMsg(' + m.id + ')">Archive</button>' +
                '</td>' +
            '</tr>';
        }).join('');
    } catch (e) { showToast('Failed to load mail'); }
}

async function searchMail() {
    const q = document.getElementById('mail-search').value;
    if (!q) { loadMail(); return; }
    try {
        const res = await fetch(API_BASE + '/mail/search?q=' + encodeURIComponent(q));
        const data = await res.json();
        const tbody = document.getElementById('mail-list');
        if (!data.messages?.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty">No results</td></tr>';
            return;
        }
        tbody.innerHTML = data.messages.map(function(m) {
            return '<tr>' +
                '<td>' + statusBadge(m.status || 'unread') + '</td>' +
                '<td class="sender">' + escapeHtml(m.sender) + '</td>' +
                '<td class="subject">' + escapeHtml(m.subject || '(no subject)') + '</td>' +
                '<td class="message-preview">' + escapeHtml(m.preview || '') + '</td>' +
                '<td>—</td>' +
                '<td><button class="btn btn-sm" onclick="viewMessage(' + m.id + ')">View</button></td>' +
            '</tr>';
        }).join('');
    } catch (e) { showToast('Search failed'); }
}

async function viewMessage(id) {
    try {
        const res = await fetch(API_BASE + '/mail/' + id);
        const m = await res.json();
        document.getElementById('modal-subject').textContent = m.subject || '(no subject)';
        document.getElementById('modal-from').textContent = m.sender;
        document.getElementById('modal-to').textContent = m.recipient;
        document.getElementById('modal-date').textContent = formatDate(m.received_at);
        document.getElementById('modal-body').textContent = m.body || '(no text body)';
        if (m.html) {
            document.getElementById('modal-html').style.display = 'block';
            document.getElementById('modal-html').innerHTML = m.html;
        } else {
            document.getElementById('modal-html').style.display = 'none';
        }
        document.getElementById('msg-modal').classList.add('show');
    } catch (e) { showToast('Failed to load message'); }
}

async function markRead(id) {
    try {
        await fetch(API_BASE + '/mail/' + id + '/read', { method: 'POST' });
        showToast('Marked as read');
        loadMail();
    } catch (e) { showToast('Failed'); }
}

async function archiveMsg(id) {
    try {
        await fetch(API_BASE + '/mail/' + id + '/archive', { method: 'POST' });
        showToast('Archived');
        loadMail();
    } catch (e) { showToast('Failed'); }
}

// ============================================================
// SENT MESSAGES + SENDER GROUPS
// ============================================================
async function loadSent() {
    try {
        const senderFilter = document.getElementById('sender-filter').value;
        let url = API_BASE + '/mail/sent?limit=100';
        if (senderFilter) url += '&sender=' + encodeURIComponent(senderFilter);

        const res = await fetch(url);
        const data = await res.json();

        // Populate sender filter dropdown
        const select = document.getElementById('sender-filter');
        const currentVal = select.value;
        if (select.options.length <= 1 && data.grouped_by_sender?.length) {
            data.grouped_by_sender.forEach(function(g) {
                const opt = document.createElement('option');
                opt.value = g.sender;
                opt.textContent = g.sender + ' (' + g.count + ')';
                select.appendChild(opt);
            });
            select.value = currentVal;
        }

        // Render sender group sidebar
        const groupDiv = document.getElementById('sender-group-list');
        if (data.grouped_by_sender?.length) {
            groupDiv.innerHTML = data.grouped_by_sender.map(function(g) {
                return '<div style="padding: 8px; cursor: pointer; border-radius: 6px; margin-bottom: 4px; ' +
                    (g.sender === senderFilter ? 'background: #3b82f6;' : 'background: #0f172a;') +
                    '" onclick="filterBySender(\'' + g.sender + '\')">' +
                    '<div style="font-weight: 500; font-size: 13px;">' + escapeHtml(g.sender) + '</div>' +
                    '<div style="font-size: 11px; color: #64748b;">' + g.count + ' emails</div>' +
                    '</div>';
            }).join('');
        } else {
            groupDiv.innerHTML = '<div class="empty" style="padding: 20px;">No sent messages</div>';
        }

        // Render sent messages table
        const tbody = document.getElementById('sent-list');
        if (!data.messages?.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty">No sent messages</td></tr>';
            return;
        }
        tbody.innerHTML = data.messages.map(function(m) {
            return '<tr>' +
                '<td>' + escapeHtml(m.to) + '</td>' +
                '<td class="subject">' + escapeHtml(m.subject) + '</td>' +
                '<td>' + statusBadge(m.status) + '</td>' +
                '<td>' + escapeHtml(m.category || '—') + '</td>' +
                '<td>' + formatDate(m.sent_at) + '</td>' +
            '</tr>';
        }).join('');
    } catch (e) { showToast('Failed to load sent messages'); }
}

function filterBySender(sender) {
    document.getElementById('sender-filter').value = sender;
    loadSent();
}

// ============================================================
// COMPOSER
// ============================================================
function openComposer() {
    document.getElementById('composer-modal').classList.add('show');
}

function closeComposer() {
    document.getElementById('composer-modal').classList.remove('show');
    document.getElementById('compose-form').reset();
}

async function sendEmail(event) {
    event.preventDefault();
    const fromSelect = document.getElementById('compose-from');
    const fromEmail = fromSelect.value;
    const fromName = fromSelect.options[fromSelect.selectedIndex].dataset.name;

    const payload = {
        to: document.getElementById('compose-to').value,
        subject: document.getElementById('compose-subject').value,
        from: fromEmail,
        from_name: fromName,
        html: document.getElementById('compose-html').value,
        text: document.getElementById('compose-text').value,
        category: document.getElementById('compose-category').value,
    };

    try {
        const res = await fetch(API_BASE + '/mail/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            showToast('Email sent! ID: ' + data.resend_id);
            closeComposer();
            loadSent();
            loadStats();
        } else {
            showToast('Failed: ' + (data.error || 'Unknown error'));
        }
    } catch (e) { showToast('Failed to send email'); }
    return false;
}

// ============================================================
// SUBSCRIBERS
// ============================================================
async function loadSubscribers() {
    try {
        const q = document.getElementById('sub-search').value;
        const url = q ? API_BASE + '/subscribers?tag=' + encodeURIComponent(q) : API_BASE + '/subscribers';
        const res = await fetch(url);
        const data = await res.json();
        const tbody = document.getElementById('sub-list');
        if (!data.subscribers?.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty">No subscribers yet</td></tr>';
            return;
        }
        tbody.innerHTML = data.subscribers.map(function(s) {
            var tags = (s.tags || []).map(function(t) {
                return '<span class="badge badge-read">' + escapeHtml(t) + '</span>';
            }).join(' ');
            return '<tr>' +
                '<td>' + escapeHtml(s.email) + '</td>' +
                '<td>' + statusBadge(s.status) + '</td>' +
                '<td>' + escapeHtml(s.plan) + '</td>' +
                '<td>' + tags + '</td>' +
                '<td>' + escapeHtml(s.source || '—') + '</td>' +
                '<td>' + formatDate(s.created_at) + '</td>' +
                '<td>' +
                    (s.status === 'pending' ? '<button class="btn btn-sm btn-success" onclick="confirmSub(\'' + s.email + '\')">Confirm</button>' : '') +
                    (s.status !== 'unsubscribed' ? ' <button class="btn btn-sm btn-danger" onclick="unsub(\'' + s.email + '\')">Unsub</button>' : '') +
                '</td>' +
            '</tr>';
        }).join('');
    } catch (e) { showToast('Failed to load subscribers'); }
}

async function confirmSub(email) {
    try {
        await fetch(API_BASE + '/subscribers/' + encodeURIComponent(email) + '/confirm', { method: 'POST' });
        showToast('Subscriber confirmed');
        loadSubscribers();
    } catch (e) { showToast('Failed'); }
}

async function unsub(email) {
    try {
        await fetch(API_BASE + '/subscribers/' + encodeURIComponent(email) + '/unsubscribe', { method: 'POST' });
        showToast('Unsubscribed');
        loadSubscribers();
    } catch (e) { showToast('Failed'); }
}

// ============================================================
// INIT
// ============================================================
loadStats();
loadMail();

