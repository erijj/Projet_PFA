/* ============================================================
   SmartCert — login.js
   Gère : toggle de rôle, navigation vues, validation,
          connexion, inscription, modal légal, persistance
   ============================================================ */

"use strict";

/* ─── ÉTAT GLOBAL ─────────────────────────────────────────── */
let currentRole = "admin";

/* ─── INITIALISATION ──────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  _initAlerts();
  _initEnterKey();
  _initLegalModal();
  _initPasswordStrength();
  _initRealTimeValidation();
});

/* ─── TOGGLE DE RÔLE ──────────────────────────────────────── */
function switchRole(role) {
  currentRole = role;

  /* Slider visuel */
  const slider = document.getElementById("toggleSlider");
  slider.style.transform = role === "admin" ? "translateX(0)" : "translateX(100%)";

  /* Boutons actifs */
  document.getElementById("btnAdmin").classList.toggle("active", role === "admin");
  document.getElementById("btnCandidate").classList.toggle("active", role === "candidate");

  const isAdmin = role === "admin";

  /* ── VUE LOGIN ── */
  document.getElementById("loginSubtitle").textContent = isAdmin
    ? "Connectez-vous à votre espace administrateur"
    : "Connectez-vous à votre espace candidat";

  const loginBadge = document.getElementById("loginBadge");
  loginBadge.className = "role-badge " + role;
  loginBadge.querySelector("i").className = isAdmin ? "fas fa-shield-halved" : "fas fa-user-graduate";
  document.getElementById("loginBadgeText").textContent = isAdmin
    ? "Accès Administrateur"
    : "Accès Candidat";

  /* ── VUE REGISTER ── */
  document.getElementById("regSubtitle").textContent = isAdmin
    ? "Inscription espace administrateur"
    : "Inscription espace candidat";

  const regBadge = document.getElementById("regBadge");
  regBadge.className = "role-badge " + role;
  regBadge.querySelector("i").className = isAdmin ? "fas fa-shield-halved" : "fas fa-user-graduate";
  document.getElementById("regBadgeText").textContent = isAdmin
    ? "Compte Administrateur"
    : "Compte Candidat";

  document.getElementById("btnRegisterText").textContent = isAdmin
    ? "Créer mon compte administrateur"
    : "Créer mon compte candidat";

  /* Champs spécifiques au rôle */
  document.getElementById("adminFields").style.display = isAdmin ? "" : "none";
  document.getElementById("candidateFields").style.display = isAdmin ? "none" : "";

  /* Réinitialiser les alertes lors du changement de rôle */
  _clearAllAlerts();
}

/* ─── NAVIGATION ENTRE VUES ───────────────────────────────── */
function showView(viewId) {
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.getElementById(viewId).classList.add("active");
  _clearAllAlerts();
}

/* ─── TOGGLE MOT DE PASSE ─────────────────────────────────── */
function togglePwd(inputId, btn) {
  const input = document.getElementById(inputId);
  const icon = btn.querySelector("i");
  if (input.type === "password") {
    input.type = "text";
    icon.className = "fas fa-eye-slash";
    btn.setAttribute("aria-label", "Masquer le mot de passe");
  } else {
    input.type = "password";
    icon.className = "fas fa-eye";
    btn.setAttribute("aria-label", "Afficher le mot de passe");
  }
}

/* ─── CONNEXION ───────────────────────────────────────────── */
function doLogin() {
  _hideAlert("loginAlert");

  const email = document.getElementById("loginEmail").value.trim();
  const pass  = document.getElementById("loginPass").value;

  /* Validations */
  if (!email || !pass) {
    return _showAlert("loginAlert", "Veuillez remplir tous les champs.");
  }
  if (!_isValidEmail(email)) {
    return _showAlert("loginAlert", "Adresse e-mail invalide.");
  }
  if (!pass.length) {
    return _showAlert("loginAlert", "Veuillez entrer votre mot de passe.");
  }

  /* Vérification en base locale (localStorage) */
  const users = _getUsers();
  const user  = users.find(
    (u) => u.email === email && u.password === _encode(pass) && u.role === currentRole
  );

  if (!user) {
    return _showAlert(
      "loginAlert",
      "Identifiants incorrects ou rôle non correspondant."
    );
  }

  /* Session */
  sessionStorage.setItem("smartcert_session", JSON.stringify({
    id:        user.id,
    role:      user.role,
    firstName: user.firstName,
    lastName:  user.lastName,
    email:     user.email,
  }));

  /* Feedback visuel avant redirection */
  const btn = document.querySelector("#viewLogin .btn-submit");
  _setBtnLoading(btn, "Connexion…");

  setTimeout(() => {
    window.location.href = currentRole === "admin"
      ? "admin-dashboard.html"
      : "candidate-dashboard.html";
  }, 900);
}

