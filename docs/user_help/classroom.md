# Classroom: your own subjects, courses, and lessons

## What the Classroom module tracks

Classroom is a three-level drill-down: Subjects contain Courses,
Courses contain Lessons. It starts empty — this is your own real
curriculum (K-12-level academic subjects, trade skills, or anything
else you're studying), not a pre-built one.

## Adding a subject

Click Add Subject and give it a name (like "Geometry" or "Electrical")
and an optional category (like "Mathematics" or "Trade Skills") to
group related subjects together. Double-click a subject, or select it
and click Open, to see its courses.

## Adding courses and lessons

Inside a subject, click Add Course to create a course, then open it
the same way to add lessons with Add Lesson. Each subject and course
row shows how many of its lessons are complete (e.g. "3 of 5
complete"), rolled up automatically from its lessons — you never set
that number directly.

## Marking a lesson complete

Select a lesson and click Mark Complete/Incomplete to toggle it — this
is the only way completion changes; editing a lesson never touches its
completion state.

## Deleting

Deleting a Subject or Course removes everything underneath it too (its
Courses and their Lessons, or just its Lessons) — there's no way to
delete just the parent and keep orphaned children around, since a
Lesson or Course doesn't mean much without what it belongs to.

## Textbooks: MIA teaches from your own books

Classroom → 📚 Textbooks → Add Textbook… takes a PDF (or a .txt/.md
file). MIA copies it into its `textbooks` folder, finds the chapters,
and indexes every page so it can quote and cite them. Make a Course
turns a book into a Classroom course with one lesson per chapter.

Then in chat or on the phone:

- "Let's study the wiring book" or "Teach me from the wiring book":
  MIA explains using passages from the book and names the pages, and
  says so when the book doesn't cover something rather than guessing.
- "Quiz me on chapter 3": one question at a time, checked against the
  book.
- "What does my textbook say about grounding?": a quick lookup with the
  page number.
- "I'm done studying" or "back to normal" to leave study mode.

A scanned PDF (pictures of pages with no text layer) is read with
text recognition (Tesseract) in the background; the list shows its
progress ("reading the scan… page 12 of 300") and it's ready to study
when that's done. If it closes midway, MIA picks up where it stopped
next time. Without Tesseract installed, MIA says so instead of adding
an empty book. Your books are
never copied anywhere but MIA's own folder.
