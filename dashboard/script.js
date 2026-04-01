/* ============================================================
   SmartCert — script.js
   Backend Flask URL configurable via localStorage
   ============================================================ */

// ─── CONFIG ───────────────────────────────────────────────
let API_BASE = localStorage.getItem('smartcert_api') || 'http://127.0.0.1:5000';

// ─── STATE ────────────────────────────────────────────────
let allCerts     = [];          // all fetched certificates
let filteredCerts = [];         // after filter/search
let currentFilter = 'all';
let currentPage   = 1;
const PAGE_SIZE   = 8;
let certToDelete  = null;       // id of cert pending delete confirmation

// ─── INIT ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // init settings input
  const s = document.getElementById('s-url');
  if (s) s.value = API_BASE;

  // set today as default issue date
  const fd = document.getElementById('f-date');
  if (fd) fd.value = new Date().toISOString().split('T')[0];

  checkChainStatus();
  loadCertificates();
});

// ─── NAVIGATION ───────────────────────────────────────────
function showPage(page) {
  const pages = ['dashboard','certificates','issue','verify','blockchain','settings'];
  pages.forEach(p => {
    const el = document.getElementById('page-' + p);
    if (el) el.style.display = p === page ? '' : 'none';
  });

  // update topbar title
  const titles = {
    dashboard: '📊 Dashboard',
    certificates: '📜 Certificats',
    issue: '➕ Émettre',
    verify: '🔍 Vérifier',
    blockchain: '⛓️ Blockchain',
    settings: '⚙️ Paramètres',
  };
  document.getElementById('topbar-title').textContent = titles[page] || page;

  // active nav item
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.remove('active');
    if (item.getAttribute('onclick') && item.getAttribute('onclick').includes(`'${page}'`)) {
      item.classList.add('active');
    }
  });

  // lazy loads
  if (page === 'blockchain') loadChainInfo();
}

// ─── BLOCKCHAIN STATUS ────────────────────────────────────
async function checkChainStatus() {
  const el = document.getElementById('chain-status-text');
  try {
    const res = await fetch(`${API_BASE}/chain/status`);
    const data = await res.json();
    if (data.connected) {
      el.textContent = `Ethereum Testnet · v${data.web3_version || '—'}`;
    } else {
      el.textContent = 'Non connecté';
      el.closest('.blockchain-status').style.background = 'rgba(239,68,68,.08)';
      el.closest('.blockchain-status').style.color = 'var(--accent-red)';
    }
  } catch {
    el.textContent = 'Backend hors-ligne';
    const bs = el.closest('.blockchain-status');
    if (bs) { bs.style.background='rgba(239,68,68,.08)'; bs.style.color='var(--accent-red)'; bs.querySelector('.status-dot').style.background='var(--accent-red)'; }
  }
}

async function loadChainInfo() {
  const el = document.getElementById('chainInfo');
  try {
    const res = await fetch(`${API_BASE}/chain/status`);
    const d = await res.json();
    el.innerHTML = `
      <div class="info-grid">
        <div class="info-item"><label>Réseau</label><p>${d.network || 'Ethereum Testnet'}</p></div>
        <div class="info-item"><label>Web3 Version</label><p>${d.web3_version || '—'}</p></div>
        <div class="info-item"><label>Statut</label><p style="color:var(--accent-green)">${d.connected ? '✅ Connecté' : '❌ Déconnecté'}</p></div>
        <div class="info-item"><label>Adresse contrat</label><p style="font-family:'Space Mono',monospace;font-size:11px">${d.contract_address || 'Non déployé'}</p></div>
      </div>
      <div style="background:rgba(59,130,246,.06);border:1px solid var(--border);border-radius:8px;padding:14px;margin-top:12px">
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px">Message</div>
        <div style="font-size:13px;color:var(--text-secondary)">${d.message || '—'}</div>
      </div>`;
  } catch {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">🔌</div><div class="empty-title">Backend non disponible</div><div class="empty-desc">Démarrez Flask sur ${API_BASE}</div></div>`;
  }
}

// ─── LOAD CERTIFICATES ────────────────────────────────────
async function loadCertificates() {
  try {
    const res = await fetch(`${API_BASE}/certificates`);
    const data = await res.json();
    allCerts = data.certificates || data || [];
    filteredCerts = [...allCerts];
    updateStats();
    renderRecentTable();
    renderFullTable();
    updateBadge();
    showToast('✅ Certificats chargés', 'success');
  } catch {
    showToast('❌ Impossible de joindre le backend', 'error');
    allCerts = [];
    filteredCerts = [];
    renderRecentTable();
    renderFullTable();
    updateStats();
  }
}