/* ─── INSCRIPTION ─────────────────────────────────────────── */
function doRegister() {
  _hideAlert("regAlertErr");
  _hideAlert("regAlertOk");

  /* Récupération des valeurs */
  const first        = document.getElementById("regFirst").value.trim();
  const last         = document.getElementById("regLast").value.trim();
  const dobInput     = document.querySelector("#viewRegister input[type='date']");
  const dob          = dobInput ? dobInput.value : "";
  const email        = document.getElementById("regEmail").value.trim();
  const pass         = document.getElementById("regPass").value;
  const passConfirm  = document.getElementById("regPassConfirm").value;
  const terms        = document.getElementById("terms").checked;
  const institution  = document.getElementById("regInstitution").value.trim();
  const studentId    = document.getElementById("regStudentId").value.trim();

  /* ── Validations ─────────────────────────── */
  if (!first || !last || !email || !pass || !passConfirm) {
    return _showAlert("regAlertErr", "Veuillez remplir tous les champs obligatoires.");
  }
  if (!_isValidName(first)) {
    return _showAlert("regAlertErr", "Prénom invalide (2–50 lettres, espaces, tirets ou apostrophes).");
  }
  if (!_isValidName(last)) {
    return _showAlert("regAlertErr", "Nom invalide (2–50 lettres, espaces, tirets ou apostrophes).");
  }
  if (dob) {
    const age = _calcAge(dob);
    if (age < 18) {
      return _showAlert("regAlertErr", "Vous devez avoir au moins 18 ans pour créer un compte.");
    }
    if (age > 120) {
      return _showAlert("regAlertErr", "Date de naissance invalide.");
    }
  }
  if (!_isValidEmail(email)) {
    return _showAlert("regAlertErr", "Adresse e-mail invalide (format : nom@domaine.com).");
  }
  if (!_isStrongPassword(pass)) {
    return _showAlert(
      "regAlertErr",
      "Mot de passe trop faible : 12+ caractères requis avec au moins 1 majuscule, 1 minuscule, 1 chiffre et 1 caractère spécial (@$!%*?&)."
    );
  }
  if (pass !== passConfirm) {
    return _showAlert("regAlertErr", "Les mots de passe ne correspondent pas.");
  }
  if (!terms) {
    return _showAlert("regAlertErr", "Vous devez accepter les conditions d'utilisation et la politique de confidentialité.");
  }

  /* Champs spécifiques au rôle */
  if (currentRole === "admin" && !institution) {
    return _showAlert("regAlertErr", "Veuillez renseigner le nom de votre institution.");
  }
  if (currentRole === "candidate" && !studentId) {
    return _showAlert("regAlertErr", "Veuillez renseigner votre numéro d'identifiant étudiant.");
  }

  /* Vérification doublon */
  const users = _getUsers();
  if (users.find((u) => u.email === email)) {
    return _showAlert("regAlertErr", "Un compte avec cette adresse e-mail existe déjà.");
  }

  /* Construction de l'objet utilisateur */
  const newUser = {
    id:        Date.now(),
    role:      currentRole,
    firstName: _sanitize(first),
    lastName:  _sanitize(last),
    dob:       dob || null,
    email:     email.toLowerCase(),
    password:  _encode(pass),
    createdAt: new Date().toISOString(),
    ...(currentRole === "admin"
      ? { institution: _sanitize(institution) }
      : { studentId:   _sanitize(studentId)   }),
  };

  users.push(newUser);
  _saveUsers(users);

  /* Feedback succès */
  document.getElementById("regAlertOk").style.display = "flex";
  const btn = document.getElementById("btnRegister");
  _setBtnLoading(btn, "Compte créé !");
  btn.disabled = true;

  /* Redirection vers login */
  setTimeout(() => {
    _resetRegisterForm();
    showView("viewLogin");
    _hideAlert("regAlertOk");
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-user-plus"></i> <span id="btnRegisterText">Créer mon compte ' +
      (currentRole === "admin" ? "administrateur" : "candidat") + "</span>";
    /* Pré-remplir l'email dans le login pour faciliter la connexion */
    document.getElementById("loginEmail").value = newUser.email;
  }, 2200);
}

