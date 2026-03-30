"""Tests for the PawPal+ scheduling system."""

import pytest
from datetime import time, date

from pawpal_system import (
    Priority, TaskCategory, Task, Pet, Owner,
    ScheduledTask, DailyPlan, Scheduler,
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def scheduler():
    return Scheduler()


@pytest.fixture
def sample_owner():
    owner = Owner(name="Jordan", available_minutes=60, preferred_start_time=time(8, 0))
    dog = Pet(name="Mochi", species="dog", age=3)
    dog.add_task(Task("Morning Walk", 30, Priority.HIGH, TaskCategory.WALK))
    dog.add_task(Task("Give Medication", 5, Priority.HIGH, TaskCategory.MEDICATION))
    dog.add_task(Task("Brush Fur", 15, Priority.LOW, TaskCategory.GROOMING))
    dog.add_task(Task("Puzzle Toy", 20, Priority.LOW, TaskCategory.ENRICHMENT))
    owner.add_pet(dog)
    return owner


# ──────────────────────────────────────────────
# Priority ordering
# ──────────────────────────────────────────────

def test_high_priority_scheduled_before_low(scheduler, sample_owner):
    plan = scheduler.generate_plan(sample_owner)
    scheduled_priorities = [st.task.priority for st in plan.scheduled_tasks]
    # HIGH tasks should come before LOW tasks
    high_indices = [i for i, p in enumerate(scheduled_priorities) if p == Priority.HIGH]
    low_indices = [i for i, p in enumerate(scheduled_priorities) if p == Priority.LOW]
    if high_indices and low_indices:
        assert max(high_indices) < min(low_indices)


def test_medication_before_walk_at_same_priority(scheduler):
    owner = Owner(name="Test", available_minutes=60)
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH, TaskCategory.WALK))
    pet.add_task(Task("Meds", 5, Priority.HIGH, TaskCategory.MEDICATION))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    titles = [st.task.title for st in plan.scheduled_tasks]
    assert titles.index("Meds") < titles.index("Walk")


# ──────────────────────────────────────────────
# Time budget
# ──────────────────────────────────────────────

def test_time_budget_respected(scheduler, sample_owner):
    plan = scheduler.generate_plan(sample_owner)
    assert plan.total_scheduled_minutes <= sample_owner.available_minutes


def test_tasks_skipped_when_budget_exceeded(scheduler):
    owner = Owner(name="Test", available_minutes=30)
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Long Walk", 25, Priority.HIGH, TaskCategory.WALK))
    pet.add_task(Task("Training", 20, Priority.MEDIUM, TaskCategory.ENRICHMENT))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert len(plan.skipped_tasks) == 1
    assert plan.skipped_tasks[0][0].title == "Training"


def test_all_tasks_fit_when_budget_large(scheduler, sample_owner):
    sample_owner.available_minutes = 500
    plan = scheduler.generate_plan(sample_owner)
    assert len(plan.skipped_tasks) == 0
    assert len(plan.scheduled_tasks) == 4


# ──────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────

def test_empty_tasks_produce_empty_plan(scheduler):
    owner = Owner(name="Test", available_minutes=60)
    plan = scheduler.generate_plan(owner)
    assert plan.scheduled_tasks == []
    assert plan.skipped_tasks == []
    assert plan.total_scheduled_minutes == 0


def test_zero_budget_skips_all_tasks(scheduler):
    owner = Owner(name="Test", available_minutes=0)
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH, TaskCategory.WALK))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert len(plan.scheduled_tasks) == 0
    assert len(plan.skipped_tasks) == 1


# ──────────────────────────────────────────────
# Time assignments
# ──────────────────────────────────────────────

def test_times_are_sequential_and_non_overlapping(scheduler, sample_owner):
    sample_owner.available_minutes = 500
    plan = scheduler.generate_plan(sample_owner)
    for i in range(1, len(plan.scheduled_tasks)):
        prev_end = plan.scheduled_tasks[i - 1].end_time
        curr_start = plan.scheduled_tasks[i].start_time
        assert curr_start >= prev_end


def test_first_task_starts_at_preferred_time(scheduler, sample_owner):
    sample_owner.available_minutes = 500
    plan = scheduler.generate_plan(sample_owner)
    assert plan.scheduled_tasks[0].start_time == sample_owner.preferred_start_time


# ──────────────────────────────────────────────
# Reasoning
# ──────────────────────────────────────────────

def test_reason_strings_are_populated(scheduler, sample_owner):
    plan = scheduler.generate_plan(sample_owner)
    for st in plan.scheduled_tasks:
        assert st.reason != ""
        assert len(st.reason) > 5


