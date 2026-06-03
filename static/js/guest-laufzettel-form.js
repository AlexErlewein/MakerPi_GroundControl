// Guest Laufzettel Form JavaScript

let guestId = null;
let previousUnpaid = null;
let isNewMode = false;  // true when coming from login page (?new=1)

// Check if URL has ?new=1 parameter (coming from login page)
function checkNewMode() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('new') === '1';
}

// Initialize form with current date/time
function initForm() {
    const now = new Date();
    const dateStr = now.toISOString().slice(0, 10);
    const localIso = now.getFullYear() + '-' +
        String(now.getMonth() + 1).padStart(2, '0') + '-' +
        String(now.getDate()).padStart(2, '0') + 'T' +
        String(now.getHours()).padStart(2, '0') + ':' +
        String(now.getMinutes()).padStart(2, '0');
    
    document.getElementById('guest-date').value = dateStr;
    document.getElementById('guest-start').value = localIso;
}

// Check for existing guest session
async function checkGuestSession() {
    try {
        // Try to get guest_id from session via a cookie check
        // We'll need to call an endpoint that checks the session
        const response = await fetch('/api/guest/session-check');
        if (response.ok) {
            const data = await response.json();
            if (data.guest_id) {
                guestId = data.guest_id;
                // Check for unpaid Laufzettel from today
                await checkTodayUnpaid();
                // Check for unpaid Laufzettel from previous days
                await checkPreviousUnpaid();
            }
        }
    } catch (e) {
        console.log('No existing guest session');
    }
}

// Check for unpaid Laufzettel from today
async function checkTodayUnpaid() {
    if (!guestId) return;
    
    try {
        const response = await fetch(`/api/guest/laufzettel/${guestId}`);
        if (response.ok) {
            const lz = await response.json();
            // Redirect to detail page
            window.location.href = `/guest/laufzettel/${lz.id}`;
        }
    } catch (e) {
        // No unpaid Laufzettel for today, that's fine
        console.log('No unpaid Laufzettel for today');
    }
}

// Check for unpaid Laufzettel from previous days
async function checkPreviousUnpaid() {
    if (!guestId) return;
    
    try {
        const response = await fetch(`/api/guest/laufzettel/${guestId}/previous`);
        if (response.ok) {
            const data = await response.json();
            if (data.has_previous_unpaid) {
                previousUnpaid = data.laufzettel;
                showReminderModal(data.laufzettel);
            }
        }
    } catch (e) {
        console.log('Error checking previous unpaid');
    }
}

// Show reminder modal for previous unpaid Laufzettel
function showReminderModal(lz) {
    const modal = document.getElementById('reminder-modal');
    const text = document.getElementById('reminder-text');
    
    text.innerHTML = `Du hast noch einen unbezahlten Laufzettel vom <strong>${lz.date}</strong> (Nr. ${lz.id}).<br><br>
        Bitte sprich einen Admin an, um diesen zu bezahlen, oder erstelle einen neuen Laufzettel für heute.`;
    
    modal.classList.remove('hidden');
}

// Hide reminder modal
function hideReminderModal() {
    document.getElementById('reminder-modal').classList.add('hidden');
}

// Show Thank You message after successful creation (new mode from login page)
function showThankYou(laufzettelId) {
    const container = document.querySelector('.guest-container');
    const name = document.getElementById('guest-name').value.trim();
    
    container.innerHTML = `
        <div class="guest-header">
            <h1>✅ Vielen Dank, ${esc(name)}!</h1>
            <p>Dein Laufzettel wurde erfolgreich erstellt.</p>
        </div>
        <div class="info-message" style="text-align: center; margin: 2rem 0;">
            <p><strong>Laufzettel Nr. ${laufzettelId}</strong></p>
            <p style="margin-top: 1rem;">Bitte wende dich an einen Admin, um Material zu erfassen und zu bezahlen.</p>
        </div>
        <div style="text-align: center; margin-top: 2rem;">
            <a href="/" class="btn btn-success">Zurück zur Startseite</a>
        </div>
    `;
}

// Escape HTML
function esc(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

// Submit form to create new guest Laufzettel
async function submitForm(e) {
    e.preventDefault();
    
    const submitBtn = document.getElementById('submit-btn');
    const errorContainer = document.getElementById('error-container');
    
    submitBtn.disabled = true;
    errorContainer.classList.add('hidden');
    
    const name = document.getElementById('guest-name').value.trim();
    const street = document.getElementById('guest-street').value.trim();
    const zip = document.getElementById('guest-zip').value.trim();
    const city = document.getElementById('guest-city').value.trim();
    const address = [street, `${zip} ${city}`.trim()].filter(Boolean).join('\n');
    const email = document.getElementById('guest-email').value.trim();
    const date = document.getElementById('guest-date').value;
    const start = document.getElementById('guest-start').value;
    
    const body = {
        name: name,
        address: address,
        email: email || null,
        date: date,
        start: new Date(start).toISOString()
    };
    
    try {
        const response = await fetch('/api/guest/laufzettel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        
        if (response.ok) {
            const lz = await response.json();
            if (isNewMode) {
                // New mode: show Thank You message
                showThankYou(lz.id);
            } else {
                // QR/Direct URL mode: redirect to detail page (cached behavior)
                window.location.href = `/guest/laufzettel/${lz.id}`;
            }
        } else {
            const error = await response.json();
            errorContainer.textContent = error.detail || 'Fehler beim Erstellen des Laufzettels';
            errorContainer.classList.remove('hidden');
        }
    } catch (e) {
        errorContainer.textContent = 'Netzwerkfehler. Bitte versuche es erneut.';
        errorContainer.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
    }
}

// Event listeners
document.getElementById('guest-form').addEventListener('submit', submitForm);

document.getElementById('reminder-close').addEventListener('click', hideReminderModal);
document.getElementById('reminder-modal').querySelector('.modal-overlay').addEventListener('click', hideReminderModal);

document.getElementById('reminder-new').addEventListener('click', () => {
    hideReminderModal();
    // User wants to create a new Laufzettel, continue with form
});

document.getElementById('reminder-continue').addEventListener('click', () => {
    if (previousUnpaid) {
        window.location.href = `/guest/laufzettel/${previousUnpaid.id}`;
    }
});

// Initialize
isNewMode = checkNewMode();
initForm();
if (!isNewMode) {
    // Only check for existing session in QR/direct URL mode
    checkGuestSession();
}