/* ─── MODAL LÉGAL ─────────────────────────────────────────── */
const _legalDocs = {
  cgu: {
    title: "Conditions Générales d'Utilisation",
    body: `
      <p><strong>Dernière mise à jour :</strong> Janvier 2026</p>
      <h5>1. Objet</h5>
      <p>Les présentes CGU définissent les modalités d'accès et d'utilisation de la plateforme SmartCert, 
      permettant l'émission, la vérification et la gestion de certificats académiques sur la blockchain Ethereum.</p>
      <h5>2. Accès à la plateforme</h5>
      <p>L'accès à SmartCert est réservé aux utilisateurs dûment inscrits, à savoir les administrateurs 
      d'établissements accrédités et les candidats enregistrés. Toute tentative d'accès non autorisé est 
      strictement prohibée.</p>
      <h5>3. Obligations de l'utilisateur</h5>
      <ul>
        <li>Fournir des informations exactes, complètes et à jour lors de l'inscription.</li>
        <li>Ne pas partager ses identifiants de connexion.</li>
        <li>Ne pas tenter de compromettre l'intégrité de la blockchain ou des données.</li>
        <li>Signaler immédiatement toute utilisation frauduleuse de son compte.</li>
      </ul>
      <h5>4. Propriété intellectuelle</h5>
      <p>Tous les éléments de la plateforme SmartCert (interface, code source, logo, contenus) sont protégés 
      par les lois relatives à la propriété intellectuelle. Toute reproduction non autorisée est interdite.</p>
      <h5>5. Limitation de responsabilité</h5>
      <p>SmartCert ne saurait être tenu responsable des interruptions de service dues à des maintenances, 
      des attaques informatiques ou des défaillances réseau indépendantes de sa volonté.</p>
      <h5>6. Résiliation</h5>
      <p>SmartCert se réserve le droit de suspendre ou supprimer tout compte en cas de violation des présentes CGU.</p>
      <h5>7. Droit applicable</h5>
      <p>Les présentes CGU sont régies par le droit tunisien. Tout litige sera soumis à la compétence des 
      tribunaux de Tunis.</p>`,
  },
  privacy: {
    title: "Politique de Confidentialité",
    body: `
      <p><strong>Dernière mise à jour :</strong> Janvier 2026</p>
      <h5>1. Responsable du traitement</h5>
      <p>SmartCert est responsable du traitement de vos données personnelles dans le cadre de l'utilisation 
      de la plateforme.</p>
      <h5>2. Données collectées</h5>
      <ul>
        <li>Données d'identité : nom, prénom, date de naissance.</li>
        <li>Données de contact : adresse e-mail.</li>
        <li>Données de rôle : institution (administrateurs) ou identifiant étudiant (candidats).</li>
        <li>Données de connexion : date/heure de connexion, adresse IP (à des fins de sécurité).</li>
      </ul>
      <h5>3. Finalités du traitement</h5>
      <ul>
        <li>Gestion des comptes utilisateurs et authentification.</li>
        <li>Émission et vérification de certificats sur la blockchain Ethereum.</li>
        <li>Sécurité et prévention des fraudes.</li>
        <li>Amélioration de la plateforme.</li>
      </ul>
      <h5>4. Base légale</h5>
      <p>Le traitement est fondé sur l'exécution contractuelle (CGU acceptées) et l'intérêt légitime 
      de SmartCert en matière de sécurité.</p>
      <h5>5. Conservation des données</h5>
      <p>Les données sont conservées pendant la durée d'activité du compte, puis archivées 3 ans 
      conformément aux obligations légales, avant suppression définitive.</p>
      <h5>6. Droits des utilisateurs</h5>
      <p>Conformément au RGPD et à la loi tunisienne n°2004-63, vous disposez des droits suivants :</p>
      <ul>
        <li>Droit d'accès à vos données.</li>
        <li>Droit de rectification.</li>
        <li>Droit à l'effacement (sous conditions).</li>
        <li>Droit à la portabilité.</li>
        <li>Droit d'opposition au traitement.</li>
      </ul>
      <p>Pour exercer vos droits : <a href="mailto:privacy@smartcert.io">privacy@smartcert.io</a></p>
      <h5>7. Sécurité</h5>
      <p>Vos données sont protégées par des mesures techniques et organisationnelles adaptées 
      (chiffrement, contrôle d'accès, audit régulier).</p>`,
  },
};

