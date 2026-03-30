"""
PawPal+ CLI Demo
Run this script to verify the backend logic before connecting to Streamlit.
Usage: python demo.py
"""

from datetime import time
from pawpal_system import (
    Priority, TaskCategory, Task, Pet, Owner, Scheduler,
)


def main():
    # ── Create owner ──
    owner = Owner(
        name="Jordan",
        available_minutes=90,
        preferred_start_time=time(8, 0),
    )

    # ── Create pets and tasks ──
    mochi = Pet(name="Mochi", species="dog", age=3)
    mochi.add_task(Task("Morning Walk", 30, Priority.HIGH, TaskCategory.WALK))
    mochi.add_task(Task("Give Heartworm Meds", 5, Priority.HIGH, TaskCategory.MEDICATION))
    mochi.add_task(Task("Breakfast", 10, Priority.MEDIUM, TaskCategory.FEEDING))
    mochi.add_task(Task("Brush Fur", 15, Priority.LOW, TaskCategory.GROOMING))
    mochi.add_task(Task("Puzzle Toy", 20, Priority.LOW, TaskCategory.ENRICHMENT))

    milo = Pet(name="Milo", species="cat", age=5)
    milo.add_task(Task("Feed Milo", 10, Priority.MEDIUM, TaskCategory.FEEDING))
    milo.add_task(Task("Litter Box Clean", 10, Priority.MEDIUM, TaskCategory.OTHER))
    milo.add_task(Task("Play with Feather Toy", 15, Priority.LOW, TaskCategory.ENRICHMENT))

    owner.add_pet(mochi)
    owner.add_pet(milo)

    # ── Generate the daily plan ──
    scheduler = Scheduler()
    plan = scheduler.generate_plan(owner)

    # ── Display results ──
    print("=" * 55)
    print(plan.get_summary())
    print("=" * 55)


if __name__ == "__main__":
    main()
