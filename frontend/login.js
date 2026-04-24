let currentRole = 'admin';

function switchRole(role) {
  currentRole = role;
  const toggle = document.getElementById('roleToggle');
  const btnAdmin = document.getElementById('btnAdmin');
  const btnCand = document.getElementById('btnCandidate');

  if (role === 'admin') {
    toggle.classList.remove('candidate-active');
    btnAdmin.classList.add('active');
    btnCand.classList.remove('active');
    // login
    document.getElementById('loginSubtitle').textContent = 'Connectez-vous à votre espace administrateur';
    document.getElementById('loginBadge').className = 'role-badge admin';
    document.getElementById('loginBadge').innerHTML = '<i class="fas fa-shield-halved"></i> <span>Accès Administrateur</span>';
    // register
    document.getElementById('regSubtitle').textContent = 'Inscription espace administrateur';
    document.getElementById('regBadge').className = 'role-badge admin';
    document.getElementById('regBadge').innerHTML = '<i class="fas fa-shield-halved"></i> <span>Compte Administrateur</span>';
    document.getElementById('adminFields').style.display = 'block';
    document.getElementById('candidateFields').style.display = 'none';
    document.getElementById('btnRegisterText').textContent = 'Créer mon compte administrateur';
  } else {
    toggle.classList.add('candidate-active');
    btnAdmin.classList.remove('active');
    btnCand.classList.add('active');
    // login
    document.getElementById('loginSubtitle').textContent = 'Connectez-vous à votre espace étudiant';
    document.getElementById('loginBadge').className = 'role-badge candidate';
    document.getElementById('loginBadge').innerHTML = '<i class="fas fa-user-graduate"></i> <span>Espace Étudiant</span>';
    // register
    document.getElementById('regSubtitle').textContent = 'Inscription espace étudiant';
    document.getElementById('regBadge').className = 'role-badge candidate';
    document.getElementById('regBadge').innerHTML = '<i class="fas fa-user-graduate"></i> <span>Compte Étudiant</span>';
    document.getElementById('adminFields').style.display = 'none';
    document.getElementById('candidateFields').style.display = 'block';
    document.getElementById('btnRegisterText').textContent = 'Créer mon compte étudiant';
  }
}

function showView(id) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  hideAlert('loginAlert');
  hideAlert('regAlertErr');
  hideAlert('regAlertOk');
}

function togglePwd(inputId, btn) {
  const inp = document.getElementById(inputId);
  const ico = btn.querySelector('i');
  if (inp.type === 'password') {
    inp.type = 'text';
    ico.classList.replace('fa-eye', 'fa-eye-slash');
  } else {
    inp.type = 'password';
    ico.classList.replace('fa-eye-slash', 'fa-eye');
  }
}

function showAlert(id, msg) {
  const el = document.getElementById(id);
  if (msg) {
    const span = el.querySelector('span');
    if (span) span.textContent = msg;
  }
  el.classList.add('show');
}
function hideAlert(id) {
  document.getElementById(id).classList.remove('show');
}