def test_skipped_tasks_include_explanation(scheduler):
    owner = Owner(name="Test", available_minutes=10)
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Long Walk", 30, Priority.HIGH, TaskCategory.WALK))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert len(plan.skipped_tasks) == 1
    _, reason = plan.skipped_tasks[0]
    assert "30 min needed" in reason
    assert "10 min left" in reason


# ──────────────────────────────────────────────
# Multi-pet interleaving
# ──────────────────────────────────────────────

def test_multi_pet_tasks_sorted_by_priority_not_pet(scheduler):
    owner = Owner(name="Test", available_minutes=120)
    dog = Pet(name="Mochi", species="dog")
    dog.add_task(Task("Dog Walk", 20, Priority.LOW, TaskCategory.WALK))
    cat = Pet(name="Milo", species="cat")
    cat.add_task(Task("Cat Meds", 5, Priority.HIGH, TaskCategory.MEDICATION))
    owner.add_pet(dog)
    owner.add_pet(cat)

    plan = scheduler.generate_plan(owner)
    titles = [st.task.title for st in plan.scheduled_tasks]
    assert titles[0] == "Cat Meds"  # HIGH priority first, regardless of pet


# ──────────────────────────────────────────────
# DailyPlan methods
# ──────────────────────────────────────────────

def test_utilization_calculation(scheduler, sample_owner):
    plan = scheduler.generate_plan(sample_owner)
    expected = (plan.total_scheduled_minutes / sample_owner.available_minutes) * 100
    assert plan.get_utilization() == pytest.approx(expected)


def test_utilization_zero_when_no_budget():
    plan = DailyPlan(owner_name="Test", date=date.today(), total_available_minutes=0)
    assert plan.get_utilization() == 0.0


def test_summary_contains_key_info(scheduler, sample_owner):
    plan = scheduler.generate_plan(sample_owner)
    summary = plan.get_summary()
    assert "Jordan" in summary
    assert "Scheduled Tasks" in summary


# ──────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────

def test_pet_add_task_sets_pet_name():
    pet = Pet(name="Luna", species="dog")
    task = Task("Walk", 20, Priority.HIGH)
    pet.add_task(task)
    assert task.pet_name == "Luna"


def test_pet_remove_task():
    pet = Pet(name="Luna", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH))
    assert pet.remove_task("Walk") is True
    assert pet.remove_task("Walk") is False
    assert len(pet.tasks) == 0


def test_owner_remove_pet():
    owner = Owner(name="Test")
    owner.add_pet(Pet(name="Luna", species="dog"))
    assert owner.remove_pet("Luna") is True
    assert owner.remove_pet("Luna") is False
    assert len(owner.pets) == 0


# ──────────────────────────────────────────────
# Feature 2: Filtering by Pet & Completion Status
# ──────────────────────────────────────────────

def test_task_default_not_completed():
    task = Task("Walk", 20, Priority.HIGH)
    assert task.is_completed is False


def test_mark_complete():
    task = Task("Walk", 20, Priority.HIGH)
    task.mark_complete()
    assert task.is_completed is True


def test_pet_get_tasks_by_status():
    pet = Pet(name="Luna", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH))
    pet.add_task(Task("Feed", 10, Priority.MEDIUM))
    pet.add_task(Task("Groom", 15, Priority.LOW))
    pet.tasks[0].mark_complete()

    assert len(pet.get_tasks_by_status(completed=True)) == 1
    assert len(pet.get_tasks_by_status(completed=False)) == 2
    assert pet.get_tasks_by_status(completed=True)[0].title == "Walk"


def test_owner_filter_by_pet():
    owner = Owner(name="Test")
    dog = Pet(name="Mochi", species="dog")
    dog.add_task(Task("Walk", 20, Priority.HIGH))
    cat = Pet(name="Milo", species="cat")
    cat.add_task(Task("Feed Milo", 10, Priority.MEDIUM))
    owner.add_pet(dog)
    owner.add_pet(cat)

    mochi_tasks = owner.get_all_tasks(pet_name="Mochi")
    assert len(mochi_tasks) == 1
    assert mochi_tasks[0].title == "Walk"

    milo_tasks = owner.get_all_tasks(pet_name="Milo")
    assert len(milo_tasks) == 1
    assert milo_tasks[0].title == "Feed Milo"


def test_owner_filter_by_completed():
    owner = Owner(name="Test")
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH))
    pet.add_task(Task("Feed", 10, Priority.MEDIUM))
    owner.add_pet(pet)
    owner.get_all_tasks()[0].mark_complete()

    assert len(owner.get_all_tasks(completed=True)) == 1
    assert len(owner.get_all_tasks(completed=False)) == 1


