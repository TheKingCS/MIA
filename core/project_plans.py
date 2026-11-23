"""
core.project_plans
====================

Plans made together, then missions (T-0060; Zac, 2026-11-22: "making MIA super capable for teaching homestead and
construction thoroughly step by step offline ... I want to be able to have auto generated missions for plans we
confirm together for different builds or gardens, projects, etc"; his answer: builds and gardens both together).

**A plan here** (`ProjectPlan`) is a draft he and MIA work on until he presses Confirm. Two kinds, both worked out in
code, never by the model:

- **A build**: a plan from the Library's shelf at his size (core/plan_library.py, its quantities from
  core/build_calcs.py) and the Trade Master job that walks it (core/trades.py: phases of steps, each with why, what to
  watch for and a hold point, its stop rules, permit note and PPE). Its stages: get the materials (the shopping list
  against what's on hand), then the job's phases.
- **A garden**: his beds and crops (`match_crop`: by name, a known other name, or the one crop holding all the
  words; never a fragment) and his frost dates (core/garden_plans.py): prepare the beds, start seeds indoors,
  harden off and transplant, sow outside, care, harvest; each step dated from his frosts.

**Changing it** (`change`): its size, beds, crops or frost dates (the stages are worked out again), a stage left out,
a note. **Confirming it** (`confirm`, the action `projectplan.confirm`, his press): one project (core/project_manager.py)
and one mission per stage, each step an objective in order (core/mission_projects.py joins them), the build's
materials on the project's needs list. One action, so one Undo takes it all back. Nothing is made before that press.
**The guide** (core/mission_guide.py's `plan` guide): a mission made from a plan shows its next step with why, what to
watch for and the check, and what her offline library says about the stage (core/offline_library.look_up).

A household store (`project_plans.json`), written through atomic_write_text so "undo that" restores it.
"""

from __future__ import annotations

from core.data_root import DATA_DIR

import json
import uuid
import copy
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "project_plans.json"
KINDS = ("build", "garden")


@dataclass
class ProjectPlan:
    """One plan: its kind, title, status (draft, confirmed, dropped), what it's made from (a build's plan, sizes and
    job; a garden's beds, crops and frost dates), its stages (each {name, steps: [{do, why, watch, check, when}],
    ask}), the stages left out, notes, and once confirmed its project and missions."""
    plan_id: str
    kind: str
    title: str
    status: str = "draft"
    shelf_plan: str = ""
    sizes: dict = field(default_factory=dict)
    job: str = ""
    beds: list = field(default_factory=list)
    crops: list = field(default_factory=list)
    last_frost: str = ""
    first_frost: str = ""
    stages: list = field(default_factory=list)
    left_out: list = field(default_factory=list)
    notes: str = ""
    warnings: list = field(default_factory=list)
    project_id: str = ""
    mission_ids: list = field(default_factory=list)
    made_by: str = "person"  # who started the draft: "person" (a screen) or "mia" (her tool, asked by him)
    created_at: str = ""
    updated_at: str = ""


