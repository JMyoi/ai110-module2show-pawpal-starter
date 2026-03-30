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
