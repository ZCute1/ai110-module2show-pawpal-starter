"""PawPal+ — core domain classes.

Data-holding types (Task, Pet, TimeBlock) are dataclasses; behavior-heavy types
(Owner, Schedule) are regular classes. The Schedule is the "brain": it retrieves
tasks from the owner's pets and places them around fixed commitments.

Times are stored as minutes since midnight (e.g. 9:30am = 570); use fmt() to
display them as "HH:MM".
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta

# Higher number = higher priority, so build() can sort tasks descending by rank.
PRIORITY_RANK = {"high": 2, "medium": 1, "low": 0}

# How far ahead each recurrence type schedules its next occurrence. Used with
# timedelta so completing a task spawns an accurately-dated follow-up.
RECURRENCE_DAYS = {"daily": 1, "weekly": 7}

# The daily window the scheduler is allowed to place tasks in (06:00–22:00).
DAY_START_MIN = 6 * 60
DAY_END_MIN = 22 * 60

# Minimum gap left between two placed tasks, for travel/prep/transition time.
BUFFER_MIN = 10

# Soft target time-of-day by pet activity level, used only when a task has no
# explicit scheduled_time: high-energy pets get morning slots, low-energy pets
# get afternoon ones. "medium"/unknown gets no bias (pure best-fit placement).
ACTIVITY_TARGET_MIN = {"high": 8 * 60, "low": 16 * 60}


def fmt(minutes: int) -> str:
    """Format minutes-since-midnight as 'HH:MM' (e.g. 570 -> '09:30')."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def to_minutes(hhmm: str) -> int | None:
    """Parse an 'HH:MM' string into minutes since midnight.

    Returns None for an empty string ("no preferred time") — the inverse of
    fmt(), used by build() to turn a task's scheduled_time into a target.
    """
    if not hhmm:
        return None
    hours, mins = hhmm.split(":")
    return int(hours) * 60 + int(mins)


@dataclass
class Task:
    """A single pet care task (e.g. morning walk, feeding)."""

    title: str
    duration_minutes: int
    priority: str  # "low" | "medium" | "high"
    # Preferred time of day as zero-padded "HH:MM" (e.g. "09:30"). Empty means
    # "no preference"; sort_by_time keys on this string directly.
    scheduled_time: str = ""
    # Recurrence: "" (one-off), "daily", or "weekly". A recurring task spawns
    # its next occurrence when completed (see mark_complete).
    recurrence: str = ""
    # The day this task is due. Defaults (in __post_init__) to today for a
    # recurring task, giving it a concrete anchor for the next occurrence.
    due_date: date | None = None
    completed: bool = False
    # Which pet this task belongs to. Set by Pet.add_task; kept out of init/repr/eq
    # so it doesn't need to be passed in and can't cause a Pet<->Task repr loop.
    pet: Pet | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Normalize casing, and give a recurring task a concrete due date."""
        self.priority = self.priority.lower()
        self.recurrence = self.recurrence.lower()
        if self.recurrence and self.due_date is None:
            self.due_date = date.today()

    @property
    def pet_name(self) -> str:
        """Name of the owning pet, or 'unassigned' if unlinked."""
        return self.pet.name if self.pet else "unassigned"

    def mark_complete(self) -> None:
        """Mark this task done; if it recurs, spawn its next occurrence.

        A "daily" task's next instance is due one day later and a "weekly" task's
        one week later — computed with timedelta so month/year boundaries and
        leap years roll over correctly. The new Task is attached to the same pet.
        """
        self.completed = True
        step = RECURRENCE_DAYS.get(self.recurrence)
        if step is None or self.pet is None:
            return  # one-off task, or somehow detached from a pet — nothing to spawn
        anchor = self.due_date or date.today()
        self.pet.add_task(
            Task(
                self.title,
                self.duration_minutes,
                self.priority,
                scheduled_time=self.scheduled_time,
                recurrence=self.recurrence,
                due_date=anchor + timedelta(days=step),
            )
        )


@dataclass
class Pet:
    """A pet the owner cares for, and the tasks it needs."""

    name: str
    species: str
    breed: str
    activity_level: str  # "low" | "medium" | "high"
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet, and link the task back to this pet."""
        task.pet = self
        self.tasks.append(task)


@dataclass(eq=False)
class TimeBlock:
    """A span of time on the schedule.

    Times are minutes since midnight (e.g. 9:30am = 570); use fmt() to display.
    An empty ``task`` means this is a commitment (work, meetings, etc.) the
    scheduler must plan around. A set ``task`` means it's a pet task the
    scheduler placed into a free window.

    eq=False so blocks compare by identity — remove_block/move_block target the
    exact object, not any other block that happens to have equal field values.
    """

    label: str
    start_min: int
    end_min: int
    task: Task | None = None

    @property
    def duration(self) -> int:
        """Length of the block in minutes."""
        return self.end_min - self.start_min