// ─── STATS ────────────────────────────────────────────────
function updateStats() {
  const total    = allCerts.length;
  const verified = allCerts.filter(c => c.status === 'Vérifié').length;
  const pending  = allCerts.filter(c => c.status === 'En attente').length;
  const revoked  = allCerts.filter(c => c.status === 'Révoqué').length;
  const pct      = total ? Math.round(verified / total * 100) : 0;

  document.getElementById('stat-total').textContent    = total;
  document.getElementById('stat-verified').textContent = verified;
  document.getElementById('stat-pending').textContent  = pending;
  document.getElementById('stat-revoked').textContent  = revoked;
  document.getElementById('stat-verified-pct').textContent = `↑ ${pct}% du total`;
}

function updateBadge() {
  document.getElementById('cert-count-badge').textContent = allCerts.length || '0';
}

// ─── RENDER RECENT TABLE (dashboard) ─────────────────────
function renderRecentTable() {
  const tbody = document.getElementById('recentTable');
  const recent = [...allCerts].slice(0, 5);
  if (!recent.length) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="empty-icon">📭</div><div class="empty-title">Aucun certificat</div><div class="empty-desc">Commencez par émettre un certificat</div></div></td></tr>`;
    return;
  }
  tbody.innerHTML = recent.map(c => buildRow(c, false)).join('');
}

// ─── RENDER FULL TABLE ────────────────────────────────────
function renderFullTable() {
  const tbody = document.getElementById('fullTable');
  const start = (currentPage - 1) * PAGE_SIZE;
  const page  = filteredCerts.slice(start, start + PAGE_SIZE);

  if (!page.length) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-title">Aucun résultat</div><div class="empty-desc">Essayez un autre filtre</div></div></td></tr>`;
  } else {
    tbody.innerHTML = page.map(c => buildRow(c, true)).join('');
  }

  // info
  document.getElementById('tableInfo').textContent =
    `${filteredCerts.length} certificat${filteredCerts.length !== 1 ? 's' : ''}`;
  buildPagination();
}

function buildRow(c, withCheckbox) {
  const badge = statusBadge(c.status);
  const date  = c.issue_date ? c.issue_date.split('T')[0] : (c.date || '—');
  const chk   = withCheckbox ? `<td><input type="checkbox" class="row-chk" data-id="${c.id}"></td>` : '';
  return `
    <tr>
      ${chk}
      <td><span class="cert-id">${c.id || c.cert_id || '—'}</span></td>
      <td><div class="recipient-info"><div class="recipient-name">${c.recipient_name || c.name || '—'}</div><div class="recipient-email">${c.email || '—'}</div></div></td>
      <td>${c.program || c.programme || '—'}</td>
      <td>${badge}</td>
      <td>${date}</td>
      <td><div class="actions">
        <button class="btn btn-success btn-sm btn-icon" title="Prévisualiser" onclick='openPreview(${JSON.stringify(c)})'>👁</button>
        <button class="btn btn-danger btn-sm btn-icon" title="Supprimer" onclick="openDelete('${c.id || c.cert_id}')">🗑</button>
      </div></td>
    </tr>`;
}

function statusBadge(status) {
  const map = {
    'Vérifié':    ['verified',  '✅'],
    'En attente': ['pending',   '⏳'],
    'Révoqué':    ['revoked',   '🚫'],
  };
  const [cls, icon] = map[status] || ['pending', '❓'];
  return `<span class="badge badge-${cls}"><span class="badge-dot"></span>${icon} ${status || 'Inconnu'}</span>`;
}

// ─── PAGINATION ───────────────────────────────────────────
function buildPagination() {
  const totalPages = Math.ceil(filteredCerts.length / PAGE_SIZE);
  const el = document.getElementById('pagination');
  if (totalPages <= 1) { el.innerHTML = ''; return; }
  let html = '';
  if (currentPage > 1) html += `<button class="page-btn" onclick="goPage(${currentPage-1})">‹</button>`;
  for (let i = 1; i <= totalPages; i++) {
    html += `<button class="page-btn ${i===currentPage?'active':''}" onclick="goPage(${i})">${i}</button>`;
  }
  if (currentPage < totalPages) html += `<button class="page-btn" onclick="goPage(${currentPage+1})">›</button>`;
  el.innerHTML = html;
}

function goPage(n) { currentPage = n; renderFullTable(); }

