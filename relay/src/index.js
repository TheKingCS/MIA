/*
 * The sealed relay (DEC-0062, docs/GLASSES_RELAY_PLAN.md). Two sockets in a
 * room, each message passed to the other. Everything in them is encrypted
 * by the phone and the glasses, so this can't read it; it stores nothing and
 * logs nothing.
 */

const ROOM = /^([a-f0-9]{64}|pair-[0-9]{6})$/;
const ROLES = new Set(["page", "phone"]);
const PAGE_ORIGIN = "https://thekingcs.github.io";
const MAX_BYTES = 256 * 1024;
const MAX_PER_MINUTE = 240;
const FULL = 1008;
const TOO_BIG = 1009;

export default {
  async fetch(request, env) {
    const { pathname, searchParams } = new URL(request.url);
    const room = pathname.slice(1);
    const role = searchParams.get("role");
    if (!ROOM.test(room) || !ROLES.has(role)) return new Response("Not found", { status: 404 });
    if (request.headers.get("Upgrade") !== "websocket") return new Response("Expected a socket", { status: 426 });

    // A browser always sends its Origin; the phone app sends none.
    const origin = request.headers.get("Origin");
    if (origin ? origin !== PAGE_ORIGIN || role !== "page" : role !== "phone") {
      return new Response("Forbidden", { status: 403 });
    }
    return env.ROOMS.get(env.ROOMS.idFromName(room)).fetch(request);
  },
};

export class Room {
  constructor(state) {
    this.state = state;
  }

  async fetch(request) {
    const role = new URL(request.url).searchParams.get("role");
    for (const old of this.state.getWebSockets(role)) old.close(FULL, "replaced");
    const [client, server] = Object.values(new WebSocketPair());
    this.state.acceptWebSocket(server, [role]);
    server.serializeAttachment({ role, minute: 0, count: 0 });
    return new Response(null, { status: 101, webSocket: client });
  }

  webSocketMessage(socket, message) {
    const size = typeof message === "string" ? message.length : message.byteLength;
    if (size > MAX_BYTES) return socket.close(TOO_BIG, "too big");

    const seen = socket.deserializeAttachment();
    const minute = Math.floor(Date.now() / 60000);
    seen.count = seen.minute === minute ? seen.count + 1 : 1;
    seen.minute = minute;
    socket.serializeAttachment(seen);
    if (seen.count > MAX_PER_MINUTE) return socket.close(FULL, "too many");

    const other = seen.role === "page" ? "phone" : "page";
    for (const peer of this.state.getWebSockets(other)) peer.send(message);
  }

  webSocketClose(socket, code) {
    try { socket.close(code === 1005 ? 1000 : code); } catch { /* already closed */ }
  }

  webSocketError(socket) {
    try { socket.close(1011); } catch { /* already closed */ }
  }
}