def _overlaps(a: TimeBlock, b: TimeBlock) -> bool:
    """Return True if two time spans overlap.

    Single source of truth for overlap checks — used by add_commitment (warning),
    free_windows (finding gaps), and build (does a task fit?).
    """
    return a.start_min < b.end_min and b.start_min < a.end_min


class Schedule:
    """The owner's day: fixed commitments plus placed pet tasks."""

    def __init__(self, day: date, owner: Owner) -> None:
        """Create an empty schedule for a given day, tied to its owner."""
        self.day: date = day
        self.owner: Owner = owner  # back-reference so the scheduler can retrieve tasks
        self.blocks: list[TimeBlock] = []
        self.unplaced: list[Task] = []  # tasks that didn't fit after build()

    def all_tasks(self) -> list[Task]:
        """Retrieve every task across all of the owner's pets (done or not)."""
        return [task for pet in self.owner.pets for task in pet.tasks]

    def pending_tasks(self) -> list[Task]:
        """Retrieve incomplete tasks due on or before this schedule's day.

        This is the scheduler acting as the 'brain': it reaches through the owner
        to gather tasks itself, rather than being handed a ready-made list. Tasks
        with no due_date are always eligible; a future-dated task (e.g. tomorrow's
        spawned recurrence) is held back until the day rolls forward to it.
        """
        return [
            t
            for t in self.all_tasks()
            if not t.completed and (t.due_date is None or t.due_date <= self.day)
        ]

    def sort_by_time(self) -> list[Task]:
        """Return all tasks sorted by their scheduled "HH:MM" time.

        Zero-padded "HH:MM" strings sort chronologically as plain strings
        ("09:30" < "14:00"), so a simple string key on scheduled_time is enough.
        Tasks with no preferred time ("") sort to the front.
        """
        return sorted(self.all_tasks(), key=lambda t: t.scheduled_time)

    def filter_tasks(
        self, *, pet_name: str | None = None, completed: bool | None = None
    ) -> list[Task]:
        """Filter tasks by pet name and/or completion status.

        Both filters are optional and combine (AND). Leaving one as None means
        "don't filter on it". Pet-name matching is case-insensitive.
        """
        tasks = self.all_tasks()
        if pet_name is not None:
            tasks = [t for t in tasks if t.pet and t.pet.name.lower() == pet_name.lower()]
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        return tasks

    def detect_conflicts(self) -> list[str]:
        """Report pairs of tasks whose requested time slots overlap.

        A task with a scheduled_time "wants" the slot [start, start + duration].
        If two such slots overlap they can't both happen as asked — one pet can't
        be in two places, and neither can the single owner. This is a lightweight
        O(n log n + pairs) check: sort by start, compare each slot only against
        later ones until they're clearly past it. It COLLECTS warning strings and
        returns them (empty list = no conflicts) — it never raises, so a clash is
        surfaced as a message to print, not a crash.
        """
        # Only tasks that actually request a time can clash on time. Parse each
        # scheduled_time once, reusing it for both the start and the end.
        slots: list[TimeBlock] = []
        for t in self.pending_tasks():
            if not t.scheduled_time:
                continue
            start = to_minutes(t.scheduled_time)
            slots.append(TimeBlock(t.title, start, start + t.duration_minutes, t))
        slots.sort(key=lambda b: b.start_min)

        warnings: list[str] = []
        for i, a in enumerate(slots):
            for b in slots[i + 1 :]:
                if b.start_min >= a.end_min:
                    break  # sorted by start: no later slot can overlap 'a' either
                if not _overlaps(a, b):
                    continue
                # Every slot here was built with a real task above, so a.task and
                # b.task are never None — no need to guard against it.
                who = "same pet" if a.task.pet is b.task.pet else "different pets"
                warnings.append(
                    f"Conflict ({who}): '{a.label}' for {a.task.pet_name} "
                    f"({fmt(a.start_min)}-{fmt(a.end_min)}) overlaps "
                    f"'{b.label}' for {b.task.pet_name} ({fmt(b.start_min)}-{fmt(b.end_min)})."
                )
        return warnings

    def add_commitment(self, start: int, end: int, label: str) -> str:
        """Add a fixed commitment block (start/end are minutes since midnight).

        Returns a warning notice if it overlaps an existing block, or an empty
        string otherwise. Never raises — overlaps are allowed, just flagged.
        """
        block = TimeBlock(label, start, end)
        clashes = [b for b in self.blocks if _overlaps(block, b)]
        self.blocks.append(block)
        if clashes:
            names = ", ".join(f"'{b.label}'" for b in clashes)
            return f"Heads up: '{label}' overlaps {names}."
        return ""

    def remove_block(self, block: TimeBlock) -> None:
        """Remove a block (e.g. a commitment that turned out unnecessary)."""
        # Identity match (TimeBlock is eq=False), so only the exact object goes.
        self.blocks = [b for b in self.blocks if b is not block]

    def move_block(self, block: TimeBlock, new_start: int) -> None:
        """Shift a block to a new start time (minutes since midnight).

        Preserves the block's duration — end_min moves with start_min.
        """
        block.end_min = new_start + block.duration
        block.start_min = new_start

    def clear_plan(self) -> None:
        """Remove generated task placements, keep the owner's commitments.

        A commitment is a TimeBlock with no task; a placed pet task has one.
        Keeps rebuilds idempotent (no stacked duplicate task blocks) and lets a
        day-rollover refresh the plan without wiping what the owner entered.
        """
        self.blocks = [b for b in self.blocks if b.task is None]
        self.unplaced = []

    def free_windows(self) -> list[TimeBlock]:
        """Return the open gaps between commitments available for tasks.

        Walks the day from DAY_START_MIN to DAY_END_MIN, skipping over each
        commitment, and yields the empty stretches in between.
        """
        commitments = sorted(
            (b for b in self.blocks if b.task is None), key=lambda b: b.start_min
        )
        windows: list[TimeBlock] = []
        cursor = DAY_START_MIN
        for c in commitments:
            if c.start_min > cursor:
                windows.append(TimeBlock("free", cursor, c.start_min))
            cursor = max(cursor, c.end_min)
        if cursor < DAY_END_MIN:
            windows.append(TimeBlock("free", cursor, DAY_END_MIN))
        return windows

    def build(self) -> list[TimeBlock]:
        """Retrieve tasks from the owner's pets and place them into free windows.

        Places tasks priority-first (shorter tasks first to break ties). Each
        task aims for a target time: its explicit ``scheduled_time`` if set,
        otherwise a soft time-of-day from its pet's activity level (high-energy
        -> morning, low-energy -> afternoon). Tasks with a target land as close
        to it as a window allows; tasks with no target use best-fit (the
        tightest window that holds them). A ``BUFFER_MIN`` gap is kept between
        placed tasks. Placing a task can split a window. Anything that doesn't
        fit is recorded in ``self.unplaced``. Returns blocks ordered by start.
        """
        self.clear_plan()

        # High priority first; among equal priority, shorter tasks first.
        tasks = sorted(
            self.pending_tasks(),
            key=lambda t: (-PRIORITY_RANK.get(t.priority, 0), t.duration_minutes),
        )

        # Track remaining free time as mutable [start, end] segments.
        windows = [[w.start_min, w.end_min] for w in self.free_windows()]

        for task in tasks:
            dur = task.duration_minutes

            # Target time: explicit scheduled_time wins; otherwise fall back to a
            # soft target from the pet's activity level (may still be None).
            target = to_minutes(task.scheduled_time)
            if target is None and task.pet is not None:
                target = ACTIVITY_TARGET_MIN.get(task.pet.activity_level)

            # Score each window and keep the cheapest. With a target: minimize
            # distance to it, tie-break by tightest window. Without a target:
            # best-fit — smallest fitting window, tie-break earliest.
            best_idx = best_start = best_cost = None
            for i, w in enumerate(windows):
                free = w[1] - w[0]
                if free < dur:
                    continue  # window too small for this task
                if target is None:
                    start, cost = w[0], (free, w[0])
                else:
                    # Clamp the target into the window's placeable range.
                    start = min(max(target, w[0]), w[1] - dur)
                    cost = (abs(start - target), free)
                if best_cost is None or cost < best_cost:
                    best_idx, best_start, best_cost = i, start, cost

            if best_idx is None:
                self.unplaced.append(task)
                continue

            start, end = best_start, best_start + dur
            self.blocks.append(TimeBlock(task.title, start, end, task))
            # Carve [start, end] out of the chosen window, leaving a BUFFER_MIN
            # gap on each side so tasks aren't scheduled back-to-back. Empty or
            # negative leftovers (e.g. at a window edge) are dropped.
            w = windows[best_idx]
            leftovers = [
                seg
                for seg in ([w[0], start - BUFFER_MIN], [end + BUFFER_MIN, w[1]])
                if seg[1] > seg[0]
            ]
            windows[best_idx : best_idx + 1] = leftovers

        self.blocks.sort(key=lambda b: b.start_min)
        return self.blocks

    def explain(self) -> str:
        """Explain the plan: why each task was placed when, and what didn't fit."""
        lines: list[str] = [f"Plan for {self.day.isoformat()}:"]
        for b in sorted(self.blocks, key=lambda b: b.start_min):
            when = f"{fmt(b.start_min)}-{fmt(b.end_min)}"
            if b.task is None:
                lines.append(f"  {when}  {b.label} (commitment)")
            else:
                pet_name = b.task.pet_name
                note = ""
                pref = to_minutes(b.task.scheduled_time)
                if pref is not None and pref != b.start_min:
                    note = f" [wanted {b.task.scheduled_time}]"
                lines.append(
                    f"  {when}  {b.label} for {pet_name} ({b.task.priority} priority){note}"
                )
        if self.unplaced:
            lines.append("")
            lines.append("Couldn't fit (no free time):")
            for t in self.unplaced:
                lines.append(
                    f"  - {t.title} for {t.pet_name} ({t.duration_minutes} min, {t.priority} priority)"
                )
        return "\n".join(lines)


