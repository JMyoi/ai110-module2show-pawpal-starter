"""
PawPal+ Pet Care Management System
Classes for managing pet care tasks, scheduling, and daily planning.
"""

from dataclasses import dataclass, field
from datetime import date, time, timedelta, datetime
from enum import Enum


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class Priority(Enum):
    """Task priority levels, integer values enable sorting."""
    HIGH = 3
    MEDIUM = 2
    LOW = 1


class TaskCategory(Enum):
    """Categories of pet care activities."""
    MEDICATION = "Medication"
    FEEDING = "Feeding"
    WALK = "Walk"
    GROOMING = "Grooming"
    ENRICHMENT = "Enrichment"
    APPOINTMENT = "Appointment"
    OTHER = "Other"


# Category scheduling order (lower = scheduled earlier among same priority)
CATEGORY_ORDER = {
    TaskCategory.MEDICATION: 0,
    TaskCategory.FEEDING: 1,
    TaskCategory.WALK: 2,
    TaskCategory.APPOINTMENT: 3,
    TaskCategory.GROOMING: 4,
    TaskCategory.ENRICHMENT: 5,
    TaskCategory.OTHER: 6,
}


# ──────────────────────────────────────────────
# Core Data Classes
# ──────────────────────────────────────────────

@dataclass
class Task:
    """A pet care task request (input to the scheduler)."""
    title: str
    duration_minutes: int
    priority: Priority
    category: TaskCategory = TaskCategory.OTHER
    pet_name: str = ""
    preferred_time: time | None = None
    is_completed: bool = False

    def mark_complete(self) -> None:
        self.is_completed = True

    def __str__(self) -> str:
        time_str = f" @ {self.preferred_time.strftime('%H:%M')}" if self.preferred_time else ""
        status = " [DONE]" if self.is_completed else ""
        return f"{self.title} ({self.duration_minutes} min, {self.priority.name}){time_str}{status}"


@dataclass
class Pet:
    """A pet with its associated care tasks."""
    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        task.pet_name = self.name
        self.tasks.append(task)

    def remove_task(self, task_title: str) -> bool:
        for i, t in enumerate(self.tasks):
            if t.title == task_title:
                self.tasks.pop(i)
                return True
        return False

    def get_tasks_by_priority(self, priority: Priority) -> list[Task]:
        return [t for t in self.tasks if t.priority == priority]

    def get_tasks_by_category(self, category: TaskCategory) -> list[Task]:
        return [t for t in self.tasks if t.category == category]

    def get_tasks_by_status(self, completed: bool) -> list[Task]:
        return [t for t in self.tasks if t.is_completed == completed]


@dataclass
class Owner:
    """A pet owner with time constraints and preferences."""
    name: str
    available_minutes: int = 120
    preferred_start_time: time = field(default_factory=lambda: time(8, 0))
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> bool:
        for i, p in enumerate(self.pets):
            if p.name == pet_name:
                self.pets.pop(i)
                return True
        return False

    def get_all_tasks(self, pet_name: str | None = None, completed: bool | None = None) -> list[Task]:
        tasks = [task for pet in self.pets for task in pet.tasks]
        if pet_name is not None:
            tasks = [t for t in tasks if t.pet_name == pet_name]
        if completed is not None:
            tasks = [t for t in tasks if t.is_completed == completed]
        return tasks


# ──────────────────────────────────────────────
# Output Classes
# ──────────────────────────────────────────────

@dataclass
class ScheduledTask:
    """A task that has been assigned a time slot by the scheduler."""
    task: Task
    start_time: time
    end_time: time
    reason: str

    def __str__(self) -> str:
        return (
            f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')} "
            f"{self.task.title} ({self.task.pet_name}) — {self.reason}"
        )


