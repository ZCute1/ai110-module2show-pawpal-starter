"""Tests for PawPal+ core classes.

Organized by the behavior under test:

- Happy paths      -- the core scheduling promise works end to end.
- Recurrence       -- completing a repeating task spawns its next occurrence.
- Task retrieval   -- pending_tasks / filter_tasks / sort_by_time.
- Conflicts        -- same-time task detection.
- Free windows     -- gaps computed correctly around commitments.
- Edge cases       -- empty inputs, exact fits, buffers, nothing-fits.
- Day rollover     -- future-dated tasks held back; stale tasks rolled forward.

Times are minutes since midnight (09:00 = 540). Dates are pinned relative to
date.today() so the suite is deterministic no matter when it runs.
"""

from datetime import date, timedelta

import pytest

from pawpal_system import (
    BUFFER_MIN,
    DAY_END_MIN,
    DAY_START_MIN,
    Owner,
    Pet,
    Task,
)

TODAY = date.today()
TOMORROW = TODAY + timedelta(days=1)
YESTERDAY = TODAY - timedelta(days=1)


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def owner() -> Owner:
    """An owner planning for TODAY, with no pets or commitments yet."""
    return Owner("Jordan", TODAY)


@pytest.fixture
def mochi() -> Pet:
    """A high-energy dog (soft target -> morning)."""
    return Pet("Mochi", "dog", "Shiba Inu", "high")


@pytest.fixture
def luna() -> Pet:
    """A low-energy cat (soft target -> afternoon)."""
    return Pet("Luna", "cat", "Tabby", "low")


def placed_tasks(owner: Owner) -> list:
    """Blocks in the built plan that hold a pet task (not commitments)."""
    return [b for b in owner.schedule.blocks if b.task is not None]


def block_for(owner: Owner, title: str):
    """The placed block for a task with the given title, or None if unplaced."""
    return next((b for b in owner.schedule.blocks if b.label == title), None)


# ===========================================================================
# Happy paths
# ===========================================================================
class TestHappyPaths:
    def test_basic_build_places_everything(self, owner, mochi):
        """A handful of tasks with plenty of free time all get placed."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Walk", 30, "high"))
        mochi.add_task(Task("Feed", 15, "medium"))
        mochi.add_task(Task("Play", 20, "low"))

        owner.build_day()

        assert len(placed_tasks(owner)) == 3
        assert owner.schedule.unplaced == []

    def test_placed_tasks_never_overlap_a_commitment(self, owner, mochi):
        """No placed task straddles the owner's fixed commitment."""
        owner.add_pet(mochi)
        owner.add_commitment(9 * 60, 17 * 60, "Work")  # 09:00-17:00
        mochi.add_task(Task("Walk", 45, "high"))
        mochi.add_task(Task("Vet call", 20, "medium"))

        owner.build_day()

        for b in placed_tasks(owner):
            # A task lies entirely before 09:00 or entirely after 17:00.
            assert b.end_min <= 9 * 60 or b.start_min >= 17 * 60

    def test_priority_wins_the_contested_slot(self, owner, mochi):
        """When two tasks want the same time, the high-priority one gets it."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Important", 30, "high", scheduled_time="08:00"))
        mochi.add_task(Task("Optional", 30, "low", scheduled_time="08:00"))

        owner.build_day()

        assert block_for(owner, "Important").start_min == 8 * 60  # got 08:00
        assert block_for(owner, "Optional").start_min != 8 * 60   # bumped away

    def test_scheduled_time_is_honored_when_free(self, owner, mochi):
        """A task with a preferred time lands exactly there if the slot is open."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Walk", 30, "high", scheduled_time="08:00"))

        owner.build_day()

        assert block_for(owner, "Walk").start_min == 8 * 60

    def test_scheduled_time_bumped_when_blocked(self, owner, mochi):
        """A preferred time inside a commitment is moved to a free slot."""
        owner.add_pet(mochi)
        owner.add_commitment(9 * 60, 17 * 60, "Work")
        mochi.add_task(Task("Vet call", 20, "medium", scheduled_time="12:30"))

        owner.build_day()

        block = block_for(owner, "Vet call")
        assert block is not None
        assert block.start_min != to_min("12:30")  # couldn't land at 12:30

    def test_high_energy_pet_gets_a_morning_slot(self, owner, mochi):
        """No preferred time + high activity -> nudged toward morning (~08:00)."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Walk", 30, "medium"))  # no scheduled_time

        owner.build_day()

        assert block_for(owner, "Walk").start_min == 8 * 60

    def test_low_energy_pet_gets_an_afternoon_slot(self, owner, luna):
        """No preferred time + low activity -> nudged toward afternoon (~16:00)."""
        owner.add_pet(luna)
        luna.add_task(Task("Grooming", 20, "medium"))

        owner.build_day()

        assert block_for(owner, "Grooming").start_min == 16 * 60


# ===========================================================================
# Recurrence
# ===========================================================================
class TestRecurrence:
    def test_daily_task_spawns_next_day(self, mochi):
        """Completing a daily task adds one new task due one day later."""
        mochi.add_task(Task("Walk", 30, "high", recurrence="daily", due_date=TODAY))
        original = mochi.tasks[0]

        original.mark_complete()

        assert len(mochi.tasks) == 2
        spawned = mochi.tasks[-1]
        assert spawned.due_date == TODAY + timedelta(days=1)
        assert spawned.completed is False
        assert spawned.recurrence == "daily"
        assert spawned.pet is mochi  # linked back to the same pet

    def test_weekly_task_spawns_seven_days_later(self, mochi):
        """A weekly task's next occurrence is due +7 days."""
        mochi.add_task(Task("Bath", 30, "low", recurrence="weekly", due_date=TODAY))

        mochi.tasks[0].mark_complete()

        assert mochi.tasks[-1].due_date == TODAY + timedelta(days=7)

    def test_one_off_task_spawns_nothing(self, mochi):
        """A non-recurring task does not create a follow-up when completed."""
        mochi.add_task(Task("Vet visit", 30, "high"))  # recurrence=""

        mochi.tasks[0].mark_complete()

        assert len(mochi.tasks) == 1

    def test_next_occurrence_anchored_to_due_date_not_today(self, mochi):
        """The spawn is +1 from the task's own due_date, not from 'today'."""
        mochi.add_task(Task("Walk", 30, "high", recurrence="daily", due_date=YESTERDAY))

        mochi.tasks[0].mark_complete()

        assert mochi.tasks[-1].due_date == YESTERDAY + timedelta(days=1)  # == TODAY