// ─── FILTER ───────────────────────────────────────────────
function filterTable(status, btn) {
  currentFilter = status;
  currentPage = 1;
  document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}

function filterTableSearch(q) {
  currentPage = 1;
  applyFilters(q);
}

function applyFilters(q) {
  const query = (q ?? document.getElementById('tableSearch').value).toLowerCase();
  filteredCerts = allCerts.filter(c => {
    const matchStatus = currentFilter === 'all' || c.status === currentFilter;
    const matchSearch = !query ||
      (c.id || '').toLowerCase().includes(query) ||
      (c.cert_id || '').toLowerCase().includes(query) ||
      (c.recipient_name || c.name || '').toLowerCase().includes(query) ||
      (c.email || '').toLowerCase().includes(query) ||
      (c.program || c.programme || '').toLowerCase().includes(query);
    return matchStatus && matchSearch;
  });
  renderFullTable();
}

// Global search (topbar)
function handleSearch(q) {
  showPage('certificates');
  document.getElementById('tableSearch').value = q;
  applyFilters(q);
}

// Select all checkbox
function toggleSelectAll(cb) {
  document.querySelectorAll('.row-chk').forEach(c => c.checked = cb.checked);
}

// ─── PREVIEW MODAL ────────────────────────────────────────
function openPreview(cert) {
  const c = cert;
  const date = c.issue_date ? c.issue_date.split('T')[0] : (c.date || '—');

  document.getElementById('certPreviewContent').innerHTML = `
    <div class="cert-border">
      <div class="cert-uni">${c.institution || 'Université SmartCert'}</div>
      <hr style="border-color:#c8d8ea;margin:10px 0">
      <div class="cert-title">Certifie que</div>
      <div class="cert-student">${c.recipient_name || c.name || '—'}</div>
      <div class="cert-desc">a complété avec succès le programme</div>
      <div class="cert-program">${c.program || c.programme || '—'}</div>
      <div class="cert-meta">
        <div class="cert-meta-item"><div class="cert-meta-label">Date</div><div class="cert-meta-value">${date}</div></div>
        <div class="cert-meta-item"><div class="cert-meta-label">ID</div><div class="cert-meta-value" style="font-family:monospace;font-size:11px">${c.id || c.cert_id || '—'}</div></div>
        <div class="cert-meta-item"><div class="cert-meta-label">Statut</div><div class="cert-meta-value" style="color:#1a7a4a">${c.status || 'Vérifié'}</div></div>
      </div>
    </div>`;

  document.getElementById('certHashDisplay').textContent =
    c.blockchain_hash || c.tx_hash || 'Hash non disponible';

  document.getElementById('certInfoGrid').innerHTML = `
    <div class="info-item"><label>Bénéficiaire</label><p>${c.recipient_name || c.name || '—'}</p></div>
    <div class="info-item"><label>Email</label><p>${c.email || '—'}</p></div>
    <div class="info-item"><label>Programme</label><p>${c.program || c.programme || '—'}</p></div>
    <div class="info-item"><label>Institution</label><p>${c.institution || '—'}</p></div>
    <div class="info-item"><label>Date d'émission</label><p>${date}</p></div>
    <div class="info-item"><label>Statut</label><p>${c.status || '—'}</p></div>`;

  openModal('previewModal');
}

// ─── DELETE MODAL ─────────────────────────────────────────
function openDelete(id) {
  certToDelete = id;
  document.getElementById('deleteCertId').textContent = `ID : ${id}`;
  openModal('deleteModal');
}

async function confirmDelete() {
  if (!certToDelete) return;
  const btn = document.getElementById('confirmDeleteBtn');
  btn.innerHTML = '<span class="spinner"></span> Suppression…';
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/certificates/${certToDelete}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('🗑 Certificat supprimé', 'success');
      await loadCertificates();
    } else {
      showToast('❌ Erreur lors de la suppression', 'error');
    }
  } catch {
    showToast('❌ Backend inaccessible', 'error');
  }

  btn.innerHTML = '🗑 Supprimer';
  btn.disabled = false;
  closeModal('deleteModal');
  certToDelete = null;
}