class Owner:
    """The pet owner — owns pets and one schedule."""

    def __init__(self, name: str, day: date) -> None:
        """Create an owner with no pets and a fresh schedule for the given day."""
        self.name: str = name
        self.pets: list[Pet] = []
        self.schedule: Schedule = Schedule(day, self)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        self.pets.append(pet)

    def add_commitment(self, start: int, end: int, label: str) -> str:
        """Add a commitment to the owner's schedule (pass-through).

        Forwards the overlap-warning string from Schedule.add_commitment.
        """
        return self.schedule.add_commitment(start, end, label)

    def remove_commitment(self, block: TimeBlock) -> None:
        """Remove a block from the owner's schedule (pass-through)."""
        self.schedule.remove_block(block)

    def move_commitment(self, block: TimeBlock, new_start: int) -> None:
        """Move a block on the owner's schedule (pass-through)."""
        self.schedule.move_block(block, new_start)

    def check_off(self, task: Task) -> None:
        """Mark one of the owner's tasks as done."""
        task.mark_complete()

    def start_new_day(self) -> None:
        """Roll the schedule forward to the next day.

        Advances the schedule's date and clears the generated plan (the owner's
        commitments are preserved via clear_plan). Completing a recurring task
        already spawned its next-day instance, which becomes eligible once the
        day advances to its due_date.

        A recurring task that was *never* completed isn't duplicated (spawning
        only happens on completion) — but we roll its due_date forward to the new
        day so it stays "today's task" instead of lingering stale-dated in the
        past. You only ever owe the current occurrence, never a backlog.
        """
        self.schedule.day = self.schedule.day + timedelta(days=1)
        for pet in self.pets:
            for task in pet.tasks:
                if (
                    task.recurrence
                    and not task.completed
                    and task.due_date is not None
                    and task.due_date < self.schedule.day
                ):
                    task.due_date = self.schedule.day
        self.schedule.clear_plan()

    def build_day(self) -> list[TimeBlock]:
        """Ask the scheduler to build the day's plan (pass-through).

        The scheduler retrieves the tasks from the pets itself (see
        Schedule.pending_tasks), so the owner just delegates.
        """
        return self.schedule.build()