class ProjectPlanBook:
    """The household's plans made together (see the module docstring)."""

    # DEC-0173: a plan's facts are worked out in code (calculators, Trade Master's jobs, the crop table) from what
    # he gave; who started it and when are on the record.
    EPISTEMIC = {"record": ProjectPlan, "source": "made_by", "at": "created_at", "how": "computed"}

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads the plans from the household's folder (or data/)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_DIR
        self._file = self.data_dir / FILE_NAME
        self.plans: dict[str, ProjectPlan] = {}
        self._load()

    def _load(self) -> None:
        """Reads the plans; a missing or unreadable file is none."""
        try:
            raw = json.loads(open_text(self._file)).get("plans", {})
            self.plans = {k: ProjectPlan(**v) for k, v in raw.items()}
        except (OSError, ValueError, TypeError):
            self.plans = {}

    def _save(self) -> None:
        """Writes the plans atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"plans": {k: asdict(v) for k, v in self.plans.items()}},
                                                 indent=1, ensure_ascii=False))

    def get(self, plan_id: str) -> Optional[ProjectPlan]:
        """One plan by id."""
        return self.plans.get(str(plan_id or ""))

    def listed(self) -> list[ProjectPlan]:
        """Every plan not dropped, newest first."""
        return sorted((p for p in self.plans.values() if p.status != "dropped"),
                      key=lambda p: p.updated_at, reverse=True)

    def put(self, plan: ProjectPlan) -> ProjectPlan:
        """Keeps a plan (stamped now)."""
        now = datetime.now().isoformat(timespec="seconds")
        plan.created_at = plan.created_at or now
        plan.updated_at = now
        self.plans[plan.plan_id] = plan
        self._save()
        return plan

    def for_mission(self, mission_id: str) -> Optional[ProjectPlan]:
        """The confirmed plan a mission was made from, or None."""
        return next((p for p in self.plans.values() if mission_id in p.mission_ids), None)


# ---- working a plan out ------------------------------------------------------------------------------------------

def _job_for(shelf_plan: str, job_id: str = "", context=None):
    """The Trade Master job for a build: the one named, else the one that walks this shelf plan (a kept plan by the
    built-in plan with its calculator); None when there's none."""
    from core import trades

    trades._loaded()
    if job_id:
        job = trades.JOBS.get(job_id)
        if job is None:
            raise ActionError("That isn't one of Trade Master's jobs.")
        return job
    bare = _bare(shelf_plan)
    found = next((j for j in trades.JOBS.values() if bare and j.plan == bare), None)
    library = getattr(context, "plans", None)
    if found is None and library is not None:
        kept = library.get(shelf_plan) or {}
        built = next((p for p in library.built_in() if kept.get("calc") and p.get("calc") == kept["calc"]), None)
        if built is not None:
            found = next((j for j in trades.JOBS.values() if j.plan == _bare(built["id"])), None)
    return found


def _bare(shelf_plan: str) -> str:
    """Pure logic. A shelf plan's id without its shelf ("builtin:raised-bed" is "raised-bed", as jobs name it)."""
    return str(shelf_plan or "").split(":", 1)[-1]


def _shelf_id(context, value: str) -> str:
    """The Library's id for a plan named either way ("raised-bed" or "builtin:raised-bed"); "" for none."""
    value = str(value or "").strip()
    library = getattr(context, "plans", None)
    if not value or library is None:
        return value
    if library.get(value) is not None:
        return value
    return f"builtin:{value}" if library.get(f"builtin:{value}") is not None else value


def _build_stages(context, plan: ProjectPlan) -> tuple[list, list]:
    """A build's stages (materials, then the job's phases; a kept plan walked by its built-in's job) and its
    warnings."""
    from core.plan_library import detail

    stages, warnings = [], []
    if plan.shelf_plan:
        page = detail(context, plan.shelf_plan, plan.sizes or None)
        if page is None:
            raise ActionError("That plan isn't on the Library's shelf.")
        if page.get("problem"):
            raise ActionError(page["problem"])
        plan.title = plan.title or page["title"]
        shop = page.get("shopping") or {}
        buy = [r for r in shop.get("rows", []) if r.get("buy", 0) > 0]
        lines = [f"{r['buy']:g} {r.get('unit') or ''} {r['item']}".replace("  ", " ") for r in buy] or \
                [f"{i['qty']:g} {i.get('unit') or ''} {i['name']}".replace("  ", " ") for i in page.get("items", [])]
        if lines:
            stages.append({"name": "Get the materials", "ask": f"{page['title']} materials", "steps": [
                {"do": f"Get {line}.", "why": "From the plan's material list, worked out for your size, less what's "
                 "already on hand.", "watch": ["buy a little extra for cuts and mistakes where the list says"],
                 "check": "It's on hand.", "when": ""} for line in lines[:40]]})
        warnings += [n for n in page.get("notes", []) if n]
    job = _job_for(plan.shelf_plan, plan.job, context)
    if job is not None:
        from core import trades

        plan.job = job.id
        plan.title = plan.title or job.name
        if job.status != trades.CONFIRMED:
            warnings.append("Trade Master's steps for this job are still a draft: read each one before doing it.")
        if job.permit:
            warnings.append(job.permit)
        for phase in job.phases:
            stages.append({"name": phase.name, "ask": f"{job.name} {phase.name}", "steps": [
                {"do": s.do, "why": s.why, "watch": list(s.watch), "check": s.hold, "when": ""} for s in phase.steps]})
    elif plan.shelf_plan:
        from core.plan_library import detail

        steps = (detail(context, plan.shelf_plan) or {}).get("steps") or []
        if steps:
            warnings.append("No Trade Master walkthrough is written for this build yet: these are the plan's own "
                            "steps, without the reasons and checks a walkthrough gives.")
            stages.append({"name": "Build it", "ask": plan.title, "steps": [
                {"do": s, "why": "", "watch": [], "check": "", "when": ""} for s in steps]})
    if not stages:
        raise ActionError("There's nothing to plan from: name a plan from the Library's shelf or a Trade Master job.")
    return stages, warnings


