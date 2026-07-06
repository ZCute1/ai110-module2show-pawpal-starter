"""PawPal+ — core domain classes.

Data-holding types (Task, Pet, TimeBlock) are dataclasses; behavior-heavy types
(Owner, Schedule) are regular classes. The Schedule is the "brain": it retrieves
tasks from the owner's pets and places them around fixed commitments.

Times are stored as minutes since midnight (e.g. 9:30am = 570); use fmt() to
display them as "HH:MM".
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date

# Higher number = higher priority, so build() can sort tasks descending by rank.
PRIORITY_RANK = {"high": 2, "medium": 1, "low": 0}

# The daily window the scheduler is allowed to place tasks in (06:00–22:00).
DAY_START_MIN = 6 * 60
DAY_END_MIN = 22 * 60


def fmt(minutes: int) -> str:
    """Format minutes-since-midnight as 'HH:MM' (e.g. 570 -> '09:30')."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@dataclass
class Task:
    """A single pet care task (e.g. morning walk, feeding)."""

    title: str
    duration_minutes: int
    priority: str  # "low" | "medium" | "high"
    recurring_daily: bool = False
    completed: bool = False
    # Which pet this task belongs to. Set by Pet.add_task; kept out of init/repr/eq
    # so it doesn't need to be passed in and can't cause a Pet<->Task repr loop.
    pet: Pet | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Normalize priority to lowercase so casing never affects ranking."""
        self.priority = self.priority.lower()

    def mark_complete(self) -> None:
        """Flag this task as completed."""
        self.completed = True

    def reset_for_day(self) -> None:
        """Clear completion so a recurring task is ready for a new day."""
        self.completed = False


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

    def pending_tasks(self) -> list[Task]:
        """Retrieve every incomplete task across all of the owner's pets.

        This is the scheduler acting as the 'brain': it reaches through the owner
        to gather tasks itself, rather than being handed a ready-made list.
        """
        return [task for pet in self.owner.pets for task in pet.tasks if not task.completed]

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

        Places tasks priority-first (shorter tasks first to break ties, so more
        fit), using earliest-fit placement into the free gaps around commitments.
        Anything that doesn't fit is recorded in ``self.unplaced``. Returns the
        day's blocks ordered by start time.
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
            placed = False
            for w in windows:
                if w[1] - w[0] >= task.duration_minutes:
                    start = w[0]
                    end = start + task.duration_minutes
                    self.blocks.append(TimeBlock(task.title, start, end, task))
                    w[0] = end  # shrink the window from the front
                    placed = True
                    break
            if not placed:
                self.unplaced.append(task)

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
                pet_name = b.task.pet.name if b.task.pet else "unassigned"
                lines.append(
                    f"  {when}  {b.label} for {pet_name} ({b.task.priority} priority)"
                )
        if self.unplaced:
            lines.append("")
            lines.append("Couldn't fit (no free time):")
            for t in self.unplaced:
                pet_name = t.pet.name if t.pet else "unassigned"
                lines.append(
                    f"  - {t.title} for {pet_name} ({t.duration_minutes} min, {t.priority} priority)"
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
        """Roll over to a new day.

        Resets recurring tasks so they reappear, and clears only the generated
        plan (commitments the owner entered are preserved via clear_plan).
        """
        for pet in self.pets:
            for task in pet.tasks:
                if task.recurring_daily:
                    task.reset_for_day()
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
