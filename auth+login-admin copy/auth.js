/**
 * SmartCert — auth.js (VERSION COOKIE)
 * Compatible avec app.py — sessions HttpOnly Cookie
 *
 * DIFFÉRENCE AVEC L'ANCIENNE VERSION :
 *   ✗ Avant : JWT Bearer token dans sessionStorage
 *   ✓ Maintenant : HttpOnly Cookie géré automatiquement par le navigateur
 *
 * Utilisation :
 *   Auth.isAuthenticated()        → Promise<boolean>
 *   Auth.getUser()                → { email, role } depuis sessionStorage
 *   Auth.logout()                 → supprime session serveur + cookie
 *   Auth.apiFetch(url, options)   → fetch avec credentials: 'include'
 */

const Auth = (() => {

  const API_BASE = localStorage.getItem('smartcert_api') || 'http://127.0.0.1:5000';
  const USER_KEY = 'smartcert_user';

  // ─── PRIVATE ──────────────────────────────────────────
  function _saveUser(user) {
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function _clearUser() {
    sessionStorage.removeItem(USER_KEY);
  }

  // ─── PUBLIC ───────────────────────────────────────────
  return {

    /**
     * Vérifie si l'utilisateur est connecté via le cookie.
     * Interroge /auth/me à chaque appel.
     * @returns {Promise<boolean>}
     */
    async isAuthenticated() {
      try {
        const res  = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' });
        const data = await res.json();
        if (data.authenticated && data.user) {
          _saveUser(data.user);
          return true;
        }
        _clearUser();
        return false;
      } catch (_) {
        // Serveur injoignable — refuser l'accès
        return false;
      }
    },

    /**
     * Retourne les infos utilisateur depuis sessionStorage.
     * (Données mises à jour lors du dernier isAuthenticated())
     * @returns {{ id, email, role } | null}
     */
    getUser() {
      const raw = sessionStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    },

    /**
     * Retourne le rôle de l'utilisateur.
     * @returns {'admin' | 'etudiant' | null}
     */
    getRole() {
      return this.getUser()?.role ?? null;
    },

    /**
     * Déconnecte l'utilisateur côté serveur et supprime le cookie.
     * Redirige vers login.html.
     */
    async logout() {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method:      'POST',
          credentials: 'include',
        });
      } catch (_) { /* réseau KO — continuer */ }
      _clearUser();
      window.location.href = '../auth+login-admin/login.html?reason=logged_out';
    },

    /**
     * Effectue un fetch() avec credentials: 'include'.
     * Gère automatiquement le 401 → redirection login.
     * @param {string} url  - chemin relatif ex: '/certificates'
     * @param {RequestInit} options
     */
    async apiFetch(url, options = {}) {
      const res = await fetch(`${API_BASE}${url}`, {
        ...options,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {}),
        },
      });

      if (res.status === 401) {
        _clearUser();
        window.location.href = '../auth+login-admin/login.html?reason=session_expired';
        throw new Error('Session expirée');
      }
      if (res.status === 403) {
        window.location.href = '../auth+login-admin/login.html?reason=unauthorized';
        throw new Error('Accès refusé');
      }
      return res;
    },

  };

})();

window.Auth = Auth;