function _initLegalModal() {
  document.querySelectorAll(".open-legal").forEach((link) => {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      const doc = this.getAttribute("data-doc");
      if (!_legalDocs[doc]) return;
      document.getElementById("legalTitle").textContent = _legalDocs[doc].title;
      document.getElementById("legalBody").innerHTML   = _legalDocs[doc].body;
      document.getElementById("legalModal").classList.add("active");
      document.body.style.overflow = "hidden";
    });
  });

  /* Fermeture via bouton */
  document.querySelectorAll(".close-legal").forEach((btn) => {
    btn.addEventListener("click", _closeLegalModal);
  });

  /* Fermeture au clic sur le fond */
  document.getElementById("legalModal").addEventListener("click", function (e) {
    if (e.target === this) _closeLegalModal();
  });

  /* Fermeture via Echap */
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") _closeLegalModal();
  });
}

function _closeLegalModal() {
  document.getElementById("legalModal").classList.remove("active");
  document.body.style.overflow = "";
}

/* ─── FORCE DU MOT DE PASSE ───────────────────────────────── */
function _initPasswordStrength() {
  const passInput = document.getElementById("regPass");
  if (!passInput) return;

  /* Création dynamique de la barre si absente */
  let bar = document.getElementById("strengthBar");
  if (!bar) {
    const wrapper = passInput.closest(".input-wrap");
    const container = document.createElement("div");
    container.innerHTML = `
      <div id="strengthBar" style="height:4px;border-radius:2px;margin-top:6px;transition:width .4s,background .4s;width:0;background:#ccc"></div>
      <div id="strengthLabel" style="font-size:0.7rem;margin-top:4px;color:var(--muted);min-height:1rem"></div>`;
    wrapper.insertAdjacentElement("afterend", container);
    bar = document.getElementById("strengthBar");
  }

  passInput.addEventListener("input", () => {
    const score = _scorePassword(passInput.value);
    const levels = [
      { pct: "0%",   color: "#ccc",    label: "" },
      { pct: "25%",  color: "#e74c3c", label: "Très faible" },
      { pct: "50%",  color: "#e67e22", label: "Faible" },
      { pct: "75%",  color: "#f1c40f", label: "Moyen" },
      { pct: "100%", color: "#27ae60", label: "Fort" },
    ];
    const lvl = levels[score];
    bar.style.width      = lvl.pct;
    bar.style.background = lvl.color;
    document.getElementById("strengthLabel").textContent = lvl.label;
    document.getElementById("strengthLabel").style.color = lvl.color;
  });
}

function _scorePassword(p) {
  if (!p) return 0;
  let score = 0;
  if (p.length >= 12)              score++;
  if (/[A-Z]/.test(p))             score++;
  if (/[0-9]/.test(p))             score++;
  if (/[@$!%*?&]/.test(p))         score++;
  return score;
}