def test_owner_no_filter_backward_compatible():
    owner = Owner(name="Test")
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH))
    pet.add_task(Task("Feed", 10, Priority.MEDIUM))
    owner.add_pet(pet)

    assert len(owner.get_all_tasks()) == 2


# ──────────────────────────────────────────────
# Feature 1: Preferred Time
# ──────────────────────────────────────────────

def test_task_with_preferred_time_str():
    task = Task("Morning Walk", 30, Priority.HIGH, preferred_time=time(9, 0))
    assert "@ 09:00" in str(task)


def test_task_without_preferred_time_str():
    task = Task("Morning Walk", 30, Priority.HIGH)
    assert "@" not in str(task)


def test_sort_earlier_preferred_time_first(scheduler):
    owner = Owner(name="Test", available_minutes=120)
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Late Walk", 20, Priority.HIGH, TaskCategory.WALK, preferred_time=time(10, 0)))
    pet.add_task(Task("Early Walk", 20, Priority.HIGH, TaskCategory.WALK, preferred_time=time(9, 0)))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    titles = [st.task.title for st in plan.scheduled_tasks]
    assert titles.index("Early Walk") < titles.index("Late Walk")


def test_task_without_preferred_time_sorts_after(scheduler):
    owner = Owner(name="Test", available_minutes=120)
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Untimed Walk", 20, Priority.HIGH, TaskCategory.WALK))
    pet.add_task(Task("Timed Walk", 20, Priority.HIGH, TaskCategory.WALK, preferred_time=time(9, 0)))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    titles = [st.task.title for st in plan.scheduled_tasks]
    assert titles.index("Timed Walk") < titles.index("Untimed Walk")


def test_assign_time_uses_preferred_time(scheduler):
    owner = Owner(name="Test", available_minutes=120, preferred_start_time=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Late Feed", 10, Priority.HIGH, preferred_time=time(10, 0)))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert plan.scheduled_tasks[0].start_time == time(10, 0)


def test_preferred_time_in_past_falls_back(scheduler):
    owner = Owner(name="Test", available_minutes=120, preferred_start_time=time(11, 0))
    pet = Pet(name="Rex", species="dog")
    # preferred_time 9:00 is before start_time 11:00 — should fall back
    pet.add_task(Task("Early Walk", 20, Priority.HIGH, preferred_time=time(9, 0)))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert plan.scheduled_tasks[0].start_time == time(11, 0)


def test_preferred_time_in_reason(scheduler):
    owner = Owner(name="Test", available_minutes=120, preferred_start_time=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH, preferred_time=time(9, 0)))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert "09:00" in plan.scheduled_tasks[0].reason


def test_completed_tasks_not_scheduled(scheduler):
    owner = Owner(name="Test", available_minutes=120)
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH))
    pet.add_task(Task("Feed", 10, Priority.MEDIUM))
    owner.add_pet(pet)
    pet.tasks[0].mark_complete()

    plan = scheduler.generate_plan(owner)
    scheduled_titles = [st.task.title for st in plan.scheduled_tasks]
    assert "Walk" not in scheduled_titles
    assert "Feed" in scheduled_titles


# ──────────────────────────────────────────────
# Feature 3: Recurring Tasks
# ──────────────────────────────────────────────

def test_task_default_no_recurrence():
    task = Task("Walk", 20, Priority.HIGH)
    assert task.recurrence is None


def test_complete_non_recurring():
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH))
    result = pet.complete_task("Walk")
    assert result is None
    assert pet.tasks[0].is_completed is True


def test_complete_daily_creates_new():
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH, recurrence="daily"))
    new_task = pet.complete_task("Walk")
    assert new_task is not None
    assert len(pet.tasks) == 2
    assert pet.tasks[0].is_completed is True
    assert new_task.is_completed is False
    assert new_task.recurrence == "daily"


def test_complete_weekly_creates_new():
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Grooming", 30, Priority.LOW, TaskCategory.GROOMING, recurrence="weekly"))
    new_task = pet.complete_task("Grooming")
    assert new_task is not None
    assert new_task.recurrence == "weekly"
    assert new_task.is_completed is False


def test_new_recurring_task_is_independent():
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH, recurrence="daily"))
    new_task = pet.complete_task("Walk")
    # Old and new are separate objects
    assert pet.tasks[0] is not new_task
    assert pet.tasks[0].is_completed is True
    assert new_task.is_completed is False


