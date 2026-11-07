/*
 * classroom.js — the Classroom (claude, 2026-11-06).
 * Renders MIA.classroom() (core/classroom_manager.py): the course to continue
 * (the design canvas's card, DEC-0113), then each subject, its courses and
 * their lessons, how far along each is. Adding, ticking a lesson
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

  // The canvas (DEC-0113): the course to continue (core/classroom_manager.continue_course) with its progress and
  // the next lessons to tick, then the subjects as rows; a subject opens into its courses and lessons.
  let open = null;
  function continueCard(c) {
    return el("section", { class: "glass surface-focus cl-continue", "aria-labelledby": "cl-continue" },
      el("span", { class: "cl-label" }, c.subject + " · Continue"),
      el("h2", { id: "cl-continue" }, c.course),
      el("div", { class: "cl-progress" }, el("div", { class: "meter" }, el("div", { class: "meter-fill", style: "width:" + Math.round(100 * c.done / c.total) + "%" })),
        el("span", { class: "cl-count" }, c.done + " / " + c.total)),
      el("div", { class: "cl-lessons" }, c.lessons.map((l) => el("button", { type: "button", class: "cl-lesson" + (l.done ? " done" : ""),
        "aria-pressed": String(l.done), onclick: () => MIAShell.act({ kind: "lesson.done", params: { lesson_id: l.id, done: l.done ? "no" : "yes" } }, { quick: true }) },
        el("span", { class: "cl-check", "aria-hidden": "true" }, l.done ? "✓" : ""), el("span", { class: "cl-name" }, l.name),
        el("span", { class: "cl-xp" }, l.done ? "Done" : l.xp ? "+" + l.xp + " XP" : "")))));
  }
  function subjectRow(sub) {
    const isOpen = open === sub.id;
    const head = el("button", { type: "button", class: "glass cl-subject" + (isOpen ? " open" : ""), "aria-expanded": String(isOpen),
      onclick: () => { open = isOpen ? null : sub.id; paint(last); } },
      el("span", {}, sub.name), el("span", { class: "cl-n" }, sub.courses.length + " course" + (sub.courses.length === 1 ? "" : "s") +
        (sub.total ? " · " + sub.done + "/" + sub.total : "")));
    if (!isOpen) return head;
    return el("div", { class: "cl-subject-open" }, head,
      ...sub.courses.map(course),
      el("div", { class: "row-buttons" },
        button("Add a course", () => add("course", { subject_id: sub.id }, "A course in " + sub.name), "btn-amber"),
        button("Take the subject out", () => MIAShell.act({ kind: "subject.delete", params: { subject_id: sub.id } }))));
  }
  let last = null;
  function paint(data) {
    last = data;
    $("class-sub").textContent = data.subjects.length ? "What you're learning." : "Nothing here yet.";
    $("panel").replaceChildren(
      data.continue ? continueCard(data.continue) : null,
      el("h2", { class: "cl-label cl-subjects-label" }, "Subjects"),
      data.subjects.length ? el("div", { class: "cl-subjects" }, data.subjects.map(subjectRow))
        : el("p", { class: "empty" }, "Your own study: subjects, the courses in each and their lessons. Tick a lesson when it's done."),
      el("div", { class: "row-buttons" }, button("Add a subject", () => add("subject", {}, "A new subject"))));
  }

  MIAShell.start(async () => { paint(await MIA.classroom()); }, { refreshOnChange: true });
})();