@dataclass
class DailyPlan:
    """The complete daily schedule produced by the scheduler."""
    owner_name: str
    date: date
    scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
    skipped_tasks: list[tuple[Task, str]] = field(default_factory=list)
    total_scheduled_minutes: int = 0
    total_available_minutes: int = 0

    def get_summary(self) -> str:
        lines = [
            f"Daily Plan for {self.owner_name} — {self.date.strftime('%A, %B %d, %Y')}",
            f"Time budget: {self.total_scheduled_minutes}/{self.total_available_minutes} min "
            f"({self.get_utilization():.0f}% utilized)",
            "",
            "Scheduled Tasks:",
            "─" * 50,
        ]
        if not self.scheduled_tasks:
            lines.append("  (no tasks scheduled)")
        for i, st in enumerate(self.scheduled_tasks, 1):
            lines.append(f"  {i}. {st}")

        if self.skipped_tasks:
            lines.append("")
            lines.append("Skipped Tasks:")
            lines.append("─" * 50)
            for task, reason in self.skipped_tasks:
                lines.append(f"  ✗ {task} — {reason}")

        return "\n".join(lines)

    def get_utilization(self) -> float:
        if self.total_available_minutes == 0:
            return 0.0
        return (self.total_scheduled_minutes / self.total_available_minutes) * 100


# ──────────────────────────────────────────────
# Scheduler
# ──────────────────────────────────────────────

class Scheduler:
    """Stateless scheduler that produces a DailyPlan from an Owner's data."""

    def generate_plan(self, owner: Owner) -> DailyPlan:
        all_tasks = [t for t in owner.get_all_tasks() if not t.is_completed]
        sorted_tasks = self._sort_tasks(all_tasks)

        scheduled = []
        skipped = []
        remaining_minutes = owner.available_minutes
        current_time = owner.preferred_start_time

        for position, task in enumerate(sorted_tasks):
            if self._fits_in_budget(task, remaining_minutes):
                st = self._assign_time(task, current_time, position, remaining_minutes)
                scheduled.append(st)
                remaining_minutes -= task.duration_minutes
                current_time = st.end_time
            else:
                reason = (
                    f"Not enough time remaining "
                    f"({task.duration_minutes} min needed, {remaining_minutes} min left)"
                )
                skipped.append((task, reason))

        total_scheduled = sum(st.task.duration_minutes for st in scheduled)

        return DailyPlan(
            owner_name=owner.name,
            date=date.today(),
            scheduled_tasks=scheduled,
            skipped_tasks=skipped,
            total_scheduled_minutes=total_scheduled,
            total_available_minutes=owner.available_minutes,
        )

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        return sorted(
            tasks,
            key=lambda t: (
                -t.priority.value,                                          # HIGH (3) first
                CATEGORY_ORDER.get(t.category, 6),                         # MEDICATION before WALK, etc.
                (0, t.preferred_time) if t.preferred_time else (1, time(0, 0)),  # timed tasks before untimed
                t.duration_minutes,                                         # shorter tasks first among equals
            ),
        )

    def _fits_in_budget(self, task: Task, remaining_minutes: int) -> bool:
        return task.duration_minutes <= remaining_minutes

    def _assign_time(self, task: Task, current_time: time, position: int, remaining_minutes: int) -> ScheduledTask:
        # Honor preferred_time if set and still in the future relative to current_time
        if task.preferred_time and task.preferred_time >= current_time:
            start_time = task.preferred_time
        else:
            start_time = current_time
        start_dt = datetime.combine(date.today(), start_time)
        end_dt = start_dt + timedelta(minutes=task.duration_minutes)
        reason = self._build_reason(task, position, remaining_minutes, used_preferred=start_time == task.preferred_time)
        return ScheduledTask(
            task=task,
            start_time=start_time,
            end_time=end_dt.time(),
            reason=reason,
        )

    def _build_reason(self, task: Task, position: int, remaining_minutes: int, used_preferred: bool = False) -> str:
        parts = []
        if task.priority == Priority.HIGH:
            parts.append("High priority — scheduled first")
        elif task.priority == Priority.MEDIUM:
            parts.append("Medium priority")
        else:
            parts.append("Low priority — fits remaining time")

        if task.category != TaskCategory.OTHER:
            parts.append(f"{task.category.value} task")

        if used_preferred and task.preferred_time:
            parts.append(f"Preferred time: {task.preferred_time.strftime('%H:%M')}")
        elif task.preferred_time:
            parts.append(f"Preferred time {task.preferred_time.strftime('%H:%M')} passed — scheduled next")

        if position == 0:
            parts.append("first in schedule")

        return ", ".join(parts)