/* ─── VALIDATION EN TEMPS RÉEL ────────────────────────────── */
function _initRealTimeValidation() {
  /* Email login */
  _addBlurValidation("loginEmail", (v) =>
    !v || _isValidEmail(v) ? "" : "Format d'email invalide."
  );

  /* Champs du formulaire d'inscription */
  _addBlurValidation("regFirst", (v) =>
    !v || _isValidName(v) ? "" : "Prénom : 2–50 lettres, tirets ou apostrophes."
  );
  _addBlurValidation("regLast", (v) =>
    !v || _isValidName(v) ? "" : "Nom : 2–50 lettres, tirets ou apostrophes."
  );
  _addBlurValidation("regEmail", (v) =>
    !v || _isValidEmail(v) ? "" : "Format d'email invalide."
  );
  _addBlurValidation("regPassConfirm", (v) => {
    const p = document.getElementById("regPass").value;
    return v && v !== p ? "Les mots de passe ne correspondent pas." : "";
  });
}

function _addBlurValidation(id, validator) {
  const el = document.getElementById(id);
  if (!el) return;

  /* Créer ou réutiliser le span d'erreur inline */
  let hint = el.closest(".input-wrap")?.nextElementSibling;
  if (!hint || !hint.classList.contains("field-hint")) {
    hint = document.createElement("div");
    hint.className = "field-hint";
    hint.style.cssText = "font-size:0.7rem;color:#e74c3c;min-height:1rem;margin-top:3px;transition:opacity .2s;";
    el.closest(".input-wrap")?.insertAdjacentElement("afterend", hint);
  }

  el.addEventListener("blur", () => {
    hint.textContent = validator(el.value.trim());
  });
  el.addEventListener("input", () => {
    if (hint.textContent) hint.textContent = validator(el.value.trim());
  });
}

/* ─── TOUCHES ENTRÉE ──────────────────────────────────────── */
function _initEnterKey() {
  ["loginEmail", "loginPass"].forEach((id) => {
    document.getElementById(id)?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") doLogin();
    });
  });

  ["regFirst", "regLast", "regEmail", "regPass", "regPassConfirm",
   "regInstitution", "regStudentId"].forEach((id) => {
    document.getElementById(id)?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") doRegister();
    });
  });
}

/* ─── ALERTES ─────────────────────────────────────────────── */
function _initAlerts() {
  ["loginAlert", "regAlertErr", "regAlertOk"].forEach(_hideAlert);
}

function _showAlert(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  const msgEl = document.getElementById(id + "Msg");
  if (msgEl && msg) msgEl.textContent = msg;
  el.style.display = "flex";
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function _hideAlert(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "none";
}

function _clearAllAlerts() {
  ["loginAlert", "regAlertErr", "regAlertOk"].forEach(_hideAlert);
}

/* ─── PERSISTANCE (localStorage) ─────────────────────────── */
function _getUsers() {
  try {
    return JSON.parse(localStorage.getItem("smartcert_users") || "[]");
  } catch {
    return [];
  }
}

function _saveUsers(users) {
  localStorage.setItem("smartcert_users", JSON.stringify(users));
}

/* ─── UTILITAIRES ─────────────────────────────────────────── */
function _isValidEmail(email) {
  return /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(email);
}

function _isValidName(name) {
  return /^[A-Za-zÀ-ÿ\s\-']{2,50}$/.test(name);
}

function _isStrongPassword(p) {
  return /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$/.test(p);
}

function _calcAge(dob) {
  const birth = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const m = today.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
  return age;
}

/* Encodage simple (Base64) — NE PAS utiliser en production sans hachage côté serveur */
function _encode(str) {
  return btoa(unescape(encodeURIComponent(str)));
}

/* Échapper les caractères HTML pour prévenir les injections XSS */
function _sanitize(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");
}

/* Feedback visuel sur les boutons */
function _setBtnLoading(btn, text) {
  if (!btn) return;
  btn.innerHTML = `<i class="fas fa-circle-notch fa-spin"></i> ${text}`;
}

/* Réinitialiser le formulaire d'inscription */
function _resetRegisterForm() {
  ["regFirst", "regLast", "regEmail", "regPass", "regPassConfirm",
   "regInstitution", "regStudentId"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  const dob = document.querySelector("#viewRegister input[type='date']");
  if (dob) dob.value = "";
  document.getElementById("terms").checked = false;
  const bar = document.getElementById("strengthBar");
  if (bar) { bar.style.width = "0"; bar.style.background = "#ccc"; }
  const lbl = document.getElementById("strengthLabel");
  if (lbl) lbl.textContent = "";
}