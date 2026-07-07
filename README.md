# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Running the terminal demo (`python main.py`) creates an owner with two pets, adds
several tasks and the owner's commitments, then builds and prints the day's plan:

```
Heads up: 'Lunch w/ Sam' overlaps 'Work'.

===== Today's Schedule =====
Plan for 2026-07-06:
  06:00-06:15  Feeding for Luna (high priority)
  06:15-07:00  Morning walk for Mochi (high priority)
  07:00-07:30  Training session for Mochi (medium priority)
  07:30-07:50  Playtime for Luna (low priority)
  09:00-17:00  Work (commitment)
  12:00-13:00  Lunch w/ Sam (commitment)
```

The scheduler places pet tasks highest-priority-first into the free time around
the owner's fixed commitments, labels each task with the pet it belongs to, and
warns when a new commitment overlaps an existing one.

## System Design
- add a pet
- schedule a walk
- see today's tasks

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

The scheduling logic lives in the `Schedule` class in `pawpal_system.py` (the
class docstring calls it the "brain" — it retrieves tasks from the owner's pets
and places them around fixed commitments). The table summarizes each feature and
the method that implements it; details follow below.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Sorting | `Schedule.sort_by_time()` | Orders tasks by preferred `"HH:MM"` time |
| Filtering | `Schedule.filter_tasks()` (+ `all_tasks()`, `pending_tasks()`) | By pet name and/or completion status |
| Conflict detection | `Schedule.detect_conflicts()` | Flags tasks requested for overlapping times |
| Recurring tasks | `Task.mark_complete()` (+ `Owner.start_new_day()`, `Task.__post_init__`) | Daily/weekly tasks spawn their next occurrence |
| Placement | `Schedule.build()` (+ `free_windows()`) | Priority-first, preference-aware, best-fit, with buffers |

### Sorting — `Schedule.sort_by_time()`

Returns all tasks ordered by their preferred time of day. Each `Task` carries a
`scheduled_time` as a zero-padded `"HH:MM"` string (e.g. `"09:30"`); because
fixed-width `"HH:MM"` strings sort chronologically as plain strings, the method
is a one-line `sorted(..., key=lambda t: t.scheduled_time)`. Tasks with no
preferred time (`""`) sort to the front.

### Filtering — `Schedule.filter_tasks(pet_name=..., completed=...)`

Filters tasks by **pet name** and/or **completion status**. Both arguments are
optional keyword-only filters that combine with AND; passing `None` (the default)
means "don't filter on that field," and pet-name matching is case-insensitive.
Two helpers back it: `all_tasks()` returns every task across all pets (done or
not), and `pending_tasks()` returns only incomplete tasks that are due on or
before the schedule's day (so future-dated recurrences stay hidden until their
day arrives).

### Conflict detection — `Schedule.detect_conflicts()`

Reports pairs of tasks whose **requested** time slots overlap — a task with a
`scheduled_time` "wants" the slot `[start, start + duration]`, and two such slots
can't both happen as asked (one pet can't be in two places, and neither can the
single owner). It's a lightweight check: sort the timed slots by start, then
compare each against later ones only until they're clearly past it. It **collects
warning strings and returns them** (empty list = no conflicts) rather than
raising, so a clash is surfaced as a message the caller can print — the terminal
demo prints them, and `app.py` shows them as a Streamlit `st.warning` banner.
Note this checks the times you *requested*, not the built plan, since `build()`
itself never double-books.

### Recurring tasks — `Task.mark_complete()`

A `Task` has a `recurrence` field of `""` (one-off), `"daily"`, or `"weekly"`,
plus a `due_date`. When a recurring task is completed, `mark_complete()`
**automatically spawns a new `Task` instance** for the next occurrence, attached
to the same pet — one day later for daily, seven for weekly, computed with
`datetime.timedelta` so month/year boundaries and leap years roll over correctly.
Supporting pieces:

- `Task.__post_init__()` gives a recurring task a concrete `due_date` (today) as
  its anchor for the next occurrence.
- `Schedule.pending_tasks()` hides future-dated instances until their day.
- `Owner.start_new_day()` advances the schedule date and rolls any *missed*
  recurring task's `due_date` forward — so a skipped daily task stays "today's
  task" instead of lingering stale-dated, and never piles up into duplicates
  (spawning only happens on completion).

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
