/*
 * taught-skills.js — Taught Skills (claude, 2026-11-15, DEC-0123).
 *
 * Renders MIA.taughtSkills() (core/web_taught_skills.py):
 * - Waiting On You: the run in progress, with what it's asking (a question
 *   to answer, a task of yours to mark done, or a yes/no before a step).
 * - Watching: what she's noted so far while you show her, with Keep It and
 *   Never Mind.
 * - Your Skills: each skill's steps in plain words (a step that asks first
 *   is marked; one that asks every time, learned or not, says so), its
 *   practice state, and Run, Change Steps, Forget.
 *
 * Teaching and changing are actions (core/taught_skill_actions.py). A run
 * goes through /api/taught-skills/run, /answer and /stop, where every step
 * passes its own gate. This file only formats.
 */
(function () {
  "use strict";
  const { el, act, form, say } = MIAShell;
  const $ = (id) => document.getElementById(id);
  let page = null;
  let heard = [];  // what she said during the run on this screen, newest last

  const btn = (label, cls, onclick) => el("button", { type: "button", class: "btn " + cls, onclick }, label);
  const buttons = (...list) => el("div", { class: "row-buttons" }, list.filter(Boolean));
  const section = (title, actions, ...body) =>
    el("section", { class: "glass money-section" }, el("div", { class: "sect" }, el("h2", {}, title), actions), ...body);
  const chip = (text, cls) => el("span", { class: "chip " + (cls || "") }, text);
  const field = (name, label, type, def, required) => ({ name, label, type, required: !!required, options: [], default: def ?? null });

  // One move of a run (start, answer, stop): keep what she said, then re-read the screen.
  async function move(step) {
    try {
      const got = await step();
      if (got.said) heard = heard.concat(got.said).slice(-12);
      if (got.status === "done" || got.status === "stopped") say(got.said && got.said.length ? got.said[got.said.length - 1] : "Stopped.");
    } catch (e) { say(e.message); }
    MIAShell.refresh();
  }
  const run = (s) => { heard = []; move(() => MIA.taughtSkillRun(s.skill_id)); };
  const answer = (text) => move(() => MIA.taughtSkillAnswer(text));

  async function teach() {
    const v = await form("Teach A Skill", [field("name", "What to call it", "text", null, true),
      field("steps", page.help, "textarea", null, true), field("about", "What it's for (optional)", "text")], {});
    if (v) act({ kind: "taught_skill.add", params: v });
  }
  async function watch() {
    const v = await form("Watch Me", [field("name", "What to call it", "text", null, true)], {});
    if (v) act({ kind: "taught_skill.watch", params: v });
  }
  async function change(s) {
    const v = await form("Change " + s.name, [field("steps", page.help, "textarea", s.steps_text, true)], { steps: s.steps_text });
    if (v) act({ kind: "taught_skill.steps", params: { skill_id: s.skill_id, steps: v.steps } });
  }

  function waiting() {
    const r = page.run;
    if (!r) return heard.length ? section("Last Run", null, el("ul", {}, heard.map((line) => el("li", {}, line)))) : null;
    const w = r.waiting || { kind: "", text: "" };
    let reply;
    if (w.kind === "ask") {
      const input = el("input", { type: "text", class: "input", "aria-label": w.text, placeholder: "Your answer" });
      const send = () => { if (input.value.trim()) answer(input.value.trim()); };
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
      reply = el("div", { class: "row-buttons" }, input, btn("Answer", "btn-green", send));
    } else if (w.kind === "you") {
      reply = buttons(btn("Done", "btn-green", () => answer("done")));
    } else {
      reply = buttons(btn("Yes, Do It", "btn-green", () => answer("yes")), btn("No", "btn-ghost", () => answer("no")));
    }
    return section("Waiting On You", buttons(btn("Stop", "btn-ghost", () => move(() => MIA.taughtSkillStop()))),
      el("p", { class: "dim" }, r.name + " · step " + r.step + " of " + r.of),
      heard.length ? el("ul", {}, heard.map((line) => el("li", {}, line))) : null,
      el("p", { class: "progress-sentence" }, w.text), reply);
  }

  function watching() {
    const w = page.watching;
    if (!w) return null;
    return section("Watching: " + w.name, buttons(
      w.steps.length ? btn("Keep It", "btn-green", () => act({ kind: "taught_skill.keep", params: {} })) : null,
      btn("Never Mind", "btn-ghost", () => act({ kind: "taught_skill.cancel", params: {} }))),
      w.steps.length ? el("ol", {}, w.steps.map((s) => el("li", {}, s)))
        : el("p", { class: "empty" }, "Do it with her now: ask her for each thing, or do it on its screen. Each one shows up here."));
  }

  function skill(s) {
    const learned = s.state === "learned";
    return el("article", { class: "glass money-section" },
      el("div", { class: "row-title" }, s.name,
        chip(learned ? "learned" : "practising · " + s.clean_runs + " of " + page.needed + " clean runs", learned ? "ok" : "")),
      s.about ? el("p", {}, s.about) : null,
      el("ol", {}, s.steps.map((st) => el("li", {}, st.text,
        st.always_asks ? chip("asks every time") : st.asks ? chip("asks while practising") : null))),
      el("p", { class: "dim" }, [s.runs ? "Run " + s.runs + "×" : "Not run yet", s.last_result ? "last: " + s.last_result : "", s.source].filter(Boolean).join(" · ")),
      buttons(btn(learned ? "Run" : "Practise", "btn-green", () => run(s)), btn("Change Steps", "btn-ghost", () => change(s)),
        btn("Forget", "btn-ghost", () => act({ kind: "taught_skill.delete", params: { skill_id: s.skill_id } }))));
  }

  function draw() {
    const learned = page.skills.filter((s) => s.state === "learned").length;
    $("strip").replaceChildren(
      el("div", { class: "cell ok" }, el("span", { class: "n" }, String(page.skills.length)), el("span", { class: "t" }, "Skills")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, String(learned)), el("span", { class: "t" }, "Learned")),
      el("div", { class: "cell ok" }, el("span", { class: "n" }, String(page.skills.length - learned)), el("span", { class: "t" }, "Practising")),
      el("div", { class: "cell " + (page.run ? "soon" : "ok") }, el("span", { class: "n" }, page.run ? "1" : "0"), el("span", { class: "t" }, "Waiting On You")));
    $("panel").replaceChildren(...[
      waiting(), watching(),
      section("Your Skills", buttons(page.watching ? null : btn("Watch Me", "btn-green", watch), btn("Teach In Steps", "btn-ghost", teach)),
        el("p", { class: "dim" }, "A skill is made of things MIA can already do. She practises it with you until " + page.needed +
          " clean runs; anything that pays, buys, sends, publishes or deletes asks every time."),
        page.skills.length ? null : el("p", { class: "empty" }, "Nothing taught yet. Press Watch Me, name it, then do it with her once.")),
      ...page.skills.map(skill)].filter(Boolean));
  }

  MIAShell.start(async () => {
    page = await MIA.taughtSkills();
    if (!page.available) { $("panel").replaceChildren(el("p", { class: "empty" }, "Taught skills aren't on this MIA.")); return; }
    draw();
  });
})();
