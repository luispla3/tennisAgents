// Authentication utilities
// This file handles authentication state management using localStorage

const AUTH_TOKEN_KEY = 'tennisAgents_auth_token';
const AUTH_USER_KEY = 'tennisAgents_user';
const REDIRECT_KEY = 'tennisAgents_redirect';

/**
 * Check if user is authenticated
 * @returns {boolean}
 */
function isAuthenticated() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    return !!token;
}

/**
 * Get authentication token
 * @returns {string|null}
 */
function getAuthToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
}

/**
 * Get current user data
 * @returns {Object|null}
 */
function getCurrentUser() {
    const userStr = localStorage.getItem(AUTH_USER_KEY);
    if (userStr) {
        try {
            return JSON.parse(userStr);
        } catch (e) {
            return null;
        }
    }
    return null;
}

/**
 * Set authentication token and user data
 * @param {string} token - Authentication token
 * @param {Object} user - User data
 */
function setAuth(token, user) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

/**
 * Clear authentication data
 */
function clearAuth() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
}

/**
 * Save redirect URL for after login
 * @param {string} url - URL to redirect to after login
 */
function saveRedirect(url) {
    localStorage.setItem(REDIRECT_KEY, url);
}

/**
 * Get and clear redirect URL
 * @returns {string|null}
 */
function getRedirect() {
    const redirect = localStorage.getItem(REDIRECT_KEY);
    if (redirect) {
        localStorage.removeItem(REDIRECT_KEY);
        return redirect;
    }
    return null;
}

/**
 * Check authentication and redirect to login if not authenticated
 * This should be called on pages that require authentication (except index)
 * @param {string} currentPath - Current page path
 */
function requireAuth(currentPath) {
    // Allow access to index, login, and register pages
    const publicPaths = ['/', '/login', '/register'];
    
    if (publicPaths.includes(currentPath)) {
        return true;
    }

    if (!isAuthenticated()) {
        // Save current path for redirect after login
        saveRedirect(currentPath);
        // Redirect to login
        window.location.href = '/login';
        return false;
    }

    return true;
}

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        isAuthenticated,
        getAuthToken,
        getCurrentUser,
        setAuth,
        clearAuth,
        saveRedirect,
        getRedirect,
        requireAuth
    };
}
