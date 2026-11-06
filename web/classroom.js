/*
 * classroom.js — the Classroom (claude, 2026-11-06).
 * Renders MIA.classroom() (core/classroom_manager.py): each subject, its
 * courses and their lessons, how far along each is. Adding, ticking a lesson
 * done (its skill XP credited once) and taking things out go through actions
 * (subject.*, course.*, lesson.*), so undo takes them back. Formatting only;
 * the look is muse's.
 */
(function () {
  "use strict";
  const { el } = MIAShell;
  const $ = (id) => document.getElementById(id);
  const button = (label, onclick, cls) => el("button", { type: "button", class: "btn " + (cls || "btn-ghost") + " btn-small", onclick }, label);

  async function add(kind, params, title) {
    const values = await MIAShell.form(title, [{ name: "name", label: "Name", type: "text", required: true }]);
    if (values) MIAShell.act({ kind: kind + ".add", params: { ...params, name: values.name } });
  }

  function lesson(l) {
    return el("div", { class: "sync-row council-msg" },
      el("div", {}, el("p", { class: "council-text" }, (l.done ? "✓ " : "") + l.name),
        l.done ? el("p", { class: "dim" }, "Done " + l.done_at) : null),
      el("div", { class: "row-buttons" },
        button(l.done ? "Not done" : "Done", () => MIAShell.act({ kind: "lesson.done", params: { lesson_id: l.id, done: l.done ? "no" : "yes" } },
          { quick: true }), l.done ? "btn-ghost" : "btn-amber"),
        button("Take out", () => MIAShell.act({ kind: "lesson.delete", params: { lesson_id: l.id } }))));
  }

  function course(c) {
    return el("div", { class: "glass money-section" },
      el("h3", {}, c.name + " · " + c.done + " of " + c.total),
      el("div", { class: "sync-rows" }, c.lessons.map(lesson)),
      el("div", { class: "row-buttons" },
        button("Add a lesson", () => add("lesson", { course_id: c.id }, "A lesson in " + c.name), "btn-amber"),
        button("Take the course out", () => MIAShell.act({ kind: "course.delete", params: { course_id: c.id } }))));
  }

  function paint(data) {
    $("class-sub").textContent = data.subjects.length ? "What you're learning." : "Nothing here yet.";
    $("panel").replaceChildren(
      el("section", { class: "glass money-section" },
        el("p", {}, "Your own study: subjects, the courses in each and their lessons. Tick a lesson when it's done."),
        el("div", { class: "row-buttons" }, button("Add a subject", () => add("subject", {}, "A new subject"), "btn-amber"))),
      ...data.subjects.map((s) => el("section", { class: "glass money-section" },
        el("h2", {}, s.name), el("p", { class: "dim" }, (s.category ? s.category + " · " : "") + s.done + " of " + s.total + " lessons done"),
        ...s.courses.map(course),
        el("div", { class: "row-buttons" },
          button("Add a course", () => add("course", { subject_id: s.id }, "A course in " + s.name), "btn-amber"),
          button("Take the subject out", () => MIAShell.act({ kind: "subject.delete", params: { subject_id: s.id } }))))));
  }

  MIAShell.start(async () => { paint(await MIA.classroom()); }, { refreshOnChange: true });
})();
