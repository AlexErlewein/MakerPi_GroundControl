const menuBtn = document.getElementById('docs-menu-btn');
const sidebar = document.querySelector('.docs-sidebar');

if (menuBtn && sidebar) {
    menuBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });

    document.addEventListener('click', (event) => {
        const isMobile = window.innerWidth <= 900;
        if (!isMobile) return;
        if (!sidebar.classList.contains('open')) return;
        if (sidebar.contains(event.target) || menuBtn.contains(event.target)) return;
        sidebar.classList.remove('open');
    });
}
