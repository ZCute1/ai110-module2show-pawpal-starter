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

Run the full test suite from the project root:

```bash
python -m pytest
```

Add `-v` for the per-test breakdown shown below.

### What the tests cover

The suite (`tests/test_pawpal.py`, 38 tests) exercises the scheduling logic in
`pawpal_system.py` across seven areas:

- **Happy paths** — tasks get placed, never overlap commitments, high-priority
  tasks win a contested slot, preferred times are honored (and bumped when
  blocked), and a pet's activity level biases placement (high → morning,
  low → afternoon).
- **Recurrence** — completing a daily task spawns the next day's task, weekly
  spawns +7 days, one-off tasks spawn nothing, and the new task is anchored to
  the original's due date.
- **Task retrieval** — `pending_tasks` excludes completed and future-dated
  tasks; `filter_tasks` combines pet-name (case-insensitive) and completion
  filters; `sort_by_time` returns tasks in chronological order.
- **Conflict detection** — same-time tasks are flagged with the correct
  same-pet / different-pet label, non-overlapping and untimed tasks don't clash,
  and both conflicting tasks still get scheduled.
- **Free windows** — gaps are computed correctly around commitments, including
  overlapping/nested ones and a fully booked day.
- **Edge cases** — no pets / no tasks, a task too big to fit (goes to
  `unplaced`), exact-fit windows, the 10-minute buffer between tasks, and input
  normalization.
- **Day rollover** — future-dated recurrences stay hidden until their day
  arrives, stale tasks roll forward without duplicating, and commitments survive
  the rollover.

Tests are deterministic (dates pinned relative to `today`) and import the
module's config constants, so they stay valid if those values change.

### Successful test run

```
$ python -m pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: .../ai110-module2show-pawpal-starter
plugins: anyio-4.14.0
collected 38 items

tests/test_pawpal.py::TestHappyPaths::test_basic_build_places_everything PASSED [  2%]
tests/test_pawpal.py::TestHappyPaths::test_placed_tasks_never_overlap_a_commitment PASSED [  5%]
tests/test_pawpal.py::TestHappyPaths::test_priority_wins_the_contested_slot PASSED [  7%]
tests/test_pawpal.py::TestHappyPaths::test_scheduled_time_is_honored_when_free PASSED [ 10%]
tests/test_pawpal.py::TestHappyPaths::test_scheduled_time_bumped_when_blocked PASSED [ 13%]
tests/test_pawpal.py::TestHappyPaths::test_high_energy_pet_gets_a_morning_slot PASSED [ 15%]
tests/test_pawpal.py::TestHappyPaths::test_low_energy_pet_gets_an_afternoon_slot PASSED [ 18%]
tests/test_pawpal.py::TestRecurrence::test_daily_task_spawns_next_day PASSED [ 21%]
tests/test_pawpal.py::TestRecurrence::test_weekly_task_spawns_seven_days_later PASSED [ 23%]
tests/test_pawpal.py::TestRecurrence::test_one_off_task_spawns_nothing PASSED [ 26%]
tests/test_pawpal.py::TestRecurrence::test_next_occurrence_anchored_to_due_date_not_today PASSED [ 28%]
tests/test_pawpal.py::TestTaskRetrieval::test_pending_excludes_completed PASSED [ 31%]
tests/test_pawpal.py::TestTaskRetrieval::test_pending_excludes_future_dated PASSED [ 34%]
tests/test_pawpal.py::TestTaskRetrieval::test_pending_includes_no_due_date_and_today PASSED [ 36%]
tests/test_pawpal.py::TestTaskRetrieval::test_completed_task_not_placed_in_plan PASSED [ 39%]
tests/test_pawpal.py::TestTaskRetrieval::test_filter_by_pet_name_is_case_insensitive PASSED [ 42%]
tests/test_pawpal.py::TestTaskRetrieval::test_filter_combines_pet_and_completion PASSED [ 44%]
tests/test_pawpal.py::TestTaskRetrieval::test_sort_by_time_orders_chronologically PASSED [ 47%]
tests/test_pawpal.py::TestConflicts::test_same_time_tasks_flagged PASSED [ 50%]
tests/test_pawpal.py::TestConflicts::test_different_pets_labeled PASSED  [ 52%]
tests/test_pawpal.py::TestConflicts::test_non_overlapping_times_no_conflict PASSED [ 55%]
tests/test_pawpal.py::TestConflicts::test_tasks_without_a_time_never_conflict PASSED [ 57%]
tests/test_pawpal.py::TestConflicts::test_both_conflicting_tasks_still_get_placed PASSED [ 60%]
tests/test_pawpal.py::TestFreeWindows::test_empty_schedule_is_one_full_window PASSED [ 63%]
tests/test_pawpal.py::TestFreeWindows::test_commitment_splits_the_day PASSED [ 65%]
tests/test_pawpal.py::TestFreeWindows::test_overlapping_commitments_merge PASSED [ 68%]
tests/test_pawpal.py::TestFreeWindows::test_fully_booked_day_has_no_windows PASSED [ 71%]
tests/test_pawpal.py::TestEdgeCases::test_owner_with_no_pets_builds_empty PASSED [ 73%]
tests/test_pawpal.py::TestEdgeCases::test_pet_with_no_tasks_builds_empty PASSED [ 76%]
tests/test_pawpal.py::TestEdgeCases::test_task_that_does_not_fit_is_unplaced PASSED [ 78%]
tests/test_pawpal.py::TestEdgeCases::test_task_fitting_a_window_exactly_is_placed PASSED [ 81%]
tests/test_pawpal.py::TestEdgeCases::test_buffer_is_kept_between_placed_tasks PASSED [ 84%]
tests/test_pawpal.py::TestEdgeCases::test_priority_normalized_to_lowercase PASSED [ 86%]
tests/test_pawpal.py::TestEdgeCases::test_recurrence_normalized_to_lowercase PASSED [ 89%]
tests/test_pawpal.py::TestDayRollover::test_start_new_day_advances_the_date PASSED [ 92%]
tests/test_pawpal.py::TestDayRollover::test_spawned_recurrence_held_back_then_appears PASSED [ 94%]
tests/test_pawpal.py::TestDayRollover::test_stale_recurring_task_rolls_forward_without_duplicating PASSED [ 97%]
tests/test_pawpal.py::TestDayRollover::test_commitments_survive_rollover PASSED [100%]

============================== 38 passed in 0.02s ==============================
```

### Confidence level

**★★★☆☆ (3 / 5)**

All 38 tests pass and cover the core behaviors plus the edge cases I could think
of. I'm holding the rating at 3 stars on purpose: the tests were written *after*
the code (not test-driven), so they largely confirm the scheduler does what the
implementation already assumes rather than proving the design is complete. One known open question remains unverified: whether a
buffer should also be enforced between a task and a fixed commitment, not just
between two tasks. Fresh eyes or real-world use could still
surface a case neither the code nor the tests anticipated.

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
