"""PawPal+ — core domain classes (skeleton).

Structure mirrors diagrams/uml.mmd. Data-holding types (Task, Pet, TimeBlock)
are dataclasses; behavior-heavy types (Owner, Schedule) are regular classes.
Method bodies are left as stubs — implement the scheduling logic next.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, time


@dataclass
class Task:
    """A single pet care task (e.g. morning walk, feeding)."""

    title: str
    duration_minutes: int
    priority: str  # "low" | "medium" | "high"
    recurring_daily: bool = False
    completed: bool = False

    def mark_done(self) -> None:
        """Flag this task as completed."""
        raise NotImplementedError

    def reset_for_day(self) -> None:
        """Clear completion so a recurring task is ready for a new day."""
        raise NotImplementedError


@dataclass
class Pet:
    """A pet the owner cares for, and the tasks it needs."""

    name: str
    species: str
    breed: str
    activity_level: str  # "low" | "medium" | "high"
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        self.tasks.append(task)
        


@dataclass
class TimeBlock:
    """A span of time on the schedule.

    An empty ``task`` means this is a commitment (work, meetings, etc.) the
    scheduler must plan around. A set ``task`` means it's a pet task the
    scheduler placed into a free window.
    """

    label: str
    start_time: time
    end_time: time
    task: Task | None = None


class Schedule:
    """The owner's day: fixed commitments plus placed pet tasks."""

    def __init__(self, day: date) -> None:
        self.day: date = day
        self.blocks: list[TimeBlock] = []
        self.unplaced: list[Task] = []  # tasks that didn't fit after build()

    def add_commitment(self, start: time, end: time, label: str) -> str:
        """Add a fixed commitment block.

        Returns a warning notice if it overlaps an existing block, or an empty
        string otherwise. Never raises — overlaps are allowed, just flagged.
        """
        raise NotImplementedError

    def remove_block(self, block: TimeBlock) -> None:
        """Remove a block (e.g. a commitment that turned out unnecessary)."""
        raise NotImplementedError

    def move_block(self, block: TimeBlock, new_start: time) -> None:
        """Shift a flexible block to a new start time."""
        raise NotImplementedError

    def build(self) -> list[TimeBlock]:
        """Place pet tasks (priority-first) into free windows around commitments.

        Tasks that don't fit are recorded in ``self.unplaced``. Returns the
        ordered list of blocks making up the day's plan.
        """
        raise NotImplementedError

    def free_windows(self) -> list[TimeBlock]:
        """Return the open gaps between commitments available for tasks."""
        raise NotImplementedError

    def explain(self) -> str:
        """Explain the plan: why each task was placed when, and what didn't fit."""
        raise NotImplementedError


class Owner:
    """The pet owner — owns pets and one schedule."""

    def __init__(self, name: str, day: date) -> None:
        self.name: str = name
        self.pets: list[Pet] = []
        self.schedule: Schedule = Schedule(day)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        raise NotImplementedError

    def add_commitment(self, start: time, end: time, label: str) -> str:
        """Add a commitment to the owner's schedule (pass-through).

        Forwards the overlap-warning string from Schedule.add_commitment.
        """
        return self.schedule.add_commitment(start, end, label)

    def check_off(self, task: Task) -> None:
        """Mark one of the owner's tasks as done."""
        raise NotImplementedError
