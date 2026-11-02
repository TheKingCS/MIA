// The relay's refusals and passing, against a running copy:
//   node test.mjs http://127.0.0.1:8787
import http from "node:http";
import https from "node:https";

const base = process.argv[2];
const socketBase = base.replace(/^http/, "ws");
const room = "a".repeat(64);
const pageOrigin = { Origin: "https://thekingcs.github.io" };
let failed = 0;

function check(name, ok) {
  console.log((ok ? "ok    " : "FAILED") + " " + name);
  if (!ok) failed++;
}

function status(path, headers = {}) {
  return new Promise((resolve) => {
    const lib = base.startsWith("https") ? https : http;
    const request = lib.request(base + path, {
      headers: { Connection: "Upgrade", Upgrade: "websocket", "Sec-WebSocket-Version": "13",
        "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==", ...headers },
    });
    request.on("response", (response) => { response.resume(); resolve(response.statusCode); });
    request.on("upgrade", (response, socket) => { socket.destroy(); resolve(101); });
    request.on("error", () => resolve(0));
    request.end();
  });
}

function open(path, headers) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(socketBase + path, headers ? { headers } : undefined);
    socket.got = [];
    socket.closedWith = null;
    socket.addEventListener("message", (event) => socket.got.push(event.data));
    socket.addEventListener("close", (event) => { socket.closedWith = event.code; });
    socket.addEventListener("open", () => resolve(socket));
    socket.addEventListener("error", () => reject(new Error("no socket: " + path)));
  });
}

const wait = (ms) => new Promise((done) => setTimeout(done, ms));

// Refused at the door
check("a bad room is refused", (await status(`/nope?role=page`, pageOrigin)) === 404);
check("a bad role is refused", (await status(`/${room}?role=admin`, pageOrigin)) === 404);
check("another website is refused", (await status(`/${room}?role=page`, { Origin: "https://evil.example" })) === 403);
check("a browser claiming to be the phone is refused", (await status(`/${room}?role=phone`, pageOrigin)) === 403);
check("no origin claiming to be the page is refused", (await status(`/${room}?role=page`)) === 403);
check("the page's own origin is let in", (await status(`/${room}?role=page`, pageOrigin)) === 101);

// Passing
const page = await open(`/${room}?role=page`, pageOrigin);
const phone = await open(`/${room}?role=phone`);
page.send("from the page");
phone.send("from the phone");
await wait(400);
check("the phone gets the page's message", phone.got.includes("from the page"));
check("the page gets the phone's message", page.got.includes("from the phone"));
check("nobody gets their own back", !page.got.includes("from the page"));

// A second room hears nothing
const elsewhere = await open(`/${"b".repeat(64)}?role=phone`);
page.send("private");
await wait(300);
check("another room hears nothing", elsewhere.got.length === 0);
elsewhere.close();

// A new phone replaces the old one
const newer = await open(`/${room}?role=phone`);
await wait(300);
check("a new phone replaces the old", phone.closedWith === 1008 || phone.readyState !== 1);
newer.close();

// Too big
page.send("x".repeat(256 * 1024 + 1));
await wait(400);
check("an oversized message closes the socket", page.closedWith === 1009 || page.readyState !== 1);

// Flood
const flood = await open(`/${"c".repeat(64)}?role=phone`);
for (let i = 0; i < 260; i++) if (flood.readyState === 1) flood.send("x");
await wait(800);
check("a flood closes the socket", flood.readyState !== 1);

console.log(failed ? `${failed} failed` : "all passed");
process.exit(failed ? 1 : 0);