def test_complete_task_not_found():
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH))
    result = pet.complete_task("Nonexistent Task")
    assert result is None
    assert pet.tasks[0].is_completed is False


def test_completed_recurring_not_rescheduled(scheduler):
    owner = Owner(name="Test", available_minutes=120)
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH, recurrence="daily"))
    owner.add_pet(pet)
    # Complete the original — creates a new recurring copy
    pet.complete_task("Walk")
    assert len(pet.tasks) == 2

    plan = scheduler.generate_plan(owner)
    scheduled_titles = [st.task.title for st in plan.scheduled_tasks]
    # Exactly one Walk in the schedule (the new copy, not the completed original)
    assert scheduled_titles.count("Walk") == 1


# ──────────────────────────────────────────────
# Feature 4: Conflict Detection
# ──────────────────────────────────────────────

def test_no_conflicts_sequential(scheduler):
    """Normal plan with no preferred times produces no warnings."""
    owner = Owner(name="Test", available_minutes=120, preferred_start_time=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 20, Priority.HIGH, TaskCategory.WALK))
    pet.add_task(Task("Feed", 10, Priority.MEDIUM, TaskCategory.FEEDING))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert plan.warnings == []


def test_conflict_detected_same_preferred_time(scheduler):
    """Two tasks with the same preferred time produce a conflict warning."""
    owner = Owner(name="Test", available_minutes=120, preferred_start_time=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 30, Priority.HIGH, TaskCategory.WALK, preferred_time=time(9, 0)))
    pet.add_task(Task("Meds", 30, Priority.HIGH, TaskCategory.MEDICATION, preferred_time=time(9, 0)))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert len(plan.warnings) >= 1


def test_conflict_message_has_task_names(scheduler):
    """Conflict warning contains both task titles."""
    owner = Owner(name="Test", available_minutes=120, preferred_start_time=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 30, Priority.HIGH, TaskCategory.WALK, preferred_time=time(9, 0)))
    pet.add_task(Task("Meds", 30, Priority.HIGH, TaskCategory.MEDICATION, preferred_time=time(9, 0)))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert any("Walk" in w and "Meds" in w for w in plan.warnings)


def test_conflict_message_has_times(scheduler):
    """Conflict warning contains the time ranges of the conflicting tasks."""
    owner = Owner(name="Test", available_minutes=120, preferred_start_time=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 30, Priority.HIGH, TaskCategory.WALK, preferred_time=time(9, 0)))
    pet.add_task(Task("Meds", 30, Priority.HIGH, TaskCategory.MEDICATION, preferred_time=time(9, 0)))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert any("09:00" in w for w in plan.warnings)


def test_multiple_conflicts_all_reported(scheduler):
    """Three tasks at the same slot produce 3 pairwise warnings."""
    owner = Owner(name="Test", available_minutes=240, preferred_start_time=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 30, Priority.HIGH, TaskCategory.WALK, preferred_time=time(9, 0)))
    pet.add_task(Task("Meds", 30, Priority.HIGH, TaskCategory.MEDICATION, preferred_time=time(9, 0)))
    pet.add_task(Task("Feed", 30, Priority.HIGH, TaskCategory.FEEDING, preferred_time=time(9, 0)))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert len(plan.warnings) == 3


def test_no_crash_on_conflict(scheduler):
    """Plan is still generated and tasks still scheduled even with conflicts."""
    owner = Owner(name="Test", available_minutes=120, preferred_start_time=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    pet.add_task(Task("Walk", 30, Priority.HIGH, TaskCategory.WALK, preferred_time=time(9, 0)))
    pet.add_task(Task("Meds", 30, Priority.HIGH, TaskCategory.MEDICATION, preferred_time=time(9, 0)))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert len(plan.scheduled_tasks) == 2
    assert plan.warnings  # warnings exist but no crash


def test_adjacent_tasks_no_conflict(scheduler):
    """A task ending at 9:30 and one starting at 9:30 do NOT overlap."""
    owner = Owner(name="Test", available_minutes=120, preferred_start_time=time(9, 0))
    pet = Pet(name="Rex", species="dog")
    # First task: 9:00–9:30 (sequential, no preferred time)
    # Second task: preferred 9:30 (starts exactly when first ends)
    pet.add_task(Task("Walk", 30, Priority.HIGH, TaskCategory.WALK))
    pet.add_task(Task("Feed", 15, Priority.HIGH, TaskCategory.FEEDING, preferred_time=time(9, 30)))
    owner.add_pet(pet)

    plan = scheduler.generate_plan(owner)
    assert plan.warnings == []