def _frosts(context, plan: ProjectPlan) -> tuple[date, Optional[date]]:
    """His frost dates for a garden this season (a spring past rolls to next year, February 29 too; a first fall
    frost before it is moved to its year or dropped); ActionError asking for the last spring frost when there's
    none."""
    from core.garden_plans import parse_day

    today = date.today()
    last = parse_day(plan.last_frost, today.year)
    if last is None:
        raise ActionError("When is your last spring frost, on average? (Say it like \"April 20\"; the extension "
                          "office or a frost-date chart for your area has it.)")
    if last < today and (today - last).days > 60:  # this spring is past: next year's garden
        try:
            last = last.replace(year=last.year + 1)
        except ValueError:  # February 29
            last = last + timedelta(days=365)
    first = parse_day(plan.first_frost, last.year)
    if first is not None and first < last:
        try:
            first = first.replace(year=last.year)
        except ValueError:
            first = None
        if first is not None and first < last:
            first = None  # a first fall frost before the last spring one isn't a date to plan by
    return last, first


def _garden_stages(context, plan: ProjectPlan) -> tuple[list, list]:
    """A garden's stages from its beds (named loosely: "bed 1" is Bed 1; one not there is refused), crops and his
    frosts, and its warnings (crops not known, space asked beyond a bed, crops that may not ripen)."""
    from core import garden_plans

    if not plan.beds:
        raise ActionError("Which beds? Give each a name and its size in feet (and its depth for a raised bed).")
    names = {_norm(b["name"]): b["name"] for b in plan.beds}
    known = []
    for c in plan.crops:
        if c.get("crop") not in garden_plans.CROPS:
            continue
        bed = names.get(_norm(c.get("bed") or plan.beds[0]["name"]))
        if bed is None:
            raise ActionError(f"There's no bed called “{c.get('bed')}”: the beds are "
                              + ", ".join(b["name"] for b in plan.beds) + ".")
        known.append({**c, "bed": bed})
    unknown = [str(c.get("crop")) for c in plan.crops if c.get("crop") not in garden_plans.CROPS]
    if not known:
        raise ActionError("Which crops? " + ", ".join(sorted(c.name for c in garden_plans.CROPS.values())) + ".")
    last, first = _frosts(context, plan)
    stages = garden_plans.stages(plan.beds, known, last, first)
    warnings = [garden_plans.NOTE] + ([f"I don't know these crops yet, so they're left out: {', '.join(unknown)}"
                                       " (say summer or winter squash, bush or pole beans)."] if unknown else [])
    for bed in plan.beds:
        asked = sum(float(c.get("sqft") or 0) for c in known if c["bed"] == bed["name"])
        area = bed["length_ft"] * bed["width_ft"]
        if asked > area:
            warnings.append(f"{bed['name']}: {asked:g} square feet asked of its {area:g}.")
    warnings += [s["watch"][-1][len("warning: "):] for st in stages for s in st["steps"]
                 if s["watch"] and str(s["watch"][-1]).startswith("warning: ")]
    plan.title = plan.title or "Garden: " + ", ".join(b["name"] for b in plan.beds)
    return stages, warnings


def work_out(context, plan: ProjectPlan) -> ProjectPlan:
    """Works a plan's stages out again from what it's made from (ActionError saying what's missing, a stage left out
    that isn't there, or every stage left out)."""
    stages, warnings = (_build_stages if plan.kind == "build" else _garden_stages)(context, plan)
    unknown = [s for s in plan.left_out if s not in {st["name"] for st in stages}]
    if unknown:
        raise ActionError(f"There's no stage called “{unknown[0]}”: the stages are "
                          + ", ".join(st["name"] for st in stages) + ".")
    plan.stages = [s for s in stages if s["name"] not in plan.left_out]
    if not plan.stages:
        raise ActionError("Every stage is left out: put one back first.")
    plan.warnings = list(dict.fromkeys(warnings))
    return plan


