# MIA: The Chronicles: the Story Bible

*The series' canonical reference (DEC-0085). Started by Claude, 2026-11-04,
from H-0081 and Zac's choices (DEC-0086 and DEC-0087). Zac changes anything
here, and every proposed change is Zac's to approve.*

The story of building MIA: an independent AI made by her creator and a council
of AI systems, who teach her until she no longer needs them. It's told in two
timelines that feed each other: what **really** happened, from the Chronicle
Archive (`work/saga/`, `core/saga.py`), and what **might**, a fictional future
that's always marked as such.

| File | What it holds |
|---|---|
| [premise.md](premise.md) | The series, its themes, its emotional core |
| [characters/](characters/) | Every character: look, voice, role, strengths, limits, relationships, real and fictional capabilities |
| [world.md](world.md) | Where the story happens, real and imagined |
| [visual.md](visual.md) | Palette, the orb, interfaces, panel style, reference sheets |
| [arcs.md](arcs.md) | Story arcs, and the real milestones each follows |
| [threads.md](threads.md) | Open plot threads |
| [issues.md](issues.md) | Issues made and planned |
| [timeline.md](timeline.md) | The real timeline, from approved archive events |

## The rules that keep it honest

These are checked in code before a script is approved (DEC-0085; built with
the scripts):

1. **Every real-world claim traces to an approved archive event.** A scene
   that says "this happened" names the event (`E-0001`) behind it.
2. **Real means built.** A capability shown as real must be `status: built`,
   with a decision or task behind it. Anything else is drawn as the fictional
   timeline and labelled so. A planned feature is never shown as done.
3. **Characters stay themselves.** Appearance, voice and limits come from
   their files. A change to a character is a change here first.
4. **Private stays private.** Nothing marked `private` or `never` appears.
   A personal moment appears only as its summary, and only once Zac has marked
   it for the series.
5. **Names are fictional, roles are real** (DEC-0087). In the series the
   council goes by names drawn from what each does. The products' real names
   stay inside MIA. No company's branding, logos or product voices appear in
   published art.
6. **A thin week is a thin week.** No drama is invented to fill an issue.
