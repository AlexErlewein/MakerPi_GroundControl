/* ── Sidebar toggle ───────────────────────────────────────────────────────── */
const menuBtn = document.getElementById('docs-menu-btn');
const sidebar = document.getElementById('docs-sidebar');

if (menuBtn && sidebar) {
    menuBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
    document.addEventListener('click', (e) => {
        if (window.innerWidth > 900) return;
        if (!sidebar.classList.contains('open')) return;
        if (sidebar.contains(e.target) || menuBtn.contains(e.target)) return;
        sidebar.classList.remove('open');
    });
}

/* ── highlight.js ─────────────────────────────────────────────────────────── */
/* Mermaid blocks are already converted to .mermaid divs server-side, so we   */
/* only need to exclude any leftover language-mermaid classes to be safe.     */
if (typeof hljs !== 'undefined') {
    document.querySelectorAll('pre code:not(.language-mermaid)').forEach((el) => {
        hljs.highlightElement(el);
    });
}

/* ── Mermaid ──────────────────────────────────────────────────────────────── */
/* .mermaid divs are injected server-side; we only need to init + run.        */
if (typeof mermaid !== 'undefined') {
    mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        themeVariables: {
            background: '#161b22',
            primaryColor: '#1f6feb',
            primaryTextColor: '#f0f6fc',
            primaryBorderColor: '#30363d',
            lineColor: '#58a6ff',
            secondaryColor: '#21262d',
            tertiaryColor: '#0d1117',
            edgeLabelBackground: '#161b22',
            clusterBkg: '#21262d',
            titleColor: '#f0f6fc',
            attributeBackgroundColorEven: '#21262d',
            attributeBackgroundColorOdd: '#161b22',
        },
    });
    mermaid.run({ querySelector: '.mermaid' });
}

/* ── TOC scrollspy ────────────────────────────────────────────────────────── */
(function () {
    const tocLinks = document.querySelectorAll('.docs-toc-card .toc a');
    if (!tocLinks.length) return;

    const headings = Array.from(
        document.querySelectorAll('.docs-content h2, .docs-content h3')
    );

    const onScroll = () => {
        const scrollY = window.scrollY + 90;
        let active = null;
        for (const h of headings) {
            if (h.offsetTop <= scrollY) active = h.id;
        }
        tocLinks.forEach((a) => {
            const href = a.getAttribute('href');
            a.classList.toggle('active', href === '#' + active);
        });
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
})();

/* ── Search ───────────────────────────────────────────────────────────────── */
(function () {
    const input = document.getElementById('docs-search-input');
    const resultsBox = document.getElementById('docs-search-results');
    const nav = document.getElementById('docs-nav');
    if (!input || !resultsBox) return;

    let debounce = null;

    const showResults = (items) => {
        resultsBox.innerHTML = '';
        if (!items.length) {
            resultsBox.innerHTML = '<div class="docs-search-empty">No results found</div>';
        } else {
            items.forEach((item) => {
                const a = document.createElement('a');
                a.href = `/page/${item.slug}`;
                a.className = 'docs-search-result-item';
                a.innerHTML = `<div class="docs-search-result-title">${escHtml(item.title)}</div>
                               <div class="docs-search-result-excerpt">${escHtml(item.excerpt)}</div>`;
                resultsBox.appendChild(a);
            });
        }
        resultsBox.hidden = false;
        if (nav) nav.hidden = true;
    };

    const hideResults = () => {
        resultsBox.hidden = true;
        if (nav) nav.hidden = false;
    };

    input.addEventListener('input', () => {
        clearTimeout(debounce);
        const q = input.value.trim();
        if (!q) { hideResults(); return; }
        debounce = setTimeout(async () => {
            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
                const data = await res.json();
                showResults(data.results || []);
            } catch (_) {
                showResults([]);
            }
        }, 180);
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') { input.value = ''; hideResults(); input.blur(); }
    });

    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !resultsBox.contains(e.target)) hideResults();
    });

    /* Press / or Cmd+K to focus search */
    document.addEventListener('keydown', (e) => {
        if ((e.key === '/' || (e.key === 'k' && (e.metaKey || e.ctrlKey))) &&
            document.activeElement !== input) {
            e.preventDefault();
            input.focus();
        }
    });

    function escHtml(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
})();
