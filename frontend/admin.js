/* ============================================================
   SmartCert — script.js
   ============================================================ */

const DEV_MODE = false;
let API_BASE = localStorage.getItem('smartcert_api') || 'http://127.0.0.1:5000';

function getToken() {
  return localStorage.getItem('smartcert_token');
}

function getAuthHeaders(json = false) {
  const h = { 'Authorization': `Bearer ${getToken()}` };
  if (json) h['Content-Type'] = 'application/json';
  return h;
}

let allCerts      = [];
let filteredCerts = [];
let currentFilter = 'all';
let currentPage   = 1;
const PAGE_SIZE   = 8;
let certToDelete  = null;
let currentUser   = null;

/* ─── INIT ─── */
document.addEventListener('DOMContentLoaded', async () => {
  await requireAuthOrRedirect();

  const s = document.getElementById('s-url');
  if (s) s.value = API_BASE;

  const fd = document.getElementById('f-date');
  if (fd) fd.value = new Date().toISOString().split('T')[0];

  checkChainStatus();
  loadCertificates();
});

/* ─── AUTH ─── */
async function requireAuthOrRedirect() {
  const token = getToken();
  if (!token) {
    window.location.href = 'login.html';
    return;
  }

  try {
    const res  = await fetch(`${API_BASE}/auth/me`, { headers: getAuthHeaders() });
    if (!res.ok) {
      localStorage.removeItem('smartcert_token');
      window.location.href = 'login.html';
      return;
    }
    const data = await res.json();
    const user = data.user || data;
    currentUser = user;
    const nameEl   = document.getElementById('user-name');
    const roleEl   = document.getElementById('user-role');
    const avatarEl = document.getElementById('user-avatar');
    if (nameEl)   nameEl.textContent   = user.name || (user.email ? user.email.split('@')[0] : 'Admin');
    if (roleEl)   roleEl.textContent   = user.role === 'admin' ? 'Administrateur' : 'Étudiant';
    if (avatarEl) avatarEl.textContent = (user.email || 'A')[0].toUpperCase();
  } catch (err) {
    console.error('Auth error:', err);
    window.location.href = 'login.html';
  }
}

async function logout() {
  await fetch(`${API_BASE}/auth/logout`, { method: 'POST', headers: getAuthHeaders() });
  localStorage.removeItem('smartcert_token');
  window.location.href = 'login.html';
}

/* ─── NAVIGATION ─── */
function showPage(page) {
  const pages = ['dashboard', 'certificates', 'issue', 'verify', 'blockchain', 'settings'];
  pages.forEach(p => {
    const el = document.getElementById('page-' + p);
    if (el) el.style.display = p === page ? '' : 'none';
  });

  const titles = {
    dashboard:    'Dashboard',
    certificates: 'Certificats',
    issue:        'Émettre',
    verify:       'Vérifier',
    blockchain:   'Blockchain',
    settings:     'Paramètres',
  };
  const titleEl = document.getElementById('topbar-title');
  if (titleEl) titleEl.textContent = titles[page] || page;

  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.remove('active');
    if (item.getAttribute('onclick') && item.getAttribute('onclick').includes(`'${page}'`)) {
      item.classList.add('active');
    }
  });

  if (page === 'blockchain') loadChainInfo();
}

/* ─── BLOCKCHAIN STATUS ─── */
async function checkChainStatus() {
  const el = document.getElementById('chain-status-text');
  try {
    const res  = await fetch(`${API_BASE}/chain/status`, { headers: getAuthHeaders() });
    const data = await res.json();
    if (data.connected) {
      el.textContent = `Ethereum Testnet · v${data.web3_version || '—'}`;
    } else {
      el.textContent = 'Non connecté';
      styleChainError(el);
    }
  } catch {
    if (el) el.textContent = 'Backend hors-ligne';
    styleChainError(el);
  }
}

function styleChainError(el) {
  if (!el) return;
  const bs = el.closest('.blockchain-status');
  if (bs) {
    bs.style.background = 'rgba(248,113,113,0.08)';
    bs.style.color      = 'var(--accent-red)';
    bs.style.borderColor = 'rgba(248,113,113,0.22)';
    const dot = bs.querySelector('.status-dot');
    if (dot) dot.style.background = 'var(--accent-red)';
  }
}

