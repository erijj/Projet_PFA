/**
 * SmartCert — auth_guard.js
 * Garde de pages sensibles (dashboard, admin, profil…)
 *
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * INTÉGRATION — à placer dans <head> APRÈS auth.js :
 *
 *   <script src="auth.js"></script>
 *   <script src="auth_guard.js"></script>
 *
 * PROTECTION D'UNE PAGE — appeler en bas du <body> :
 *
 *   <!-- Admin seulement -->
 *   <script>requireAuth(['admin']);</script>
 *
 *   <!-- Tout utilisateur connecté -->
 *   <script>requireAuth();</script>
 *
 * INJECTION AUTOMATIQUE — attributs HTML reconnus :
 *
 *   <span data-auth-name></span>    → nom de l'utilisateur
 *   <span data-auth-email></span>   → adresse email
 *   <span data-auth-role></span>    → libellé du rôle
 *
 *   <div data-role-only="admin">…</div>   → visible admins seulement
 *   <div data-role-only="etudiant">…</div>→ visible étudiants seulement
 *
 * DÉCONNEXION :
 *
 *   <button onclick="handleLogout()">Se déconnecter</button>
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 */

(function () {
  'use strict';

  // ─── Masque la page pendant la vérification ───────────────
  document.documentElement.style.visibility = 'hidden';

  // ─── MESSAGES D'ERREUR LOCALISÉS ─────────────────────────
  const REASONS = {
    session_expired:  'Votre session a expiré. Veuillez vous reconnecter.',
    unauthorized:     'Accès refusé. Vous n\'avez pas les droits nécessaires.',
    logged_out:       'Vous avez été déconnecté.',
  };

  // ─── UTILS ────────────────────────────────────────────────
  function _redirect(page, reason) {
    const params = new URLSearchParams({
      reason,
      return: window.location.pathname,
    });
    window.location.replace(`${page}?${params}`);
  }

  function _showPage() {
    document.documentElement.style.visibility = 'visible';
  }

  function _injectUserInfo() {
    const user = Auth.getUser();
    if (!user) return;

    const ROLE_LABELS = { admin: 'Administrateur', etudiant: 'Étudiant' };

    document.querySelectorAll('[data-auth-name]').forEach(el => {
      el.textContent = user.name || user.email;
    });
    document.querySelectorAll('[data-auth-email]').forEach(el => {
      el.textContent = user.email;
    });
    document.querySelectorAll('[data-auth-role]').forEach(el => {
      el.textContent = ROLE_LABELS[user.role] || user.role;
    });

    // Affiche / masque selon rôle
    document.querySelectorAll('[data-role-only]').forEach(el => {
      const needed = el.getAttribute('data-role-only');
      el.style.display = (user.role === needed) ? '' : 'none';
    });
  }

  function _showSessionMessage() {
    const params  = new URLSearchParams(window.location.search);
    const reason  = params.get('reason');
    const message = REASONS[reason];
    if (!message) return;

    // Injection dans un élément dédié ou création d'une bannière temporaire
    const container = document.getElementById('auth-message');
    if (container) {
      container.textContent = message;
      container.style.display = 'block';
    } else {
      const banner = document.createElement('div');
      banner.textContent = message;
      Object.assign(banner.style, {
        position:   'fixed',
        top:        '16px',
        left:       '50%',
        transform:  'translateX(-50%)',
        background: reason === 'unauthorized' ? '#7f1d1d' : '#1c3d5a',
        color:      '#fff',
        padding:    '10px 24px',
        borderRadius: '8px',
        fontSize:   '0.85rem',
        zIndex:     '9999',
        boxShadow:  '0 4px 20px rgba(0,0,0,0.4)',
      });
      document.body.appendChild(banner);
      setTimeout(() => banner.remove(), 4000);
    }
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  //  API PUBLIQUE
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /**
   * Protège la page courante.
   * @param {string[]} allowedRoles - ex: ['admin'] | ['admin','etudiant'] | []
   * @param {string}   redirectTo   - page de login (défaut: login.html)
   */
  async function requireAuth(allowedRoles = [], redirectTo = 'login.html') {

    // 1. Vérification locale (rapide, synchrone)
    if (!Auth.isAuthenticated()) {
      _redirect(redirectTo, 'session_expired');
      return;
    }

    // 2. Vérification du rôle
    const role = Auth.getRole();
    if (allowedRoles.length > 0 && !allowedRoles.includes(role)) {
      _redirect(redirectTo, 'unauthorized');
      return;
    }

    // 3. Validation serveur (asynchrone)
    const valid = await Auth.verifyWithServer();
    if (!valid) {
      _redirect(redirectTo, 'session_expired');
      return;
    }

    // 4. Tout est OK
    _injectUserInfo();
    _showPage();
    _showSessionMessage();
  }

  /**
   * Déconnexion avec confirmation.
   * @param {boolean} skipConfirm - passe la confirmation si true
   */
  async function handleLogout(skipConfirm = false) {
    if (!skipConfirm && !confirm('Voulez-vous vous déconnecter ?')) return;
    await Auth.logout();
  }

  // Expose sur window
  window.requireAuth  = requireAuth;
  window.handleLogout = handleLogout;

})();
