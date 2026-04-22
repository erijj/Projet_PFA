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
    document.getElementById('loginSubtitle').textContent = 'Connectez-vous à votre espace candidat';
    document.getElementById('loginBadge').className = 'role-badge candidate';
    document.getElementById('loginBadge').innerHTML = '<i class="fas fa-user-graduate"></i> <span>Espace Candidat</span>';
    // register
    document.getElementById('regSubtitle').textContent = 'Inscription espace candidat';
    document.getElementById('regBadge').className = 'role-badge candidate';
    document.getElementById('regBadge').innerHTML = '<i class="fas fa-user-graduate"></i> <span>Compte Candidat</span>';
    document.getElementById('adminFields').style.display = 'none';
    document.getElementById('candidateFields').style.display = 'block';
    document.getElementById('btnRegisterText').textContent = 'Créer mon compte candidat';
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

function doLogin() {
  const email = document.getElementById('loginEmail').value.trim();
  const pass = document.getElementById('loginPass').value;
  hideAlert('loginAlert');
  if (!email || !pass) {
    showAlert('loginAlert', 'Veuillez remplir tous les champs.');
    return;
  }
  if (!email.includes('@')) {
    showAlert('loginAlert', 'Adresse e-mail invalide.');
    return;
  }
  // Simulate login — replace with real API call
  if (currentRole === 'admin') {
    window.location.href = 'dashboard_admin.html';
  } else {
    window.location.href = 'dashboard_candidat.html';
  }
}

function doRegister() {
  const first = document.getElementById('regFirst').value.trim();
  const last = document.getElementById('regLast').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const pass = document.getElementById('regPass').value;
  const conf = document.getElementById('regPassConfirm').value;
  const terms = document.getElementById('terms').checked;
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
  if (currentRole === 'admin') {
    const inst = document.getElementById('regInstitution').value.trim();
    const role = document.getElementById('regRole').value;
    if (!inst || !role) {
      showAlert('regAlertErr', 'Veuillez renseigner l\'institution et le rôle.');
      return;
    }
  } else {
    const sid = document.getElementById('regStudentId').value.trim();
    if (!sid) {
      showAlert('regAlertErr', 'Veuillez entrer votre identifiant étudiant.');
      return;
    }
  }

  // Simulate registration success
  showAlert('regAlertOk');
  document.getElementById('btnRegister').disabled = true;
  setTimeout(() => {
    showView('viewLogin');
    document.getElementById('btnRegister').disabled = false;
    document.getElementById('loginEmail').value = email;
  }, 1800);
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