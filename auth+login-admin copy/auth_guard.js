/**
 * SmartCert — auth_guard.js (VERSION COOKIE)
 * Compatible avec app.py — sessions HttpOnly Cookie
 *
 * DIFFÉRENCE AVEC L'ANCIENNE VERSION :
 *   ✗ Avant : vérifiait un JWT dans sessionStorage (synchrone)
 *   ✓ Maintenant : interroge /auth/me via Cookie (asynchrone)
 *
 * INTÉGRATION — dans <head> APRÈS auth.js :
 *
 *   <script src="../auth+login-admin/auth.js"></script>
 *   <script src="../auth+login-admin/auth_guard.js"></script>
 *
 * PROTECTION D'UNE PAGE — en bas du <body> :
 *
 *   <!-- Admin seulement -->
 *   <script>requireAuth(['admin']);</script>
 *
 *   <!-- Tout utilisateur connecté -->
 *   <script>requireAuth();</script>
 *
 * ATTRIBUTS HTML AUTOMATIQUES :
 *
 *   <span data-auth-email></span>       → email utilisateur
 *   <span data-auth-role></span>        → rôle (Administrateur / Étudiant)
 *   <div data-role-only="admin">…</div> → visible admins seulement
 *
 * DÉCONNEXION :
 *
 *   <button onclick="handleLogout()">Se déconnecter</button>
 */

(function () {
  'use strict';

  // Masquer la page pendant la vérification — évite le flash de contenu
  document.documentElement.style.visibility = 'hidden';

  const LOGIN_PAGE = '../auth+login-admin/login.html';

  const ROLE_LABELS = {
    admin:    'Administrateur',
    etudiant: 'Étudiant',
  };

  // ─── REDIRECT ─────────────────────────────────────────
  function _redirect(reason) {
    window.location.replace(
      `${LOGIN_PAGE}?reason=${reason}&return=${encodeURIComponent(window.location.pathname)}`
    );
  }

  // ─── AFFICHER LA PAGE ─────────────────────────────────
  function _showPage() {
    document.documentElement.style.visibility = 'visible';
  }

  // ─── INJECTER INFOS UTILISATEUR ───────────────────────
  function _injectUserInfo(user) {
    if (!user) return;

    document.querySelectorAll('[data-auth-email]').forEach(el => {
      el.textContent = user.email || '—';
    });
    document.querySelectorAll('[data-auth-role]').forEach(el => {
      el.textContent = ROLE_LABELS[user.role] || user.role;
    });
    document.querySelectorAll('[data-auth-name]').forEach(el => {
      el.textContent = user.email ? user.email.split('@')[0] : '—';
    });

    // Afficher / masquer selon rôle
    document.querySelectorAll('[data-role-only]').forEach(el => {
      el.style.display = (el.getAttribute('data-role-only') === user.role) ? '' : 'none';
    });
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  //  API PUBLIQUE
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /**
   * Protège la page courante via cookie de session.
   * @param {string[]} allowedRoles - ex: ['admin'] | [] = tous
   */
  async function requireAuth(allowedRoles = []) {
    try {
      const authenticated = await Auth.isAuthenticated();

      if (!authenticated) {
        _redirect('session_expired');
        return;
      }

      const user = Auth.getUser();
      if (allowedRoles.length > 0 && !allowedRoles.includes(user?.role)) {
        _redirect('unauthorized');
        return;
      }

      // Tout OK
      _injectUserInfo(user);
      _showPage();

    } catch (_) {
      // Erreur réseau → rediriger
      _redirect('session_expired');
    }
  }

  /**
   * Déconnexion propre.
   * @param {boolean} skipConfirm
   */
  async function handleLogout(skipConfirm = false) {
    if (!skipConfirm && !confirm('Voulez-vous vous déconnecter ?')) return;
    await Auth.logout();
  }

  window.requireAuth  = requireAuth;
  window.handleLogout = handleLogout;

})();