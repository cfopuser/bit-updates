import { currentLang, i18n, setLang } from './i18n.js';
import { fetchAppData, appConfigs } from './api.js';
import { renderGrid, closeModal, loader, appGrid, emptyState } from './ui.js';

let isDark = localStorage.getItem('theme') === 'dark' ||
    (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);

function updateTheme() {
    const html = document.documentElement;
    const icon = document.getElementById('themeIcon');
    if (isDark) {
        html.classList.add('dark');
        icon.className = 'fa-solid fa-sun text-base sm:text-lg transition-transform';
    } else {
        html.classList.remove('dark');
        icon.className = 'fa-solid fa-moon text-base sm:text-lg transition-transform';
    }
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

function toggleTheme() {
    isDark = !isDark;
    updateTheme();
}

function updateLangUI() {
    document.documentElement.dir = currentLang === 'he' ? 'rtl' : 'ltr';
    document.documentElement.lang = currentLang;

    document.querySelectorAll('[data-key]').forEach(el => {
        const key = el.getAttribute('data-key');
        if (i18n[currentLang][key]) el.textContent = i18n[currentLang][key];
    });

    document.getElementById('langLabel').textContent = i18n[currentLang].langLabel;
    if (Object.keys(appConfigs).length > 0) renderGrid();
}

function toggleLang() {
    setLang(currentLang === 'en' ? 'he' : 'en');
    updateLangUI();
}

async function init() {
    updateTheme();
    updateLangUI();

    const success = await fetchAppData();

    loader.classList.add('hidden');
    if (success && Object.keys(appConfigs).length > 0) {
        renderGrid();
        appGrid.classList.remove('hidden');
    } else {
        emptyState.classList.remove('hidden');
    }
}

// Ensure the DOM is fully loaded before attaching listeners
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    document.getElementById('langToggle').addEventListener('click', toggleLang);
    document.getElementById('modalClose').addEventListener('click', closeModal);
    document.getElementById('modalBackdrop').addEventListener('click', closeModal);
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

    init();
});