# ===========================================================================
# Task retrieval: pending / filter / sort
# ===========================================================================
class TestTaskRetrieval:
    def test_pending_excludes_completed(self, owner, mochi):
        """A checked-off task drops out of pending_tasks."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Walk", 30, "high"))
        mochi.tasks[0].mark_complete()

        assert owner.schedule.pending_tasks() == []

    def test_pending_excludes_future_dated(self, owner, mochi):
        """A task due tomorrow is not pending on today's schedule."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Walk", 30, "high", due_date=TOMORROW))

        assert owner.schedule.pending_tasks() == []

    def test_pending_includes_no_due_date_and_today(self, owner, mochi):
        """Tasks with no due_date, or due today, are pending."""
        owner.add_pet(mochi)
        mochi.add_task(Task("No date", 30, "high"))            # due_date=None
        mochi.add_task(Task("Due today", 30, "high", due_date=TODAY))

        titles = {t.title for t in owner.schedule.pending_tasks()}
        assert titles == {"No date", "Due today"}

    def test_completed_task_not_placed_in_plan(self, owner, mochi):
        """A completed task never appears in the built schedule."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Walk", 30, "high"))
        mochi.tasks[0].mark_complete()

        owner.build_day()

        assert block_for(owner, "Walk") is None

    def test_filter_by_pet_name_is_case_insensitive(self, owner, mochi, luna):
        """filter_tasks(pet_name=...) matches regardless of case."""
        owner.add_pet(mochi)
        owner.add_pet(luna)
        mochi.add_task(Task("Walk", 30, "high"))
        luna.add_task(Task("Nap", 30, "low"))

        result = owner.schedule.filter_tasks(pet_name="luna")

        assert len(result) == 1
        assert result[0].title == "Nap"

    def test_filter_combines_pet_and_completion(self, owner, mochi):
        """The two filters AND together."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Done", 30, "high"))
        mochi.add_task(Task("Todo", 30, "high"))
        mochi.tasks[0].mark_complete()

        result = owner.schedule.filter_tasks(pet_name="Mochi", completed=False)

        assert [t.title for t in result] == ["Todo"]

    def test_sort_by_time_orders_chronologically(self, owner, mochi):
        """Tasks sort by scheduled_time; no-time tasks sort to the front."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Afternoon", 30, "high", scheduled_time="14:00"))
        mochi.add_task(Task("Morning", 30, "high", scheduled_time="09:30"))
        mochi.add_task(Task("Anytime", 30, "high"))  # ""

        order = [t.title for t in owner.schedule.sort_by_time()]

        assert order == ["Anytime", "Morning", "Afternoon"]


# ===========================================================================
# Conflict detection
# ===========================================================================
class TestConflicts:
    def test_same_time_tasks_flagged(self, owner, mochi):
        """Two tasks requesting overlapping slots produce one warning."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Groomer", 30, "medium", scheduled_time="06:30"))
        mochi.add_task(Task("Playdate", 30, "low", scheduled_time="06:30"))

        conflicts = owner.schedule.detect_conflicts()

        assert len(conflicts) == 1
        assert "same pet" in conflicts[0]

    def test_different_pets_labeled(self, owner, mochi, luna):
        """A clash across two pets is labeled 'different pets'."""
        owner.add_pet(mochi)
        owner.add_pet(luna)
        mochi.add_task(Task("Walk", 30, "high", scheduled_time="07:00"))
        luna.add_task(Task("Feed", 30, "high", scheduled_time="07:00"))

        conflicts = owner.schedule.detect_conflicts()

        assert len(conflicts) == 1
        assert "different pets" in conflicts[0]

    def test_non_overlapping_times_no_conflict(self, owner, mochi):
        """Back-to-back (non-overlapping) slots don't clash."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Walk", 30, "high", scheduled_time="07:00"))  # 07:00-07:30
        mochi.add_task(Task("Feed", 30, "high", scheduled_time="07:30"))  # 07:30-08:00

        assert owner.schedule.detect_conflicts() == []

    def test_tasks_without_a_time_never_conflict(self, owner, mochi):
        """Tasks with no scheduled_time can't clash on time."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Walk", 30, "high"))
        mochi.add_task(Task("Feed", 30, "high"))

        assert owner.schedule.detect_conflicts() == []

    def test_both_conflicting_tasks_still_get_placed(self, owner, mochi):
        """Detection warns, but build() still schedules both (one bumped)."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Groomer", 30, "medium", scheduled_time="06:30"))
        mochi.add_task(Task("Playdate", 30, "low", scheduled_time="06:30"))

        owner.build_day()

        assert len(placed_tasks(owner)) == 2
        assert owner.schedule.unplaced == []


# ===========================================================================
# Free windows
# ===========================================================================
class TestFreeWindows:
    def test_empty_schedule_is_one_full_window(self, owner):
        """With no commitments, the whole day is one free window."""
        windows = owner.schedule.free_windows()

        assert len(windows) == 1
        assert windows[0].start_min == DAY_START_MIN
        assert windows[0].end_min == DAY_END_MIN

    def test_commitment_splits_the_day(self, owner):
        """A midday commitment yields a window before and after it."""
        owner.add_commitment(9 * 60, 17 * 60, "Work")

        windows = owner.schedule.free_windows()

        spans = [(w.start_min, w.end_min) for w in windows]
        assert spans == [(DAY_START_MIN, 9 * 60), (17 * 60, DAY_END_MIN)]

    def test_overlapping_commitments_merge(self, owner):
        """A nested commitment doesn't create a bogus window inside another."""
        owner.add_commitment(9 * 60, 17 * 60, "Work")    # 09:00-17:00
        owner.add_commitment(12 * 60, 13 * 60, "Lunch")  # nested inside Work

        windows = owner.schedule.free_windows()

        spans = [(w.start_min, w.end_min) for w in windows]
        assert spans == [(DAY_START_MIN, 9 * 60), (17 * 60, DAY_END_MIN)]
        for w in windows:
            assert w.end_min > w.start_min  # no zero/negative windows

    def test_fully_booked_day_has_no_windows(self, owner):
        """A commitment spanning the whole day leaves no free time."""
        owner.add_commitment(DAY_START_MIN, DAY_END_MIN, "All day")

        assert owner.schedule.free_windows() == []