def _beds(value) -> list:
    """Beds as {name, length_ft, width_ft, depth_in}, from a list of dicts (or one); ActionError for a bad size."""
    beds = value if isinstance(value, list) else [value] if value else []
    out = []
    for n, b in enumerate(beds, start=1):
        try:
            bed = {"name": str(b.get("name") or f"Bed {n}")[:40], "length_ft": float(b.get("length_ft")),
                   "width_ft": float(b.get("width_ft")), "depth_in": float(b.get("depth_in") or 0)}
        except (TypeError, ValueError, AttributeError):
            raise ActionError("Each bed needs its length and width in feet.") from None
        if not (0 < bed["length_ft"] <= 500 and 0 < bed["width_ft"] <= 500 and 0 <= bed["depth_in"] <= 48):
            raise ActionError("That bed's size doesn't look right (feet, and a depth in inches).")
        out.append(bed)
    return out


_ALIASES = {"potatoes": "potato", "potato": "potato", "sweet potatoes": "sweet_potato", "green beans": "bean_bush",
            "beans": "bean_bush", "bush beans": "bean_bush", "pole beans": "bean_pole", "bell peppers": "pepper",
            "peppers": "pepper", "hot peppers": "pepper", "summer squash": "zucchini", "courgettes": "zucchini",
            "butternut squash": "winter_squash", "butternut": "winter_squash", "acorn squash": "winter_squash",
            "corn": "corn", "sweetcorn": "corn", "greens": "", "squash": "", "swiss chard": "chard", "chard": "chard",
            "onion sets": "onion", "scallions": "", "garlic": "", "strawberries": ""}


def _norm(text: str) -> str:
    """Pure logic. A name compared loosely: lower case, spaces and dashes as one space, each word without a plain
    plural ending."""
    words = re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).split()
    return " ".join(w[:-2] if w.endswith("oes") else w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss")
                    else w for w in words)


def match_crop(name: str) -> str:
    """Pure logic. The crop a name means: its id, its name, a known other name, or the one crop whose name holds all
    its words; "" when none or more than one could be meant."""
    from core.garden_plans import CROPS

    said = _norm(name)
    if not said:
        return ""
    aliases = {_norm(k): v for k, v in _ALIASES.items()}
    if said in aliases:
        return aliases[said]
    for crop in CROPS.values():
        if said in (_norm(crop.id), _norm(crop.name)):
            return crop.id
    words = set(said.split())
    hits = [c.id for c in CROPS.values() if words <= set(_norm(c.name).split())]
    return hits[0] if len(hits) == 1 else ""


def _crops(value) -> list:
    """Crops as {crop, bed, sqft}, from names or dicts (`match_crop`; one not known keeps its words, said back);
    ActionError for space below zero."""
    items = value if isinstance(value, list) else [value] if value else []
    out = []
    for item in items:
        item = item if isinstance(item, dict) else {"crop": item}
        said = str(item.get("crop") or "").strip()
        try:
            sqft = float(item.get("sqft") or 0)
        except (TypeError, ValueError):
            raise ActionError("A crop's space is in square feet.") from None
        if sqft < 0:
            raise ActionError("A crop's space can't be below zero.")
        out.append({"crop": match_crop(said) or said.lower(), "bed": str(item.get("bed") or "").strip(), "sqft": sqft})
    return out


def _new(context, params: dict) -> ProjectPlan:
    """A new plan from the params (a build: shelf_plan, sizes, job; a garden: beds, crops, frosts), worked out but not
    kept; ActionError for one that can't be worked out yet (what's missing is said)."""
    kind = str(params.get("kind") or ("garden" if params.get("beds") or params.get("crops") else "build"))
    if kind not in KINDS:
        raise ActionError("A plan is a build or a garden.")
    plan = ProjectPlan(plan_id=uuid.uuid4().hex[:10], kind=kind, title=str(params.get("title") or "")[:80],
                       shelf_plan=_shelf_id(context, params.get("shelf_plan")),
                       sizes=dict(params.get("sizes") or {}),
                       job=str(params.get("job") or ""), beds=_beds(params.get("beds")),
                       crops=_crops(params.get("crops")), notes=str(params.get("notes") or "")[:2000],
                       made_by="mia" if params.get("made_by") == "mia" else "person")
    config = getattr(context, "config", None)
    plan.last_frost = str(params.get("last_frost") or (config.get("garden.last_frost", "") if config else ""))
    plan.first_frost = str(params.get("first_frost") or (config.get("garden.first_frost", "") if config else ""))
    return work_out(context, plan)


