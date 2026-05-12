// Activity Tracker - Keeps member session alive with heartbeat requests

const HEARTBEAT_INTERVAL = 60000; // 60 seconds
let heartbeatTimer = null;
let lastActivityTime = Date.now();

function updateActivity() {
    lastActivityTime = Date.now();
}

function sendHeartbeat() {
    fetch('/api/auth/heartbeat', {
        method: 'POST',
        credentials: 'include'
    })
    .then(res => {
        if (res.status === 401) {
            // Session expired, redirect to login
            window.location.href = '/';
        }
    })
    .catch(err => {
        console.error('Heartbeat failed:', err);
    });
}

function startHeartbeat() {
    if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
    }
    heartbeatTimer = setInterval(() => {
        // Only send heartbeat if there was activity in the last interval
        if (Date.now() - lastActivityTime < HEARTBEAT_INTERVAL) {
            sendHeartbeat();
        }
    }, HEARTBEAT_INTERVAL);
}

// Track user activity
const activityEvents = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
activityEvents.forEach(event => {
    document.addEventListener(event, updateActivity);
});

// Start heartbeat when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startHeartbeat);
} else {
    startHeartbeat();
}
