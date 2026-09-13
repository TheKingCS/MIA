// MIA Mobile — Phase 1: login, subscribe to Web Push, send a test push.
// Not a dashboard yet — proving the pipeline is this page's only job.

const $ = (id) => document.getElementById(id);
let sessionToken = null;

function setStatus(text) {
    $("status").textContent = text;
}

function urlBase64ToUint8Array(base64) {
    const padding = "=".repeat((4 - (base64.length % 4)) % 4);
    const raw = atob((base64 + padding).replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

async function login() {
    const profileId = $("profile_id").value.trim();
    const password = $("password").value;
    const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: profileId, password }),
    });
    if (!res.ok) {
        setStatus("Login failed — check the profile ID and password.");
        return;
    }
    const data = await res.json();
    sessionToken = data.token;
    setStatus(`Logged in as ${data.name}.`);
    $("push-section").hidden = false;
}

async function enableNotifications() {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        setStatus("This browser doesn't support push notifications.");
        return;
    }
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
        setStatus("Notification permission was not granted.");
        return;
    }

    const registration = await navigator.serviceWorker.register("/service-worker.js");
    const keyRes = await fetch("/api/vapid-public-key");
    const { public_key } = await keyRes.json();

    const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key),
    });
    const subJson = subscription.toJSON();

    await fetch("/api/push/subscribe", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${sessionToken}`,
        },
        body: JSON.stringify({ endpoint: subJson.endpoint, keys: subJson.keys }),
    });
    setStatus("Subscribed to push notifications.");
}

async function sendTestPush() {
    const res = await fetch("/api/push/test", {
        method: "POST",
        headers: { Authorization: `Bearer ${sessionToken}` },
    });
    if (!res.ok) {
        setStatus("Couldn't send a test push — subscribe first.");
        return;
    }
    const data = await res.json();
    setStatus(`Sent ${data.sent} of ${data.attempted} test push(es).`);
}

$("login-button").addEventListener("click", login);
$("enable-button").addEventListener("click", enableNotifications);
$("test-button").addEventListener("click", sendTestPush);