async function doLogin() {
  const email = document.getElementById('loginEmail').value.trim();
  const pass = document.getElementById('loginPass').value;
  const btn = document.querySelector('#viewLogin .btn-submit');
  const alertId = 'loginAlert';

  hideAlert(alertId);

  if (!email || !pass) {
    showAlert(alertId, 'Veuillez remplir tous les champs.');
    return;
  }

  // Visual feedback
  const originalText = btn.innerHTML;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Connexion...';
  btn.disabled = true;

  try {
    const API_BASE = localStorage.getItem('smartcert_api') || 'http://127.0.0.1:5000';
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password: pass })
    });

    const data = await response.json();

    if (response.ok) {
      // Store token and user info
      localStorage.setItem('smartcert_token', data.token);
      localStorage.setItem('smartcert_user', JSON.stringify(data.user));

      // Redirect based on role
      if (data.user.role === 'admin') {
        window.location.href = 'dashboard-admin.html';
      } else {
        window.location.href = 'dashboard_candidat.html';
      }
    } else {
      showAlert(alertId, data.error || 'Identifiants incorrects');
    }
  } catch (error) {
    console.error('Login error:', error);
    const API_BASE = localStorage.getItem('smartcert_api') || 'http://127.0.0.1:5000';
    showAlert(alertId, `Impossible de contacter le serveur (${API_BASE}). Vérifiez que le backend est lancé.`);
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

async function doRegister() {
  const first = document.getElementById('regFirst').value.trim();
  const last = document.getElementById('regLast').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const pass = document.getElementById('regPass').value;
  const conf = document.getElementById('regPassConfirm').value;
  const terms = document.getElementById('terms').checked;
  const btn = document.getElementById('btnRegister');

  hideAlert('regAlertErr');
  hideAlert('regAlertOk');

  if (!first || !last || !email || !pass || !conf) {
    showAlert('regAlertErr', 'Veuillez remplir tous les champs obligatoires.');
    return;
  }
  if (!email.includes('@')) {
    showAlert('regAlertErr', 'Adresse e-mail invalide.');
    return;
  }
  if (pass.length < 8) {
    showAlert('regAlertErr', 'Le mot de passe doit contenir au moins 8 caractères.');
    return;
  }
  if (pass !== conf) {
    showAlert('regAlertErr', 'Les mots de passe ne correspondent pas.');
    return;
  }
  if (!terms) {
    showAlert('regAlertErr', 'Vous devez accepter les conditions d\'utilisation.');
    return;
  }

  let institution = "";
  let student_id = "";

  if (currentRole === 'admin') {
    institution = document.getElementById('regInstitution').value.trim();
    if (!institution) {
      showAlert('regAlertErr', 'Veuillez renseigner l\'institution.');
      return;
    }
  } else {
    student_id = document.getElementById('regStudentId').value.trim();
    if (!student_id) {
      showAlert('regAlertErr', 'Veuillez entrer votre identifiant étudiant.');
      return;
    }
  }

  // Visual feedback
  const originalText = btn.innerHTML;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Création...';
  btn.disabled = true;

  const payload = {
    email,
    password: pass,
    name: `${first} ${last}`,
    role: currentRole, // 'admin' or 'etudiant'
    institution,
    student_id
  };
  
  console.log('Sending registration payload:', payload);

  try {
    const API_BASE = localStorage.getItem('smartcert_api') || 'http://127.0.0.1:5000';
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (response.ok) {
      showAlert('regAlertOk');
      setTimeout(() => {
        showView('viewLogin');
        btn.innerHTML = originalText;
        btn.disabled = false;
        document.getElementById('loginEmail').value = email;
      }, 2000);
    } else {
      showAlert('regAlertErr', data.error || 'Erreur lors de l\'inscription');
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  } catch (error) {
    console.error('Register error:', error);
    showAlert('regAlertErr', 'Impossible de contacter le serveur. Vérifiez que le backend est lancé.');
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

// Enter key on login
['loginEmail', 'loginPass'].forEach(id => {
  document.getElementById(id).addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
});
const legalModal = document.getElementById('legalModal');
const legalTitle = document.getElementById('legalTitle');
const legalBodyDiv = document.getElementById('legalBody');

function showLegal(type) {
  if (type === 'cgu') {
    legalTitle.innerText = 'Conditions d\'utilisation SmartCert';
    legalBodyDiv.innerHTML = `<p><strong>Conditions Générales d'Utilisation (CGU)</strong><br>SmartCert fournit une plateforme de certification numérique infalsifiable via la blockchain. L'utilisateur s'engage à ne pas usurper l'identité d'un tiers. Tout certificat frauduleux entraînera des poursuites. Les données personnelles sont traitées conformément au RGPD. Les administrateurs sont responsables des émissions de certificats.</p>`;
  } else {
    legalTitle.innerText = 'Politique de confidentialité';
    legalBodyDiv.innerHTML = `<p><strong>Politique de confidentialité SmartCert</strong><br>Nous collectons vos nom, email, identifiant étudiant (pour les candidats) et institution (pour les administrateurs). Ces données sont stockées de manière sécurisée et utilisées uniquement pour la délivrance et la vérification des certificats blockchain. Aucune donnée n'est revendue.</p><p>Conforme au Règlement Général sur la Protection des Données (UE) 2016/679.</p>`;
  }
  legalModal.classList.add('active');
}

legalModal.addEventListener('click', (e) => {
  if (e.target === legalModal || e.target.classList.contains('close-legal')) {
    legalModal.classList.remove('active');
  }
});

document.querySelectorAll('.open-legal').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    const doc = link.getAttribute('data-doc');
    showLegal(doc);
  });
});