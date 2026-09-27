// MIA phone app: log in, then hold a spoken conversation with the full
// MIA running on the computer at home (through Tailscale), plus push
// notifications. Audio capture/encoding lives in voice.js.

const $ = (id) => document.getElementById(id);
const TOKEN_KEY = "mia.sessionToken";
const GOODBYE = /\b(goodbye|bye mia|good bye|stop listening|that'?s all|end conversation)\b/i;

let sessionToken = null;
try { sessionToken = localStorage.getItem(TOKEN_KEY); } catch (err) { sessionToken = null; }

let mic = null;
let player = null;
let wakeLock = null;
let inConversation = false;
let endAfterReply = false;
let busy = false;

// ---------------------------------------------------------------- UI helpers

function setStatus(text, isError = false) {
    $("status").textContent = text || "";
    $("status").className = isError ? "error" : "";
}

const ORB_LABELS = {
    idle: "Tap to talk", listening: "Listening…", recording: "Hearing you", thinking: "Thinking…", speaking: "Speaking",
};

function setOrb(state, line) {
    $("orb").className = state;
    $("orb").textContent = ORB_LABELS[state] || "";
    $("state-line").textContent = line || "";
}

function addBubble(who, text) {
    if (!text) return;
    const div = document.createElement("div");
    div.className = `bubble ${who}`;
    div.textContent = text;
    $("log").prepend(div);
}

function showLoggedIn(loggedIn) {
    $("login-section").hidden = loggedIn;
    $("talk-section").hidden = !loggedIn;
}

// ---------------------------------------------------------------- API

async function api(path, options = {}) {
    const headers = Object.assign({}, options.headers || {}, { Authorization: `Bearer ${sessionToken}` });
    const res = await fetch(path, Object.assign({}, options, { headers }));
    if (res.status === 401) {
        logout("Your session expired (MIA may have restarted). Please log in again.");
        throw new Error("unauthorized");
    }
    if (!res.ok) {
        let detail = `${res.status}`;
        try { detail = (await res.json()).detail || detail; } catch (err) { /* keep status */ }
        throw new Error(detail);
    }
    return res.json();
}

async function login() {
    const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: $("profile_id").value.trim(), password: $("password").value }),
    });
    if (!res.ok) {
        let detail = "Login failed. Check your name and password.";
        try { detail = (await res.json()).detail || detail; } catch (err) { /* keep default */ }
        setStatus(detail, true);
        return;
    }
    const data = await res.json();
    sessionToken = data.token;
    try { localStorage.setItem(TOKEN_KEY, sessionToken); } catch (err) { /* private mode: session-only */ }
    $("password").value = "";
    showLoggedIn(true);
    setStatus(`Logged in as ${data.name}.`);
    checkVoiceStatus();
}

function logout(message) {
    endConversation();
    sessionToken = null;
    try { localStorage.removeItem(TOKEN_KEY); } catch (err) { /* ignore */ }
    showLoggedIn(false);
    setStatus(message || "Logged out.");
}

async function checkVoiceStatus() {
    try {
        const s = await api("/api/voice/status");
        const missing = [];
        if (!s.speech_to_text) missing.push("speech recognition");
        if (!s.text_to_speech) missing.push("MIA's voice");
        if (!s.assistant) missing.push("the assistant model");
        if (missing.length) setStatus(`Not available on MIA's computer right now: ${missing.join(", ")}.`, true);
    } catch (err) { /* status is best-effort */ }
}

// ---------------------------------------------------------------- playback

// One reused <audio> element, "unlocked" by the first tap, so phones
// allow it to play MIA's replies later without another tap.
const SILENT_WAV = "data:audio/wav;base64,UklGRkQDAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YSADAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="; // 50 ms of silence

function unlockPlayer() {
    if (!player) player = new Audio();
    player.src = SILENT_WAV;
    player.play().catch(() => {});
}

function playReply(base64Wav) {
    return new Promise((resolve) => {
        if (!base64Wav || !player) { resolve(); return; }
        player.onended = () => resolve();
        player.onerror = () => resolve();
        player.src = `data:audio/wav;base64,${base64Wav}`;
        player.play().catch(() => resolve());
    });
}

// ---------------------------------------------------------------- conversation

async function acquireWakeLock() {
    try {
        if ("wakeLock" in navigator) wakeLock = await navigator.wakeLock.request("screen");
    } catch (err) { wakeLock = null; }
}

document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && inConversation) acquireWakeLock();
});

async function startConversation() {
    if (inConversation) return;
    unlockPlayer();
    try {
        if (!mic) {
            mic = new MIAVoice.Microphone({ onUtterance: handleUtterance, onLevelState: onLevelState });
            await mic.start();
        }
    } catch (err) {
        mic = null;
        setStatus("Microphone blocked. Allow mic access for this page (it must be opened over https).", true);
        return;
    }
    inConversation = true;
    endAfterReply = false;
    $("end-button").hidden = false;
    acquireWakeLock();
    setStatus("");
    listen();
}