async function loadChainInfo() {
  const el = document.getElementById('chainInfo');
  try {
    const res = await fetch(`${API_BASE}/chain/status`, { headers: getAuthHeaders() });
    const d   = await res.json();
    el.innerHTML = `
      <div class="info-grid">
        <div class="info-item"><label>Réseau</label><p>${d.network || 'Ethereum Testnet'}</p></div>
        <div class="info-item"><label>Web3 Version</label><p>${d.web3_version || '—'}</p></div>
        <div class="info-item"><label>Statut</label><p style="color:var(--accent-green)">${d.connected ? '✅ Connecté' : '❌ Déconnecté'}</p></div>
        <div class="info-item"><label>Adresse contrat</label><p style="font-family:'Space Mono',monospace;font-size:11px">${d.contract_address || 'Non déployé'}</p></div>
      </div>
      <div style="background:rgba(15,168,192,0.06);border:1px solid var(--border);border-radius:10px;padding:14px;margin-top:14px">
        <div style="font-size:11px;color:var(--muted);margin-bottom:6px;text-transform:uppercase;letter-spacing:1px">Message</div>
        <div style="font-size:13px;color:var(--text-secondary)">${d.message || '—'}</div>
      </div>`;
  } catch {
    el.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon"><i class="fas fa-plug"></i></div>
        <div class="empty-title">Backend non disponible</div>
        <div class="empty-desc">Démarrez Flask sur ${API_BASE}</div>
      </div>`;
  }
}

/* ─── LOAD CERTIFICATES ─── */
async function loadCertificates() {
  try {
    const res  = await fetch(`${API_BASE}/certificates`, { headers: getAuthHeaders() });
    const data = await res.json();
    allCerts      = data.certificates || data || [];
    filteredCerts = [...allCerts];
    updateStats();
    renderRecentTable();
    renderFullTable();
    updateBadge();
    showToast('Certificats chargés', 'success');
  } catch {
    showToast('Impossible de joindre le backend', 'error');
    allCerts      = [];
    filteredCerts = [];
    renderRecentTable();
    renderFullTable();
    updateStats();
  }
}

/* ─── STATS ─── */
function updateStats() {
  const total    = allCerts.length;
  const verified = allCerts.filter(c => c.status === 'Vérifié').length;
  const pending  = allCerts.filter(c => c.status === 'En attente').length;
  const revoked  = allCerts.filter(c => c.status === 'Révoqué').length;
  const pct      = total ? Math.round(verified / total * 100) : 0;

  setText('stat-total',        total);
  setText('stat-verified',     verified);
  setText('stat-pending',      pending);
  setText('stat-revoked',      revoked);
  setText('stat-verified-pct', `↑ ${pct}% du total`);
}

function updateBadge() {
  setText('cert-count-badge', allCerts.length || '0');
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

/* ─── RENDER RECENT TABLE ─── */
function renderRecentTable() {
  const tbody  = document.getElementById('recentTable');
  const recent = [...allCerts].slice(0, 5);
  if (!recent.length) {
    tbody.innerHTML = emptyRow(6, 'Aucun certificat', 'Commencez par émettre un certificat');
    return;
  }
  tbody.innerHTML = recent.map(c => buildRow(c, false)).join('');
}

/* ─── RENDER FULL TABLE ─── */
function renderFullTable() {
  const tbody = document.getElementById('fullTable');
  const start = (currentPage - 1) * PAGE_SIZE;
  const page  = filteredCerts.slice(start, start + PAGE_SIZE);

  tbody.innerHTML = page.length
    ? page.map(c => buildRow(c, true)).join('')
    : emptyRow(7, 'Aucun résultat', 'Essayez un autre filtre');

  setText('tableInfo', `${filteredCerts.length} certificat${filteredCerts.length !== 1 ? 's' : ''}`);
  buildPagination();
}

function emptyRow(cols, title, desc) {
  return `<tr><td colspan="${cols}">
    <div class="empty-state">
      <div class="empty-icon"><i class="fas fa-inbox"></i></div>
      <div class="empty-title">${title}</div>
      <div class="empty-desc">${desc}</div>
    </div></td></tr>`;
}

function buildRow(c, withCheckbox) {
  const badge = statusBadge(c.status);
  const date  = c.issue_date ? c.issue_date.split('T')[0] : (c.date || '—');
  const chk   = withCheckbox
    ? `<td><input type="checkbox" class="row-chk" data-id="${c.id}"></td>`
    : '';
  const certData = JSON.stringify(c).replace(/'/g, '&#39;');
  return `
    <tr>
      ${chk}
      <td><span class="cert-id">${c.id || c.cert_id || '—'}</span></td>
      <td>
        <div class="recipient-info">
          <div class="recipient-name">${c.recipient_name || c.name || '—'}</div>
          <div class="recipient-email">${c.email || '—'}</div>
        </div>
      </td>
      <td>${c.program || c.programme || '—'}</td>
      <td>${badge}</td>
      <td>${date}</td>
      <td>
        <div class="actions">
          <button class="btn btn-success btn-sm btn-icon" title="Prévisualiser"
            onclick='openPreview(${certData})'>
            <i class="fas fa-eye"></i>
          </button>
          <button class="btn btn-danger btn-sm btn-icon" title="Supprimer"
            onclick="openDelete('${c.id || c.cert_id}')">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </td>
    </tr>`;
}

function statusBadge(status) {
  const map = {
    'Vérifié':    ['verified', '<i class="fas fa-circle-check" style="font-size:9px"></i>'],
    'En attente': ['pending',  '<i class="fas fa-hourglass-half" style="font-size:9px"></i>'],
    'Révoqué':    ['revoked',  '<i class="fas fa-ban" style="font-size:9px"></i>'],
  };
  const [cls, icon] = map[status] || ['pending', ''];
  return `<span class="badge badge-${cls}"><span class="badge-dot"></span>${icon} ${status || 'Inconnu'}</span>`;
}

/* ─── PAGINATION ─── */
function buildPagination() {
  const totalPages = Math.ceil(filteredCerts.length / PAGE_SIZE);
  const el = document.getElementById('pagination');
  if (!el || totalPages <= 1) { if (el) el.innerHTML = ''; return; }

  let html = '';
  if (currentPage > 1)
    html += `<button class="page-btn" onclick="goPage(${currentPage - 1})"><i class="fas fa-chevron-left" style="font-size:10px"></i></button>`;
  for (let i = 1; i <= totalPages; i++)
    html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="goPage(${i})">${i}</button>`;
  if (currentPage < totalPages)
    html += `<button class="page-btn" onclick="goPage(${currentPage + 1})"><i class="fas fa-chevron-right" style="font-size:10px"></i></button>`;
  el.innerHTML = html;
}

function goPage(n) { currentPage = n; renderFullTable(); }

/* ─── FILTERS ─── */
function filterTable(status, btn) {
  currentFilter = status;
  currentPage   = 1;
  document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}

function filterTableSearch(q) { currentPage = 1; applyFilters(q); }

function applyFilters(q) {
  const query = (q ?? document.getElementById('tableSearch').value).toLowerCase();
  filteredCerts = allCerts.filter(c => {
    const matchStatus = currentFilter === 'all' || c.status === currentFilter;
    const matchSearch = !query ||
      (c.id             || '').toLowerCase().includes(query) ||
      (c.cert_id        || '').toLowerCase().includes(query) ||
      (c.recipient_name || c.name || '').toLowerCase().includes(query) ||
      (c.email          || '').toLowerCase().includes(query) ||
      (c.program        || c.programme || '').toLowerCase().includes(query);
    return matchStatus && matchSearch;
  });
  renderFullTable();
}

function handleSearch(q) {
  showPage('certificates');
  const ts = document.getElementById('tableSearch');
  if (ts) ts.value = q;
  applyFilters(q);
}

function toggleSelectAll(cb) {
  document.querySelectorAll('.row-chk').forEach(c => c.checked = cb.checked);
}

/* ─── PREVIEW MODAL ─── */
function openPreview(cert) {
  const c    = cert;
  const date = c.issue_date ? c.issue_date.split('T')[0] : (c.date || '—');

  document.getElementById('certPreviewContent').innerHTML = `
    <div class="cert-border">
      <div class="cert-uni">${c.institution || 'Université SmartCert'}</div>
      <hr style="border-color:#c8d8ea;margin:10px 0">
      <div style="font-size:0.6rem;letter-spacing:2px;text-transform:uppercase;color:#4a6a9a;margin-bottom:6px">Certifie que</div>
      <div class="cert-student">${c.recipient_name || c.name || '—'}</div>
      <div class="cert-desc">a complété avec succès le programme</div>
      <div class="cert-program">${c.program || c.programme || '—'}</div>
      <div class="cert-meta">
        <div class="cert-meta-item">
          <div class="cert-meta-label">Date</div>
          <div class="cert-meta-value">${date}</div>
        </div>
        <div class="cert-meta-item">
          <div class="cert-meta-label">ID</div>
          <div class="cert-meta-value" style="font-family:monospace;font-size:10px">${c.id || c.cert_id || '—'}</div>
        </div>
        <div class="cert-meta-item">
          <div class="cert-meta-label">Statut</div>
          <div class="cert-meta-value" style="color:#1a7a4a">${c.status || 'Vérifié'}</div>
        </div>
      </div>
    </div>`;

  setText('certHashDisplay', c.blockchain_hash || c.tx_hash || 'Hash non disponible');

  document.getElementById('certInfoGrid').innerHTML = `
    <div class="info-item"><label>Bénéficiaire</label><p>${c.recipient_name || c.name || '—'}</p></div>
    <div class="info-item"><label>Email</label><p>${c.email || '—'}</p></div>
    <div class="info-item"><label>Programme</label><p>${c.program || c.programme || '—'}</p></div>
    <div class="info-item"><label>Institution</label><p>${c.institution || '—'}</p></div>
    <div class="info-item"><label>Date d'émission</label><p>${date}</p></div>
    <div class="info-item"><label>Statut</label><p>${c.status || '—'}</p></div>`;

  openModal('previewModal');
}

/* ─── DELETE MODAL ─── */
function openDelete(id) {
  certToDelete = id;
  setText('deleteCertId', `ID : ${id}`);
  openModal('deleteModal');
}

async function confirmDelete() {
  if (!certToDelete) return;
  const btn = document.getElementById('confirmDeleteBtn');
  btn.innerHTML = '<span class="spinner"></span> Suppression…';
  btn.disabled  = true;

  try {
    const res = await fetch(`${API_BASE}/certificates/${certToDelete}`, {
      method: 'DELETE', headers: getAuthHeaders()
    });
    if (res.ok) {
      showToast('Certificat supprimé', 'success');
      await loadCertificates();
    } else {
      showToast('Erreur lors de la suppression', 'error');
    }
  } catch {
    showToast('Backend inaccessible', 'error');
  }

  btn.innerHTML = '<i class="fas fa-trash" style="font-size:11px"></i> Supprimer';
  btn.disabled  = false;
  closeModal('deleteModal');
  certToDelete  = null;
}

/* ─── ISSUE CERTIFICATE ─── */
async function issueCertificate() {
  const name  = document.getElementById('f-name').value.trim();
  const email = document.getElementById('f-email').value.trim();
  const prog  = document.getElementById('f-program').value.trim();
  const inst  = document.getElementById('f-institution').value.trim();
  const date  = document.getElementById('f-date').value;

  if (!name || !email || !prog) {
    showToast('Remplissez les champs obligatoires (*)', 'error');
    return;
  }

  const btn = document.getElementById('issueBtn');
  btn.innerHTML = '<span class="spinner"></span> Enregistrement…';
  btn.disabled  = true;

  try {
    const res = await fetch(`${API_BASE}/certificates`, {
      method:  'POST',
      headers: getAuthHeaders(true),
      body:    JSON.stringify({
        recipient_name: name, email,
        program:        prog,
        institution:    inst || 'SmartCert University',
        issue_date:     date
      }),
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Certificat émis avec succès !', 'success');
      clearIssueForm();
      await loadCertificates();
      showPage('certificates');
    } else {
      showToast(data.error || 'Erreur serveur', 'error');
    }
  } catch {
    showToast('Backend inaccessible', 'error');
  }

  btn.innerHTML = '<i class="fas fa-link" style="font-size:11px"></i> Émettre sur Blockchain';
  btn.disabled  = false;
}

function clearIssueForm() {
  ['f-name', 'f-email', 'f-program', 'f-institution'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  const fd = document.getElementById('f-date');
  if (fd) fd.value = new Date().toISOString().split('T')[0];
}

/* ─── VERIFY CERTIFICATE ─── */
async function verifyCertificate() {
  const id     = document.getElementById('v-id').value.trim();
  const result = document.getElementById('verifyResult');
  if (!id) { showToast('Entrez un ID', 'error'); return; }

  result.innerHTML = `<div style="color:var(--muted);font-size:13px"><span class="spinner"></span> Vérification en cours…</div>`;

  try {
    const res  = await fetch(`${API_BASE}/certificates/verify/${encodeURIComponent(id)}`, { headers: getAuthHeaders() });
    const data = await res.json();

    if (data.valid || data.verified) {
      result.innerHTML = `
        <div style="background:rgba(34,212,160,0.07);border:1px solid rgba(34,212,160,0.22);border-radius:12px;padding:20px">
          <div style="font-size:15px;color:var(--accent-green);font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px">
            <i class="fas fa-circle-check"></i> Certificat Valide
          </div>
          <div class="info-grid" style="margin-top:4px">
            <div class="info-item"><label>Bénéficiaire</label><p>${data.recipient_name || data.name || '—'}</p></div>
            <div class="info-item"><label>Programme</label><p>${data.program || '—'}</p></div>
            <div class="info-item"><label>Date</label><p>${data.issue_date || data.date || '—'}</p></div>
            <div class="info-item"><label>Institution</label><p>${data.institution || '—'}</p></div>
          </div>
          ${data.blockchain_hash ? `<div class="cert-hash-display" style="margin-top:14px">${data.blockchain_hash}</div>` : ''}
        </div>`;
    } else {
      result.innerHTML = `
        <div style="background:rgba(248,113,113,0.07);border:1px solid rgba(248,113,113,0.22);border-radius:12px;padding:20px">
          <div style="font-size:15px;color:var(--accent-red);font-weight:700;margin-bottom:8px;display:flex;align-items:center;gap:8px">
            <i class="fas fa-circle-xmark"></i> Certificat Invalide ou Introuvable
          </div>
          <p style="font-size:13px;color:var(--muted)">${data.message || 'Aucun enregistrement trouvé pour cet identifiant.'}</p>
        </div>`;
    }
  } catch {
    result.innerHTML = `
      <div style="color:var(--accent-red);font-size:13px;display:flex;align-items:center;gap:8px">
        <i class="fas fa-plug"></i> Impossible de joindre le backend
      </div>`;
  }
}

/* ─── EXPORT CSV ─── */
function exportCSV() {
  if (!filteredCerts.length) { showToast('Aucune donnée à exporter', 'error'); return; }
  const headers = ['ID', 'Nom', 'Email', 'Programme', 'Institution', 'Statut', 'Date'];
  const rows = filteredCerts.map(c => [
    c.id || c.cert_id || '',
    c.recipient_name || c.name || '',
    c.email || '',
    c.program || c.programme || '',
    c.institution || '',
    c.status || '',
    c.issue_date || c.date || '',
  ].map(v => `"${v}"`).join(','));
  const csv  = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = 'smartcert_export.csv'; a.click();
  URL.revokeObjectURL(url);
  showToast('Export CSV téléchargé', 'success');
}

/* ─── DOWNLOAD PDF ─── */
function downloadPDF() {
  showToast('Connexion backend pour PDF requise', 'info');
}

/* ─── SETTINGS ─── */
function saveSettings() {
  const url = document.getElementById('s-url').value.trim();
  if (url) {
    API_BASE = url;
    localStorage.setItem('smartcert_api', url);
    showToast('URL sauvegardée', 'success');
    loadCertificates();
    checkChainStatus();
  }
}

/* ─── MODAL UTILS ─── */
function openModal(id)  { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

document.addEventListener('click', e => {
  ['previewModal', 'deleteModal'].forEach(id => {
    const overlay = document.getElementById(id);
    if (e.target === overlay) closeModal(id);
  });
});

/* ─── TOAST ─── */
function showToast(msg, type = 'info') {
  const container = document.getElementById('toastContainer');
  const icons = { success: 'fa-circle-check', error: 'fa-circle-xmark', info: 'fa-circle-info' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<i class="fas ${icons[type] || icons.info}" style="font-size:13px;flex-shrink:0"></i><span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = 'opacity .4s, transform .4s';
    toast.style.opacity    = '0';
    toast.style.transform  = 'translateX(110%)';
    setTimeout(() => toast.remove(), 400);
  }, 3000);
}
