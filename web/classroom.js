/*
 * classroom.js — the Classroom (claude, 2026-11-06).
 * Renders MIA.classroom() (core/classroom_manager.py): the course to continue
 * (the design canvas's card, DEC-0113), then each subject, its courses and
 * their lessons, how far along each is. Adding, ticking a lesson
 * done (its skill XP credited once) and taking things out go through actions
 * (subject.*, course.*, lesson.*, a lesson's notes through lesson.notes), so undo takes them back. Formatting only;
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

  // A lesson's notes (what you learned), edited whole and saved through lesson.notes; by voice, "add to my notes for…".
  async function notes(l) {
    const values = await MIAShell.form("Notes · " + l.name, [{ name: "notes", label: "What you learned", type: "textarea" }], { notes: l.notes || "" });
    if (values) MIAShell.act({ kind: "lesson.notes", params: { lesson_id: l.id, notes: values.notes || "" } }, { quick: true });
  }

  // The skill a lesson trains and its XP (lesson.skill; credited once, when it's first done).
  async function trains(l) {
    const v = await MIAShell.form("What " + l.name + " Trains", [
      { name: "skill_id", label: "Skill", type: "pick", options: ["skills"] },
      { name: "xp", label: "XP when it's done (1 to 100)", type: "int", default: 10 }],
      { skill_id: l.skill ? l.skill.id : "", xp: l.skill ? l.skill.xp : 10 }, { skills: last.skills });
    if (v) MIAShell.act({ kind: "lesson.skill", params: { lesson_id: l.id, skill_id: v.skill_id || "", xp: v.xp || 10 } });
  }

  function lesson(l) {
    return el("div", { class: "sync-row council-msg" },
      el("div", {}, el("p", { class: "council-text" }, (l.done ? "✓ " : "") + l.name),
        l.done ? el("p", { class: "dim" }, "Done " + l.done_at) : null,
        l.skill ? el("p", { class: "dim" }, "Trains " + l.skill.name + " · " + l.skill.xp + " XP") : null,
        l.notes ? el("p", { class: "cl-notes" }, l.notes) : null),
      el("div", { class: "row-buttons" },
        button(l.notes ? "Notes" : "Add notes", () => notes(l)),
        last && last.skills.length ? button("Skill", () => trains(l)) : null,
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
      el("div", { class: "row-buttons" }, button("Add a subject", () => add("subject", {}, "A new subject"))),
      textbooks(data.textbooks));
  }

  // Textbooks (core/web_textbooks.py): your books with their chapters, a search inside them, Make A Course (one lesson
  // per chapter) and Remove, as textbook.course / textbook.remove; Add A Book uploads a PDF or text file. By voice:
  // "what does my welding book say about porosity?", "let's study" a book.
  let found = null;
  function textbooks(t) {
    if (!t || !t.available) return null;
    const pick = el("input", { type: "file", accept: ".pdf,.txt,.md", hidden: true, onchange: async () => {
      const file = pick.files[0];
      if (!file) return;
      try { MIAShell.say("Reading " + file.name + "…"); await MIA.upload("/api/classroom/textbook", file); paint(await MIA.classroom()); }
      catch (e) { MIAShell.say(e.message); }
    } });
    const ask = el("input", { type: "search", class: "money-find", placeholder: "Look something up in your books…",
      "aria-label": "Search your textbooks", value: found ? found.query : "" });
    const results = el("div", { class: "tb-hits" }, found ? (found.hits.length ? found.hits.map((h) => el("article", { class: "tb-hit" },
      el("span", { class: "pw-label" }, h.book + " · page " + h.page + (h.chapter ? " · " + h.chapter : "")),
      el("p", {}, h.text))) : [el("p", { class: "dim" }, "Nothing in your books about that.")]) : []);
    const book = (b) => el("div", { class: "sync-row council-msg" },
      el("div", {}, el("p", { class: "council-text" }, b.title),
        el("p", { class: "dim" }, b.reading ? "Still reading the scan…" : b.error ? "Couldn't read it: " + b.error
          : [b.pages + " pages", b.chapters.length + (b.chapters.length === 1 ? " chapter" : " chapters"), b.course ? "course: " + b.course : null].filter(Boolean).join(" · ")),
        b.chapters.length > 1 ? el("details", {}, el("summary", {}, "Chapters"),
          el("ol", {}, b.chapters.map((c) => el("li", {}, c.title + " · p. " + c.page)))) : null),
      el("div", { class: "row-buttons" },
        !b.course && !b.reading ? button("Make a course", () => MIAShell.act({ kind: "textbook.course", params: { book_id: b.id } }), "btn-amber") : null,
        button("Remove", () => MIAShell.act({ kind: "textbook.remove", params: { book_id: b.id } }))));
    return el("section", { class: "glass money-section cl-books" },
      el("h2", { class: "cl-label" }, "Textbooks"),
      t.books.length ? [el("form", { class: "tb-search", onsubmit: async (ev) => {
        ev.preventDefault();
        found = ask.value.trim() ? await MIA.textbookSearch(ask.value.trim()) : null;
        paint(last);
      } }, ask, el("button", { type: "submit", class: "btn btn-ghost btn-small" }, "Look Up")), results,
        el("div", { class: "sync-rows" }, t.books.map(book))]
        : el("p", { class: "dim" }, "Add a textbook (a PDF or a text file) and MIA reads it: ask what it says, study it chapter by chapter, or make it a course."),
      el("div", { class: "row-buttons" }, button("Add a book", () => pick.click()), pick));
  }

  MIAShell.start(async () => { paint(await MIA.classroom()); }, { refreshOnChange: true });
})();
