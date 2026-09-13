// MIA Mobile — Phase 1 service worker.
//
// Only job right now: turn an incoming Web Push message into a visible
// notification. No offline caching yet — that's real, separate scope
// once there's an actual dashboard worth caching.

self.addEventListener("push", (event) => {
    let data = { title: "MIA", message: "" };
    if (event.data) {
        try {
            data = event.data.json();
        } catch (err) {
            data = { title: "MIA", message: event.data.text() };
        }
    }
    event.waitUntil(
        self.registration.showNotification(data.title || "MIA", {
            body: data.message || "",
        })
    );
});

self.addEventListener("install", () => {
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(self.clients.claim());
});
