// ─── MakerPi GroundControl PWA Utilities ────────────────────────

(function () {
    'use strict';

    // ─── Service Worker Registration ─────────────────────────────
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js', { scope: '/' })
                .then((reg) => {
                    console.log('[PWA] Service Worker registered:', reg.scope);

                    // Check for updates periodically (every 30 min)
                    setInterval(() => reg.update(), 30 * 60 * 1000);

                    // Handle updates
                    reg.addEventListener('updatefound', () => {
                        const newWorker = reg.installing;
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'activated') {
                                showUpdateToast();
                            }
                        });
                    });
                })
                .catch((err) => {
                    console.error('[PWA] Service Worker registration failed:', err);
                });
        });
    }

    // ─── Connectivity Indicator ──────────────────────────────────
    const indicator = document.createElement('div');
    indicator.id = 'gc-connectivity';
    indicator.setAttribute('aria-live', 'polite');
    Object.assign(indicator.style, {
        position: 'fixed',
        bottom: '0',
        left: '0',
        right: '0',
        padding: '8px 16px',
        textAlign: 'center',
        fontSize: '0.85rem',
        fontWeight: '500',
        zIndex: '9999',
        transform: 'translateY(100%)',
        transition: 'transform 0.3s ease',
        fontFamily: 'inherit',
    });

    function showOffline() {
        indicator.textContent = '📡 Offline — Änderungen werden synchronisiert wenn wieder verbunden';
        indicator.style.background = 'var(--danger, #f85149)';
        indicator.style.color = '#fff';
        indicator.style.transform = 'translateY(0)';
        document.body.classList.add('gc-offline');
    }

    function showOnline() {
        indicator.textContent = '✓ Verbindung wiederhergestellt';
        indicator.style.background = 'var(--success, #3fb950)';
        indicator.style.color = '#fff';
        indicator.style.transform = 'translateY(0)';
        document.body.classList.remove('gc-offline');

        setTimeout(() => {
            indicator.style.transform = 'translateY(100%)';
        }, 3000);
    }

    document.body.appendChild(indicator);

    window.addEventListener('offline', showOffline);
    window.addEventListener('online', showOnline);

    if (!navigator.onLine) {
        showOffline();
    }

    // ─── Update Toast ────────────────────────────────────────────
    function showUpdateToast() {
        const toast = document.createElement('div');
        toast.setAttribute('role', 'alert');
        Object.assign(toast.style, {
            position: 'fixed',
            top: '16px',
            right: '16px',
            background: 'var(--bg-secondary, #161b22)',
            border: '1px solid var(--border-color, #30363d)',
            borderRadius: '8px',
            padding: '12px 16px',
            fontSize: '0.9rem',
            color: 'var(--text-primary, #e6edf3)',
            zIndex: '10000',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            fontFamily: 'inherit',
        });

        toast.innerHTML = `
            <span>🔄 App aktualisiert</span>
            <button style="background:var(--accent);color:#fff;border:none;border-radius:4px;padding:6px 12px;cursor:pointer;font-size:0.85rem;">
                Neu laden
            </button>
        `;

        toast.querySelector('button').addEventListener('click', () => {
            window.location.reload();
        });

        document.body.appendChild(toast);

        // Auto-dismiss after 10s
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 10000);
    }

    // ─── Offline-aware Fetch Wrapper ─────────────────────────────
    window.gcFetch = async function (url, options = {}) {
        try {
            const response = await fetch(url, options);

            if (!navigator.onLine) {
                // If we got a response while "offline", we're back
                window.dispatchEvent(new Event('online'));
            }

            return response;
        } catch (err) {
            if (!navigator.onLine && options.method && options.method !== 'GET') {
                // Queue mutation for background sync
                console.log('[PWA] Queuing mutation for sync:', options.method, url);
            }
            throw err;
        }
    };

    // ─── Push Notification Subscription ──────────────────────────
    window.gcPushSubscribe = async function () {
        if (!('PushManager' in window)) {
            console.log('[PWA] Push notifications not supported');
            return null;
        }

        try {
            const reg = await navigator.serviceWorker.ready;

            // Check if already subscribed
            let subscription = await reg.pushManager.getSubscription();
            if (subscription) return subscription;

            // Fetch VAPID public key from server
            const res = await fetch('/api/push/vapid-key');
            if (!res.ok) return null;

            const { publicKey } = await res.json();

            subscription = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(publicKey),
            });

            // Send subscription to server
            await fetch('/api/push/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subscription.toJSON()),
            });

            return subscription;
        } catch (err) {
            console.error('[PWA] Push subscription failed:', err);
            return null;
        }
    };

    // ─── Install Prompt ──────────────────────────────────────────
    let deferredPrompt = null;

    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;

        // Show install button if it exists
        const installBtn = document.getElementById('gc-install-btn');
        if (installBtn) {
            installBtn.style.display = 'inline-flex';
            installBtn.addEventListener('click', async () => {
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                console.log('[PWA] Install prompt outcome:', outcome);
                deferredPrompt = null;
                installBtn.style.display = 'none';
            });
        }
    });

    window.addEventListener('appinstalled', () => {
        console.log('[PWA] App installed');
        deferredPrompt = null;
        const installBtn = document.getElementById('gc-install-btn');
        if (installBtn) installBtn.style.display = 'none';
    });

    // ─── Helpers ─────────────────────────────────────────────────
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
})();