# ===========================================================================
# Edge cases
# ===========================================================================
class TestEdgeCases:
    def test_owner_with_no_pets_builds_empty(self, owner):
        """No pets -> no tasks -> empty plan, no error."""
        assert owner.build_day() == []
        assert owner.schedule.unplaced == []

    def test_pet_with_no_tasks_builds_empty(self, owner, mochi):
        """A pet with zero tasks contributes nothing and doesn't crash."""
        owner.add_pet(mochi)

        assert owner.build_day() == []

    def test_task_that_does_not_fit_is_unplaced(self, owner, mochi):
        """A task too big for any free window lands in unplaced."""
        owner.add_pet(mochi)
        owner.add_commitment(DAY_START_MIN, DAY_END_MIN, "All day")  # no free time
        mochi.add_task(Task("Walk", 30, "high"))

        owner.build_day()

        assert block_for(owner, "Walk") is None
        assert owner.schedule.unplaced[0].title == "Walk"

    def test_task_fitting_a_window_exactly_is_placed(self, owner, mochi):
        """A task whose duration exactly equals the free window still fits."""
        owner.add_pet(mochi)
        # Leave exactly a 30-minute window at the end of the day (21:30-22:00).
        owner.add_commitment(DAY_START_MIN, DAY_END_MIN - 30, "Busy")
        mochi.add_task(Task("Walk", 30, "medium"))  # medium -> best-fit

        owner.build_day()

        block = block_for(owner, "Walk")
        assert block is not None
        assert (block.start_min, block.end_min) == (DAY_END_MIN - 30, DAY_END_MIN)

    def test_buffer_is_kept_between_placed_tasks(self, owner, mochi):
        """Two placed tasks are separated by at least BUFFER_MIN."""
        owner.add_pet(mochi)
        mochi.add_task(Task("First", 30, "medium"))
        mochi.add_task(Task("Second", 30, "medium"))

        owner.build_day()

        starts = sorted(placed_tasks(owner), key=lambda b: b.start_min)
        gap = starts[1].start_min - starts[0].end_min
        assert gap >= BUFFER_MIN

    def test_priority_normalized_to_lowercase(self):
        """Task casing is normalized in __post_init__."""
        assert Task("Walk", 30, "HIGH").priority == "high"

    def test_recurrence_normalized_to_lowercase(self):
        """Recurrence casing is normalized in __post_init__."""
        assert Task("Walk", 30, "high", recurrence="Daily").recurrence == "daily"