# ---------------------------------------------------------------------------
# FUTURE EXTENSION (not implemented) — multi-day / calendar scope
# ---------------------------------------------------------------------------
# What: a Calendar that holds many days' worth of commitments and schedules,
#       instead of PawPal+'s current single-day Schedule.
#
# Why it's here: right now a Schedule only models ONE day, so the owner can't
#       add commitments ahead of time (e.g. next Tuesday's vet visit) — a
#       single-day Schedule has nowhere to store future-dated blocks.
#
# Why I thought of it: while designing start_new_day() we noticed that wiping
#       the schedule on rollover would destroy commitments the owner scheduled
#       in advance. We fixed today's case with clear_plan(), but true "plan
#       ahead" support needs commitments to live above a single day. Leaving
#       this stub so the idea isn't lost if I grow PawPal+ into a calendar app.
#
# class Calendar:
#     def __init__(self, owner: "Owner") -> None:
#         self.owner = owner
#         self.schedules: dict[date, Schedule] = {}   # one Schedule per day
#
#     def schedule_for(self, day: date) -> Schedule:
#         """Get (or create) the Schedule for a given day."""
#         ...
#
#     def add_commitment(self, day: date, start: int, end: int, label: str) -> str:
#         """Add a commitment to any day — including future ones."""
#         ...