def draft(context, params: dict) -> ProjectPlan:
    """A new draft, worked out (`_new`) and kept; his frost dates remembered for the next garden."""
    book = _need(context, "project_plans")
    plan = _new(context, params)
    _remember_frosts(context, plan)
    return book.put(plan)


def _remember_frosts(context, plan: ProjectPlan) -> None:
    """His frost dates, kept for the next garden (device config: the garden is the household's)."""
    config = getattr(context, "config", None)
    if plan.kind != "garden" or config is None:
        return
    for key, value in (("garden.last_frost", plan.last_frost), ("garden.first_frost", plan.first_frost)):
        if value and config.get(key, "") != value:
            config.set(key, value)
            try:
                config.save()
            except Exception:  # noqa: BLE001 - the plan is kept either way
                pass


def _draft_of(context, params: dict) -> ProjectPlan:
    """The draft the params name; ActionError when it isn't one."""
    plan = _need(context, "project_plans").get(params.get("plan_id"))
    if plan is None:
        raise ActionError("That plan isn't here.")
    if plan.status != "draft":
        raise ActionError(f"“{plan.title}” is already {plan.status}.")
    return plan


def change(context, params: dict) -> ProjectPlan:
    """Changes a draft (`_changed`) and keeps it; his frost dates remembered."""
    plan = _changed(context, params)
    _remember_frosts(context, plan)
    return _need(context, "project_plans").put(plan)


def _changed(context, params: dict) -> ProjectPlan:
    """A draft with the change made: its title, sizes, beds, crops, frost dates, a stage left out or put back, its
    notes; worked out again, on a copy (the kept one changes only when this all works and is put back). The card's
    sentence runs this too, so a change that can't be made is said before the card."""
    plan = copy.deepcopy(_draft_of(context, params))
    if "title" in params:
        plan.title = str(params["title"] or plan.title)[:80]
    if "sizes" in params:
        plan.sizes = dict(params["sizes"] or {})
    if "beds" in params:
        plan.beds = _beds(params["beds"])
    if "crops" in params:
        plan.crops = _crops(params["crops"])
    for key in ("last_frost", "first_frost", "notes"):
        if key in params:
            setattr(plan, key, str(params[key] or "")[:2000])
    if params.get("leave_out"):
        plan.left_out = sorted(set(plan.left_out) | {str(params["leave_out"]).strip()})
    if params.get("put_back"):
        plan.left_out = [s for s in plan.left_out if s != str(params["put_back"])]
    return work_out(context, plan)


def _objective(step: dict) -> str:
    """Pure logic. A step as a mission objective: what to do, and when."""
    return (step["do"] + (f" ({step['when']})" if step.get("when") else ""))[:300]


def confirm(context, params: dict) -> str:
    """His press: the draft becomes one project and one mission a stage (each step an objective, in order), the
    build's materials on the project's needs; the plan keeps their ids. Worked out on a copy, kept only at the end."""
    plan = work_out(context, copy.deepcopy(_draft_of(context, params)))  # as things are now, on a copy
    projects, missions = _need(context, "projects"), _need(context, "missions")
    summary = f"Planned with MIA (plan:{plan.plan_id})."
    if plan.warnings:
        summary += "\n" + "\n".join("- " + w for w in plan.warnings)
    project = projects.add_project(name=plan.title, description=summary)
    plan.project_id = project.project_id
    if plan.kind == "build" and plan.shelf_plan:
        try:
            from core.plan_actions import _needs_from, _worked

            shelf, materials, _ = _worked(context, {"plan_id": plan.shelf_plan, **plan.sizes})
            _needs_from(context, project, materials, shelf)
        except ActionError:
            pass
    plan.mission_ids = []
    for n, stage in enumerate(plan.stages, start=1):
        mission = missions.add_mission(f"{plan.title}: {stage['name']}", project_id=project.project_id,
                                       summary=f"Stage {n} of {len(plan.stages)} of {plan.title}.",
                                       icon="\U0001F331" if plan.kind == "garden" else "\U0001F6E0")
        for step in stage["steps"]:
            missions.add_objective(mission.mission_id, _objective(step), "tally", 1)
        plan.mission_ids.append(mission.mission_id)
    plan.status = "confirmed"
    _need(context, "project_plans").put(plan)
    return (f"Confirmed “{plan.title}”: the project and {len(plan.mission_ids)} mission"
            f"{'s' if len(plan.mission_ids) != 1 else ''}, one a stage, each step on its own screen.")