function listen() {
    setOrb("listening", "Go ahead, I'm listening.");
    mic.listen();
}

function onLevelState(state) {
    if (busy) return;
    if (state === "speech" && $("orb").className !== "recording") setOrb("recording", "Hearing you…");
    if (state === "idle" && $("orb").className === "recording") setOrb("listening", "Go ahead, I'm listening.");
}

function endConversation() {
    inConversation = false;
    if (mic) { mic.stop(); mic = null; }
    if (wakeLock) { wakeLock.release().catch(() => {}); wakeLock = null; }
    $("end-button").hidden = true;
    setOrb("idle", "Ready");
}

async function handleUtterance(wavBytes) {
    busy = true;
    setOrb("thinking", "Thinking…");
    try {
        const reply = await api("/api/voice/turn", {
            method: "POST",
            headers: { "Content-Type": "audio/wav" },
            body: wavBytes,
        });
        if (reply.transcript) addBubble("you", reply.transcript);
        if (GOODBYE.test(reply.transcript || "")) endAfterReply = true;
        await speak(reply);
    } catch (err) {
        if (err.message !== "unauthorized") setStatus(`Couldn't reach MIA: ${err.message}`, true);
    } finally {
        busy = false;
        afterTurn();
    }
}

async function speak(reply) {
    addBubble("mia", reply.reply_text);
    setOrb("speaking", "");
    await playReply(reply.audio_wav_base64);
}

function afterTurn() {
    if (!inConversation) { setOrb("idle", "Ready"); return; }
    if (endAfterReply || !$("handsfree").checked) {
        if (endAfterReply) endConversation();
        else { mic.pause(); setOrb("idle", "Tap to talk again"); }
        return;
    }
    listen();
}

async function sendText() {
    const text = $("text-input").value.trim();
    if (!text || busy) return;
    $("text-input").value = "";
    unlockPlayer();
    busy = true;
    if (mic) mic.pause();
    addBubble("you", text);
    setOrb("thinking", "Thinking…");
    try {
        await speak(await api("/api/voice/text", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
        }));
    } catch (err) {
        if (err.message !== "unauthorized") setStatus(`Couldn't reach MIA: ${err.message}`, true);
    } finally {
        busy = false;
        afterTurn();
    }
}

function onOrbTap() {
    if (busy) return;
    if (!inConversation) { startConversation(); return; }
    // In a conversation but paused (hands-free off): tap to talk again.
    if (mic && mic.paused) listen();
}

async function newTopic() {
    try {
        await api("/api/voice/reset", { method: "POST" });
        $("log").innerHTML = "";
        setStatus("Started a new topic.");
    } catch (err) { /* handled in api() */ }
}

// Headphone play/pause button (best effort; support varies by phone).
if ("mediaSession" in navigator) {
    const toggle = () => (inConversation ? endConversation() : startConversation());
    try {
        navigator.mediaSession.setActionHandler("play", toggle);
        navigator.mediaSession.setActionHandler("pause", toggle);
    } catch (err) { /* unsupported action */ }
}

// ---------------------------------------------------------------- notifications

function urlBase64ToUint8Array(base64) {
    const padding = "=".repeat((4 - (base64.length % 4)) % 4);
    const raw = atob((base64 + padding).replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

async function enableNotifications() {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        setStatus("This browser doesn't support push notifications. On iPhone, add MIA to your Home Screen first.", true);
        return;
    }
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
        setStatus("Notification permission was not granted.", true);
        return;
    }
    const registration = await navigator.serviceWorker.register("/service-worker.js");
    const { public_key } = await (await fetch("/api/vapid-public-key")).json();
    const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key),
    });
    const subJson = subscription.toJSON();
    await api("/api/push/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint: subJson.endpoint, keys: subJson.keys }),
    });
    setStatus("Subscribed to push notifications.");
}

async function sendTestPush() {
    try {
        const data = await api("/api/push/test", { method: "POST" });
        setStatus(`Sent ${data.sent} of ${data.attempted} test push(es).`);
    } catch (err) {
        setStatus("Couldn't send a test push. Enable notifications first.", true);
    }
}

// ---------------------------------------------------------------- wiring

$("login-button").addEventListener("click", login);
$("password").addEventListener("keydown", (e) => { if (e.key === "Enter") login(); });
$("orb").addEventListener("click", onOrbTap);
$("end-button").addEventListener("click", endConversation);
$("new-button").addEventListener("click", newTopic);
$("text-send").addEventListener("click", sendText);
$("text-input").addEventListener("keydown", (e) => { if (e.key === "Enter") sendText(); });
$("enable-button").addEventListener("click", enableNotifications);
$("test-button").addEventListener("click", sendTestPush);
$("logout-button").addEventListener("click", () => logout());

if (sessionToken) {
    showLoggedIn(true);
    checkVoiceStatus();
}
if (!window.isSecureContext) {
    setStatus("Open MIA through its https:// Tailscale address. Phones only allow the microphone on secure pages.", true);
}