# ===========================================================================
# Day rollover
# ===========================================================================
class TestDayRollover:
    def test_start_new_day_advances_the_date(self, owner):
        """Rolling over moves the schedule to the next calendar day."""
        owner.start_new_day()

        assert owner.schedule.day == TOMORROW

    def test_spawned_recurrence_held_back_then_appears(self, owner, luna):
        """A daily task's spawn is invisible today, visible after rollover.

        This is the recurrence + date-filter integration: completing today's
        instance spawns tomorrow's, which stays off today's plan until the day
        rolls forward to its due date.
        """
        owner.add_pet(luna)
        luna.add_task(Task("Feed", 15, "high", recurrence="daily", due_date=TODAY))

        owner.check_off(luna.tasks[0])  # completes today's, spawns tomorrow's
        # Today: original is done, spawn is future-dated -> nothing pending.
        assert owner.schedule.pending_tasks() == []

        owner.start_new_day()
        # Tomorrow: the spawned occurrence is now due and eligible.
        pending_titles = [t.title for t in owner.schedule.pending_tasks()]
        assert pending_titles == ["Feed"]

    def test_stale_recurring_task_rolls_forward_without_duplicating(self, owner, mochi):
        """An uncompleted recurring task due in the past is re-dated, not cloned."""
        owner.add_pet(mochi)
        mochi.add_task(Task("Walk", 30, "high", recurrence="daily", due_date=YESTERDAY))

        owner.start_new_day()

        assert len(mochi.tasks) == 1                      # not duplicated
        assert mochi.tasks[0].due_date == TOMORROW        # rolled to the new day

    def test_commitments_survive_rollover(self, owner, mochi):
        """clear_plan on rollover keeps commitments but drops placed tasks."""
        owner.add_pet(mochi)
        owner.add_commitment(9 * 60, 17 * 60, "Work")
        mochi.add_task(Task("Walk", 30, "high"))
        owner.build_day()
        assert len(placed_tasks(owner)) == 1

        owner.start_new_day()

        # The commitment remains; the generated task placement is cleared.
        assert placed_tasks(owner) == []
        assert any(b.label == "Work" for b in owner.schedule.blocks)


# Small local helper mirroring the model's "HH:MM" -> minutes conversion,
# used only for readability in assertions above.
def to_min(hhmm: str) -> int:
    hours, mins = hhmm.split(":")
    return int(hours) * 60 + int(mins)
