// Theme Toggle - Dark/Light Mode
(function () {
    const STORAGE_KEY = 'gc-theme';
    const DEFAULT = 'dark';

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme === 'light' ? 'light' : '');
        const btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.textContent = theme === 'light' ? '🌙' : '☀️';
            btn.title = theme === 'light' ? 'Dark Mode' : 'Light Mode';
        }
    }

    function getTheme() {
        return localStorage.getItem(STORAGE_KEY) || DEFAULT;
    }

    function toggleTheme() {
        const current = getTheme();
        const next = current === 'dark' ? 'light' : 'dark';
        localStorage.setItem(STORAGE_KEY, next);
        applyTheme(next);
    }

    // Apply immediately on load (also called inline in <head> for flash prevention)
    applyTheme(getTheme());

    document.addEventListener('DOMContentLoaded', function () {
        applyTheme(getTheme());
        const btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.addEventListener('click', toggleTheme);
        }
    });
})();