// ─── ISSUE CERTIFICATE ────────────────────────────────────
async function issueCertificate() {
  const name   = document.getElementById('f-name').value.trim();
  const email  = document.getElementById('f-email').value.trim();
  const prog   = document.getElementById('f-program').value.trim();
  const inst   = document.getElementById('f-institution').value.trim();
  const date   = document.getElementById('f-date').value;

  if (!name || !email || !prog) {
    showToast('⚠ Remplissez les champs obligatoires', 'error'); return;
  }

  const btn = document.getElementById('issueBtn');
  btn.innerHTML = '<span class="spinner"></span> Enregistrement…';
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/certificates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipient_name: name, email, program: prog, institution: inst, issue_date: date }),
    });
    const data = await res.json();
    if (res.ok) {
      showToast('✅ Certificat émis avec succès !', 'success');
      clearIssueForm();
      await loadCertificates();
      showPage('certificates');
    } else {
      showToast(`❌ ${data.error || 'Erreur serveur'}`, 'error');
    }
  } catch {
    showToast('❌ Backend inaccessible', 'error');
  }

  btn.innerHTML = '🔗 Émettre sur Blockchain';
  btn.disabled = false;
}

function clearIssueForm() {
  ['f-name','f-email','f-program','f-institution'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.getElementById('f-date').value = new Date().toISOString().split('T')[0];
}

// ─── VERIFY CERTIFICATE ───────────────────────────────────
async function verifyCertificate() {
  const id = document.getElementById('v-id').value.trim();
  const result = document.getElementById('verifyResult');
  if (!id) { showToast('⚠ Entrez un ID', 'error'); return; }

  result.innerHTML = `<div style="color:var(--text-muted);font-size:13px"><span class="spinner"></span> Vérification en cours…</div>`;

  try {
    const res = await fetch(`${API_BASE}/certificates/verify/${encodeURIComponent(id)}`);
    const data = await res.json();

    if (data.valid || data.verified) {
      result.innerHTML = `
        <div style="background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.25);border-radius:10px;padding:20px">
          <div style="font-size:18px;margin-bottom:8px">✅ Certificat Valide</div>
          <div class="info-grid" style="margin-top:12px">
            <div class="info-item"><label>Bénéficiaire</label><p>${data.recipient_name || data.name || '—'}</p></div>
            <div class="info-item"><label>Programme</label><p>${data.program || '—'}</p></div>
            <div class="info-item"><label>Date</label><p>${data.issue_date || data.date || '—'}</p></div>
            <div class="info-item"><label>Institution</label><p>${data.institution || '—'}</p></div>
          </div>
          ${data.blockchain_hash ? `<div class="cert-hash-display" style="margin-top:12px">${data.blockchain_hash}</div>` : ''}
        </div>`;
    } else {
      result.innerHTML = `
        <div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25);border-radius:10px;padding:20px">
          <div style="font-size:18px;color:var(--accent-red)">❌ Certificat Invalide ou Introuvable</div>
          <p style="font-size:13px;color:var(--text-muted);margin-top:8px">${data.message || 'Aucun enregistrement trouvé pour cet identifiant.'}</p>
        </div>`;
    }
  } catch {
    result.innerHTML = `<div style="color:var(--accent-red);font-size:13px">❌ Impossible de joindre le backend</div>`;
  }
}

// ─── EXPORT CSV ───────────────────────────────────────────
function exportCSV() {
  if (!filteredCerts.length) { showToast('⚠ Aucune donnée à exporter', 'error'); return; }
  const headers = ['ID','Nom','Email','Programme','Institution','Statut','Date'];
  const rows = filteredCerts.map(c => [
    c.id || c.cert_id || '',
    c.recipient_name || c.name || '',
    c.email || '',
    c.program || c.programme || '',
    c.institution || '',
    c.status || '',
    c.issue_date || c.date || '',
  ].map(v => `"${v}"`).join(','));
  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = 'smartcert_export.csv'; a.click();
  URL.revokeObjectURL(url);
  showToast('⬇ Export CSV téléchargé', 'success');
}

// ─── DOWNLOAD PDF ─────────────────────────────────────────
function downloadPDF() {
  showToast('ℹ Connexion backend pour PDF requise', 'info');
  // TODO: call API_BASE/certificates/{id}/pdf
}

// ─── SETTINGS ─────────────────────────────────────────────
function saveSettings() {
  const url = document.getElementById('s-url').value.trim();
  if (url) {
    API_BASE = url;
    localStorage.setItem('smartcert_api', url);
    showToast('✅ URL sauvegardée', 'success');
    loadCertificates();
    checkChainStatus();
  }
}

// ─── MODAL UTILS ──────────────────────────────────────────
function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

// click outside to close
document.addEventListener('click', e => {
  ['previewModal','deleteModal'].forEach(id => {
    const overlay = document.getElementById(id);
    if (e.target === overlay) closeModal(id);
  });
});

// ─── TOAST ────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = msg;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = 'opacity .4s, transform .4s';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 400);
  }, 3000);
}