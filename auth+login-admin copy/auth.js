/**
 * SmartCert — auth.js
 * Module d'authentification frontend
 *
 * Responsabilités :
 *   • Login / Logout via Flask API
 *   • Stockage sécurisé du JWT dans sessionStorage
 *   • Gestion de l'expiration de session
 *   • Validation du token côté serveur
 *
 * Utilisation :
 *   <script src="auth.js"></script>
 *   Auth.login(email, pw).then(...)
 *   Auth.isAuthenticated()  →  boolean
 *   Auth.getUser()          →  { email, role, name }
 *   Auth.authHeaders()      →  { Authorization: 'Bearer ...' }
 */

const Auth = (() => {

  // ─── CONFIG ──────────────────────────────────────────────
  // Fix P10: read API URL from localStorage so it matches the configurable setting
  const API_BASE    = localStorage.getItem('smartcert_api') || 'http://127.0.0.1:5000';
  const TOKEN_KEY   = 'smartcert_token';
  const USER_KEY    = 'smartcert_user';
  const EXPIRY_KEY  = 'smartcert_expiry';

  // Durée de vie minimum restante avant de forcer le renouvellement (5 min)
  const MIN_TTL_MS  = 5 * 60 * 1000;

  // ─── PRIVATE HELPERS ─────────────────────────────────────
  function _store(token, user, expiresIn) {
    const expiry = Date.now() + (expiresIn * 1000) - MIN_TTL_MS;
    sessionStorage.setItem(TOKEN_KEY,  token);
    sessionStorage.setItem(USER_KEY,   JSON.stringify(user));
    sessionStorage.setItem(EXPIRY_KEY, expiry.toString());
  }

  function _clear() {
    [TOKEN_KEY, USER_KEY, EXPIRY_KEY].forEach(k => sessionStorage.removeItem(k));
  }

  function _isExpired() {
    const expiry = parseInt(sessionStorage.getItem(EXPIRY_KEY) || '0');
    return Date.now() > expiry;
  }

  // ─── PUBLIC API ──────────────────────────────────────────
  return {

    /**
     * Authentifie l'utilisateur.
     * @param {string} email
     * @param {string} password
     * @returns {Promise<{token, user, expires_in}>}
     * @throws {Error} si les identifiants sont incorrects ou réseau KO
     */
    async login(email, password) {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email, password }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Erreur de connexion');

      _store(data.token, data.user, data.expires_in);
      return data;
    },

    /**
     * Déconnecte l'utilisateur (appel API + nettoyage local).
     * Redirige vers login.html.
     */
    async logout() {
      const token = this.getToken();
      if (token) {
        try {
          await fetch(`${API_BASE}/auth/logout`, {
            method:  'POST',
            headers: { 'Authorization': `Bearer ${token}` },
          });
        } catch (_) { /* réseau KO — on continue quand même */ }
      }
      _clear();
      window.location.href = 'login.html';
    },

    /**
     * Retourne le JWT stocké, ou null si absent / expiré.
     */
    getToken() {
      if (_isExpired()) { _clear(); return null; }
      return sessionStorage.getItem(TOKEN_KEY);
    },

    /**
     * Retourne l'objet user { email, role, name } ou null.
     */
    getUser() {
      const raw = sessionStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    },

    /**
     * Retourne le rôle ('admin' | 'etudiant') ou null.
     */
    getRole() {
      return this.getUser()?.role ?? null;
    },

    /**
     * true si un token valide est présent en local.
     */
    isAuthenticated() {
      return !!this.getToken();
    },

    /**
     * Valide le token auprès du serveur.
     * Fallback : accepte le token local si le serveur est injoignable.
     * @returns {Promise<boolean>}
     */
    async verifyWithServer() {
      const token = this.getToken();
      if (!token) return false;

      try {
        const res = await fetch(`${API_BASE}/auth/verify-token`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (res.status === 401) { _clear(); return false; }
        return res.ok;
      } catch (_) {
        // Réseau injoignable : on accepte le token local (mode offline)
        console.warn('SmartCert Auth: serveur injoignable, validation locale uniquement');
        return this.isAuthenticated();
      }
    },

    /**
     * Retourne les headers HTTP avec Bearer token pour fetch().
     * @param {object} extra - headers supplémentaires
     * @returns {object}
     */
    authHeaders(extra = {}) {
      return {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${this.getToken()}`,
        ...extra,
      };
    },

    /**
     * Effectue un fetch() authentifié.
     * Gère automatiquement le 401 (redirige vers login).
     * @param {string} url
     * @param {RequestInit} options
     */
    async apiFetch(url, options = {}) {
      const headers = { ...this.authHeaders(), ...(options.headers || {}) };
      const res = await fetch(`${API_BASE}${url}`, { ...options, headers });

      if (res.status === 401) {
        _clear();
        window.location.href = `login.html?reason=session_expired&return=${encodeURIComponent(window.location.pathname)}`;
        throw new Error('Session expirée');
      }
      return res;
    },

  };
})();

// Expose globalement
window.Auth = Auth;
