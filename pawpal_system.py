"""PawPal+ core classes: owners, pets, care tasks, and the daily scheduler.

Mirrors the design in diagrams/uml.mmd.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from enum import Enum


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


PRIORITY_SCORES = {Priority.LOW: 1, Priority.MEDIUM: 2, Priority.HIGH: 3}

# Order used to place chosen tasks through the day; "" means no preference.
TIME_SLOTS = {"morning": 0, "afternoon": 1, "evening": 2, "": 3}

# Earliest start time for tasks with a preferred time of day.
SLOT_STARTS = {"afternoon": "12:00", "evening": "17:00"}


def _to_minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def _to_hhmm(total: int) -> str:
    return f"{total // 60:02d}:{total % 60:02d}"


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    category: str = ""
    preferred_time: str = ""
    completed: bool = False

    def __post_init__(self) -> None:
        # Accept plain strings like "high" so UI input can be passed straight in.
        if isinstance(self.priority, str):
            self.priority = Priority(self.priority.lower())
        self.preferred_time = self.preferred_time.lower()
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if self.preferred_time not in TIME_SLOTS:
            raise ValueError(f"preferred_time must be one of {list(TIME_SLOTS)}")

    def update(self, changes: dict) -> None:
        allowed = {f.name for f in fields(self)}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unknown task fields: {sorted(unknown)}")
        for name, value in changes.items():
            setattr(self, name, value)
        self.__post_init__()

    def mark_complete(self) -> None:
        self.completed = True

    def priority_score(self) -> int:
        return PRIORITY_SCORES[self.priority]


@dataclass
class Pet:
    name: str
    species: str
    age: int = 0
    notes: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def _find_task(self, title: str) -> Task:
        for task in self.tasks:
            if task.title == title:
                return task
        raise KeyError(f"{self.name} has no task titled {title!r}")

    def edit_task(self, title: str, changes: dict) -> None:
        self._find_task(title).update(changes)

    def remove_task(self, title: str) -> None:
        self.tasks.remove(self._find_task(title))


@dataclass
class Owner:
    name: str
    available_minutes: int
    day_start: str = "08:00"
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        self.pets.append(pet)

    def remove_pet(self, name: str) -> None:
        self.pets.remove(self.get_pet(name))

    def get_pet(self, name: str) -> Pet:
        for pet in self.pets:
            if pet.name == name:
                return pet
        raise KeyError(f"{self.name} has no pet named {name!r}")

    def all_tasks(self) -> list[Task]:
        return [task for pet in self.pets for task in pet.tasks]


@dataclass
class ScheduledTask:
    task: Task
    pet: Pet
    start_time: str
    end_time: str
    reason: str


@dataclass
class DailyPlan:
    scheduled: list[ScheduledTask] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    total_minutes: int = 0
    skip_reasons: dict[str, str] = field(default_factory=dict)

    def add(self, item: ScheduledTask) -> None:
        self.scheduled.append(item)
        self.total_minutes += item.task.duration_minutes

    def skip(self, task: Task, reason: str) -> None:
        self.skipped.append(task)
        self.skip_reasons[task.title] = reason

    def explain(self) -> str:
        if not self.scheduled and not self.skipped:
            return "No tasks to schedule."
        lines = [f"Planned {len(self.scheduled)} task(s), {self.total_minutes} minutes total."]
        for item in self.scheduled:
            lines.append(
                f"- {item.start_time}-{item.end_time} {item.task.title} ({item.pet.name}): {item.reason}"
            )
        for task in self.skipped:
            lines.append(f"- Skipped {task.title}: {self.skip_reasons[task.title]}")
        return "\n".join(lines)

    def to_table(self) -> list[dict]:
        return [
            {
                "start": item.start_time,
                "end": item.end_time,
                "pet": item.pet.name,
                "task": item.task.title,
                "duration_minutes": item.task.duration_minutes,
                "priority": item.task.priority.value,
                "reason": item.reason,
            }
            for item in self.scheduled
        ]


class Scheduler:
    """Builds a DailyPlan by picking the most important tasks that fit the owner's time."""

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def generate_plan(self) -> DailyPlan:
        plan = DailyPlan()
        pet_for = {id(task): pet for pet in self.owner.pets for task in pet.tasks}
        pending = [task for task in self.owner.all_tasks() if not task.completed]

        # Pick tasks in priority order until time runs out.
        chosen: list[Task] = []
        remaining = self.owner.available_minutes
        for task in self._sort_tasks(pending):
            if self._fits_in_time(task, remaining):
                chosen.append(task)
                remaining -= task.duration_minutes
            else:
                plan.skip(
                    task,
                    f"needs {task.duration_minutes} min but only {remaining} min left",
                )

        # Lay the chosen tasks out through the day, honoring preferred times.
        chosen.sort(key=lambda t: TIME_SLOTS[t.preferred_time])
        clock = _to_minutes(self.owner.day_start)
        for task in chosen:
            if task.preferred_time in SLOT_STARTS:
                clock = max(clock, _to_minutes(SLOT_STARTS[task.preferred_time]))
            end = clock + task.duration_minutes
            plan.add(
                ScheduledTask(
                    task=task,
                    pet=pet_for[id(task)],
                    start_time=_to_hhmm(clock),
                    end_time=_to_hhmm(end),
                    reason=self._reason(task),
                )
            )
            clock = end
        return plan

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        # Highest priority first; owner preferences break ties; then shorter tasks first.
        return sorted(
            tasks,
            key=lambda t: (
                -t.priority_score(),
                t.category not in self.owner.preferences,
                t.duration_minutes,
            ),
        )

    def _fits_in_time(self, task: Task, remaining: int) -> bool:
        return task.duration_minutes <= remaining

    def _reason(self, task: Task) -> str:
        parts = [f"{task.priority.value} priority"]
        if task.category and task.category in self.owner.preferences:
            parts.append(f"owner prefers {task.category}")
        if task.preferred_time:
            parts.append(f"scheduled in the {task.preferred_time}")
        return ", ".join(parts)