def drop(context, params: dict) -> str:
    """Lets a draft go (a confirmed plan stays: its missions are his to end)."""
    plan = _draft_of(context, params)
    plan.status = "dropped"
    _need(context, "project_plans").put(plan)
    return f"Let “{plan.title}” go."


def page(context) -> dict:
    """The Planner page: the plans (drafts and confirmed, each build with its own size fields), the shelf's builds
    that have a walkthrough, the crops, and his frost dates."""
    from core import garden_plans, trades

    book = getattr(context, "project_plans", None)
    library = getattr(context, "plans", None)
    trades._loaded()
    walked = {j.plan: j for j in trades.JOBS.values() if j.plan}
    builds = [{"id": p["id"], "title": p["title"], "walked": _bare(p["id"]) in walked}
              for p in (library.built_in() if library is not None else [])]
    config = getattr(context, "config", None)
    plans = []
    for p in (book.listed() if book else []):
        row = asdict(p)
        row["size_fields"] = _size_fields(context, p)
        plans.append(row)
    return {"available": book is not None, "plans": plans,
            "builds": builds, "crops": [{"id": c.id, "name": c.name, "per_sqft": c.per_sqft, "days": c.days}
                                       for c in garden_plans.CROPS.values()],
            "last_frost": config.get("garden.last_frost", "") if config else "",
            "first_frost": config.get("garden.first_frost", "") if config else "", "sources": list(garden_plans.SOURCES)}


def _size_fields(context, plan: ProjectPlan) -> list:
    """A build draft's own sizes, as its plan's calculator names them ({name, label, unit, value}); [] for a garden."""
    if plan.kind != "build" or not plan.shelf_plan:
        return []
    from core.plan_library import detail

    try:
        return list((detail(context, plan.shelf_plan, plan.sizes or None) or {}).get("sizes") or [])
    except Exception:  # noqa: BLE001 - the page shows the plan either way
        return []


def _describe_draft(c, p) -> str:
    """The card's sentence for a draft, once it's worked out (so what's missing is asked before the card)."""
    plan = _new(c, p)
    return f"Draft the plan “{plan.title}”: {len(plan.stages)} stages to go through together"


def _describe_confirm(c, p) -> str:
    """The card's sentence for a confirm: what it makes (worked out on a copy)."""
    plan = work_out(c, copy.deepcopy(_draft_of(c, p)))
    return (f"Confirm “{plan.title}”: a project and {len(plan.stages)} missions ("
            + ", ".join(s["name"] for s in plan.stages) + ")")


PLAN_ACTIONS: dict[str, ActionType] = {a.kind: a for a in (
    ActionType("projectplan.draft", "Plan It", {"kind": "build or garden", "shelf_plan": "a Library plan's id",
               "sizes": "its sizes", "job": "a Trade Master job", "beds": "garden beds", "crops": "crops",
               "last_frost": "his last spring frost", "first_frost": "his first fall frost", "title": "a name"},
               _describe_draft, lambda c, p: f"Drafted “{draft(c, p).title}”. Change anything, then Confirm."),
    ActionType("projectplan.change", "Change It", {"plan_id": "the draft", "sizes": "", "beds": "", "crops": "",
               "last_frost": "", "first_frost": "", "leave_out": "a stage", "put_back": "a stage", "notes": ""},
               lambda c, p: f"Change the plan “{_changed(c, p).title}”",
               lambda c, p: f"Changed “{change(c, p).title}”."),
    ActionType("projectplan.confirm", "Confirm", {"plan_id": "the draft"}, _describe_confirm, confirm),
    ActionType("projectplan.drop", "Let It Go", {"plan_id": "the draft"},
               lambda c, p: f"Let the plan “{_draft_of(c, p).title}” go", drop),
)}
ACTION_TYPES.update(PLAN_ACTIONS)
