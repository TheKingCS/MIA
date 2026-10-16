/*
 * calendar.js — the Calendar screen (claude, 2026-10-16).
 * Renders MIA.calendar(month) (core/calendar_view.py): Past Due, Due Today,
 * Due Soon (the next two weeks, by day) and a month grid. Each item says
 * what it is and offers its own action (Done, Mark Paid...); your own
 * events can be removed; Add Event proposes event.add. Formatting only.
 */
(function () {
  "use strict";
  const { el, act, form } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const TABS = [["past_due", "Past Due"], ["today", "Due Today"], ["soon", "Due Soon"], ["month", "Month"]];
  let page = null, month = "", picked = null;
  let tab = TABS.some(([t]) => t === location.hash.slice(1)) ? location.hash.slice(1) : "today";

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const longDay = (iso) => new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });

  function row(item, showDate) {
    const icon = (window.MIAIcons && MIAIcons.svg(item.app)) || null;
    const sub = [showDate ? longDay(item.date) : null, item.time || null, item.detail || null].filter(Boolean).join(" · ");
    const actions = [];
    if (item.action) actions.push(btn(item.action.label, "btn-green", () => act({ kind: item.action.kind, params: item.action.params })));
    if (item.event_id) actions.push(btn("Remove", "btn-ghost", () => act({ kind: "event.delete", params: { event_id: item.event_id } })));
    return el("div", { class: "row cal-row" + (item.due && item.date < page.as_of ? " overdue" : "") },
      el("span", { class: "cal-ico", "aria-hidden": "true" }, icon),
      el("div", { class: "cal-main" },
        el("div", { class: "row-title" }, item.title),
        sub ? el("div", { class: "row-sub" }, sub) : null),
      el("span", { class: "chip cal-kind" }, item.kind_label),
      actions.length ? el("div", { class: "row-buttons" }, actions) : null);
  }
  const list = (items, showDate, empty) => items.length
    ? el("div", { class: "rows" }, items.map((i) => row(i, showDate))) : el("p", { class: "empty" }, empty);

  async function addEvent(day) {
    const v = await form("Add Event", page.forms.event.fields, day ? { date: day } : {});
    if (v) act({ kind: "event.add", params: v });
  }

  function monthView() {
    const m = page.month;
    const grid = el("div", { class: "cal-grid", role: "grid", "aria-label": m.label },
      m.weekdays.map((w) => el("div", { class: "cal-wd" }, w)),
      m.days.map((d) => el("button", {
        type: "button", class: "cal-day" + (d.in_month ? "" : " out") + (d.today ? " today" : "") +
          (picked === d.date ? " picked" : "") + (d.late ? " late" : ""),
        "aria-label": longDay(d.date) + (d.count ? ", " + d.count + " things" : ""),
        onclick: () => { picked = d.date; draw(); },
      }, el("span", { class: "n" }, String(d.day)),
        el("span", { class: "dots" }, (d.kinds || []).slice(0, 4).map((k) => el("i", { class: "dot k-" + k }))))));
    const day = picked && m.by_date[picked] ? m.by_date[picked] : picked ? [] : null;
    return [section(m.label, el("div", { class: "row-buttons" },
        btn("‹ Previous", "btn-ghost", () => go(m.prev)), btn("Next ›", "btn-ghost", () => go(m.next))), grid),
      picked ? section(longDay(picked), btn("Add Event", "btn-amber", () => addEvent(picked)),
        list(day || [], false, "Nothing on this day.")) : null];
  }

  async function go(m) { month = m; picked = null; page = await MIA.calendar(month); draw(); }

  function draw() {
    const soonCount = page.soon.reduce((n, d) => n + d.items.length, 0);
    $("strip").replaceChildren(
      el("div", { class: "cell " + (page.past_due.length ? "bad" : "ok") }, el("span", { class: "n" }, page.past_due.length), el("span", { class: "t" }, "Past Due")),
      el("div", { class: "cell soon" }, el("span", { class: "n" }, page.today.length), el("span", { class: "t" }, "Today")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, soonCount), el("span", { class: "t" }, "Next 2 Weeks")));
    $("tabs").hidden = false;
    $("tabs").replaceChildren(...TABS.map(([id, l]) =>
      el("button", { type: "button", role: "tab", "aria-selected": String(id === tab),
        onclick: () => { tab = id; history.replaceState(null, "", "#" + id); draw(); } }, l)));
    const add = btn("Add Event", "btn-amber", () => addEvent(null));
    let body;
    if (tab === "past_due") body = [section("Past Due", add, list(page.past_due, true, "Nothing past due. You're caught up."))];
    else if (tab === "today") body = [section("Due Today · " + longDay(page.as_of), add, list(page.today, false, "Nothing on today."))];
    else if (tab === "soon") body = page.soon.length
      ? page.soon.map((d, i) => section(d.label, i === 0 ? add : null, list(d.items, false, "")))
      : [section("Due Soon", add, el("p", { class: "empty" }, "Nothing in the next two weeks."))];
    else body = monthView();
    $("panel").replaceChildren(...body.filter(Boolean));
  }

  MIAShell.start(async () => {
    page = await MIA.calendar(month);
    draw();
  });
})();
