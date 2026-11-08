/*
 * health.js — Health (DEC-0129, claude, 2026-11-08).
 * Renders MIA.health() (core/health_actions.health_page): what's coming up, the week's sleep (tap a night's hours
 * to log it), medications and supplements (Taken, reminders at their times, refills), visits, and records. Every
 * change is an action, so undo takes it back; the same is said by voice ("I slept 7 hours", "I took my vitamin D").
 * MIA keeps what you tell her as you tell it; she doesn't suggest doses or read results.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls + " btn-small", onclick }, label);
  const card = (title, actions, ...kids) => el("section", { class: "glass money-section" },
    el("div", { class: "sect" }, el("h2", {}, title), actions), ...kids);
  const day = (iso) => {
    if (!iso) return "";
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric",
      year: d.getFullYear() === new Date().getFullYear() ? undefined : "numeric" });  // the year when it isn't this one
  };
  let page = null;

  async function add(kind, actionKind, title, values) {
    const v = await form(title, page.forms[kind], values || {});
    if (v) act({ kind: actionKind, params: v });
  }

  function due() {
    if (!page.due.length) return null;
    return el("section", { class: "glass money-section health-due", "aria-label": "Coming up" },
      el("h2", { class: "pw-label" }, "Coming Up"),
      el("div", { class: "rows" }, page.due.map((d) => el("div", { class: "row money-row" },
        el("div", {}, el("div", { class: "row-title" }, d.title), el("div", { class: "row-sub" }, day(d.when))),
        el("span", { class: "chip chip-soon" }, d.days < 0 ? "Past due" : d.days === 0 ? "Today" : "In " + d.days + "d")))));
  }

  function sleep() {
    const s = page.sleep;
    const max = 10;
    return card("Sleep", btn("Log a night", "btn-amber", () => add("sleep", "sleep.log", "Log a night's sleep")),
      el("p", { class: "dim" }, s.average != null ? "Averaging " + s.average + " hours over the nights logged this week." : "No nights logged this week. Tap a night to log it."),
      el("div", { class: "sleep-week", role: "list" }, s.nights.map((n) => el("button", { type: "button", class: "sleep-night", role: "listitem",
        "aria-label": day(n.night) + (n.hours != null ? ": " + n.hours + " hours" + (n.rested ? ", rested " + n.rested + " of 5" : "") : ": not logged, log it"),
        onclick: () => add("sleep", "sleep.log", "The night of " + day(n.night), { night: n.night, hours: n.hours ?? "", rested: n.rested ?? "" }) },
        el("span", { class: "sleep-bar" + (n.hours == null ? " empty" : "") , style: "height:" + (n.hours != null ? Math.max(6, Math.min(100, 100 * n.hours / max)) : 6) + "%" }),
        el("span", { class: "sleep-h" }, n.hours != null ? n.hours + "h" : "—"),
        el("span", { class: "sleep-d" }, new Date(n.night + "T00:00:00").toLocaleDateString(undefined, { weekday: "narrow" }))))));
  }

  function meds() {
    const row = (m) => el("div", { class: "row money-row" + (m.active ? "" : " muted") },
      el("div", {}, el("div", { class: "row-title" }, m.name + (m.dose ? " · " + m.dose : "")),
        el("div", { class: "row-sub" }, [m.kind, m.times.length ? (m.reminders ? "reminders " : "") + m.times.join(", ") : null,
          m.active ? m.taken_today + " taken today" : "stopped",
          m.refills != null ? m.refills + " refill" + (m.refills === 1 ? "" : "s") + " left" : null,
          m.refill_on ? "refill " + day(m.refill_on) : null].filter(Boolean).join(" · "))),
      el("div", { class: "row-buttons" },
        m.active ? btn("Taken", "btn-amber", () => act({ kind: "med.take", params: { med_id: m.id } }, { quick: true })) : null,
        btn("Edit", "btn-ghost", async () => {
          const v = await form("Edit " + m.name, page.forms.med.filter((f) => f.name !== "kind"), { ...m, times: m.times.join(", ") });
          if (v) act({ kind: "med.edit", params: { med_id: m.id, ...v } });
        }),
        btn(m.active ? "Stop" : "Restart", "btn-ghost", () => act({ kind: "med.edit", params: { med_id: m.id, active: m.active ? "no" : "yes" } })),
        btn("Delete", "btn-ghost danger", () => act({ kind: "med.delete", params: { med_id: m.id } }))));
    return card("Medications and Supplements", btn("Add", "btn-amber", () => add("med", "med.add", "Add a medication or supplement")),
      page.meds.length ? el("div", { class: "rows" }, page.meds.map(row))
        : el("p", { class: "dim" }, "Add what you take, as written on the label. Each time you give it gets a daily reminder that only says “Medication time”."));
  }

  function visits() {
    const row = (v) => el("div", { class: "row money-row" },
      el("div", {}, el("div", { class: "row-title" }, v.kind + (v.who ? " · " + v.who : "") + (v.upcoming ? " (booked)" : "")),
        el("div", { class: "row-sub" }, [day(v.when), v.what_for, v.next_due ? "next due " + day(v.next_due) : null].filter(Boolean).join(" · ")),
        v.notes ? el("p", { class: "dim" }, v.notes) : null),
      el("div", { class: "row-buttons" },
        btn("Edit", "btn-ghost", async () => { const x = await form("Edit visit", page.forms.visit, v); if (x) act({ kind: "visit.edit", params: { visit_id: v.id, ...x } }); }),
        btn("Delete", "btn-ghost danger", () => act({ kind: "visit.delete", params: { visit_id: v.id } }))));
    return card("Doctor and Dentist", btn("Add a visit", "btn-amber", () => add("visit", "visit.add", "A visit", { kind: "Doctor" })),
      page.visits.length ? el("div", { class: "rows" }, page.visits.map(row)) : el("p", { class: "dim" }, "Visits you've had or booked, and when the next one is due."));
  }

  function records() {
    const row = (r) => el("div", { class: "row money-row" },
      el("div", {}, el("div", { class: "row-title" }, r.name + (r.value ? ": " + r.value : "")),
        el("div", { class: "row-sub" }, [r.kind, r.when ? day(r.when) : null].filter(Boolean).join(" · ")),
        r.notes ? el("p", { class: "dim" }, r.notes) : null),
      btn("Delete", "btn-ghost danger", () => act({ kind: "record.delete", params: { record_id: r.id } })));
    return card("Records", btn("Add a record", "btn-amber", () => add("record", "record.add", "A health record", { kind: "Test result" })),
      page.records.length ? el("div", { class: "rows" }, page.records.map(row))
        : el("p", { class: "dim" }, "Test results, vaccinations, allergies and documents, kept as you give them."));
  }

  MIAShell.start(async () => {
    page = await MIA.health();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "Health isn't set up on this MIA.")); return; }
    $("panel").replaceChildren(...[due(), sleep(), meds(), visits(), records(),
      el("p", { class: "dim health-note" }, "Kept in your own folder, encrypted on the PC, never on a shared screen.")].filter(Boolean));
  });
})();
