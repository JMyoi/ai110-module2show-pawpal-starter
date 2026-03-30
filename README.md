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

---

## System Object Design

All classes are defined in `pawpal_system.py`. The system separates **input data** (Owner, Pet, Task) from **output data** (ScheduledTask, DailyPlan), with the **Scheduler** as the bridge between them.

### Enums

#### `Priority`

Represents task urgency. Integer values enable direct sorting by the scheduler.

| Value | Int | Purpose |
|-------|-----|---------|
| `HIGH` | 3 | Must-do tasks (medications, critical appointments) |
| `MEDIUM` | 2 | Should-do tasks (walks, feeding) |
| `LOW` | 1 | Nice-to-do tasks (enrichment, extra grooming) |

#### `TaskCategory`

Categorizes pet care activities. Used by the scheduler to break ties among tasks with equal priority (e.g., medication is scheduled before walks).

| Value | Description |
|-------|-------------|
| `MEDICATION` | Medical tasks (pills, treatments) |
| `FEEDING` | Meals and treats |
| `WALK` | Exercise and outdoor time |
| `GROOMING` | Bathing, brushing, nail trims |
| `ENRICHMENT` | Play, training, puzzles |
| `APPOINTMENT` | Vet visits, checkups |
| `OTHER` | Catch-all for uncategorized tasks |

#### `CATEGORY_ORDER` (dict)

A constant dictionary that maps each `TaskCategory` to a scheduling rank (lower = scheduled earlier among same priority). This gives the scheduler a deterministic tiebreaker so that medical needs always come before recreational tasks.

---

### Core Data Classes

#### `Task`

A pet care task **request** — represents what needs to be done, not when. The scheduler assigns times separately, keeping input and output cleanly separated.

**Data Members:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `title` | `str` | Name of the task (e.g., "Morning Walk") |
| `duration_minutes` | `int` | How long the task takes in minutes |
| `priority` | `Priority` | Urgency level (HIGH, MEDIUM, LOW) |
| `category` | `TaskCategory` | Type of care activity (default: OTHER) |
| `pet_name` | `str` | Which pet this task belongs to (set automatically by `Pet.add_task()`) |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `__str__()` | `str` | Human-readable format, e.g., `"Morning Walk (30 min, HIGH)"` |

---

#### `Pet`

Represents a pet and holds its list of care tasks. Acts as the composition link between an owner and their tasks.

**Data Members:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Pet's display name |
| `species` | `str` | Species type ("dog", "cat", "other") |
| `age` | `int` | Age in years (default: 0) |
| `tasks` | `list[Task]` | Care tasks associated with this pet |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `add_task(task)` | `None` | Appends a task and automatically sets its `pet_name` to this pet's name |
| `remove_task(task_title)` | `bool` | Removes the first task matching the title; returns whether it was found |
| `get_tasks_by_priority(priority)` | `list[Task]` | Filters and returns tasks matching a specific priority level |
| `get_tasks_by_category(category)` | `list[Task]` | Filters and returns tasks matching a specific category |

---

#### `Owner`

Represents the pet owner with their time constraints and preferences. This is the top-level input object passed to the scheduler.

**Data Members:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Owner's display name |
| `available_minutes` | `int` | Total minutes available for pet care today (default: 120) — the main time constraint |
| `preferred_start_time` | `time` | Earliest time the owner wants to start tasks (default: 08:00) |
| `pets` | `list[Pet]` | Pets belonging to this owner |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `add_pet(pet)` | `None` | Appends a pet to the owner's list |
| `remove_pet(pet_name)` | `bool` | Removes a pet by name; returns whether it was found |
| `get_all_tasks()` | `list[Task]` | Flattens and returns all tasks across all pets — convenience method used by the scheduler |

---

### Output Classes

#### `ScheduledTask`

Wraps an original `Task` with a scheduled time slot and a reason explaining why the scheduler placed it there. This is the scheduler's **output** — it never modifies the original Task object.

**Data Members:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `task` | `Task` | Reference to the original task request |
| `start_time` | `time` | When this task starts in the daily plan |
| `end_time` | `time` | When this task ends (computed from start_time + duration) |
| `reason` | `str` | Human-readable explanation of why this task was scheduled here |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `__str__()` | `str` | Formatted string, e.g., `"08:00-08:30 Morning Walk (Mochi) — High priority, scheduled first"` |

---

#### `DailyPlan`

The complete daily schedule produced by the scheduler. Contains both scheduled and skipped tasks, providing full transparency about what was planned and what was dropped (and why).

**Data Members:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `owner_name` | `str` | Whose plan this is |
| `date` | `date` | Which day this plan covers |
| `scheduled_tasks` | `list[ScheduledTask]` | Ordered list of tasks that fit within the time budget |
| `skipped_tasks` | `list[tuple[Task, str]]` | Tasks that did not fit, paired with a reason string |
| `total_scheduled_minutes` | `int` | Sum of durations of all scheduled tasks |
| `total_available_minutes` | `int` | The owner's original time budget |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_summary()` | `str` | Multi-line human-readable plan with time slots, reasoning, and skipped tasks |
| `get_utilization()` | `float` | Percentage of available time used (scheduled / available * 100) |

---

### Scheduler

#### `Scheduler`

The scheduling engine. Stateless by design — it takes an `Owner` as input and returns a `DailyPlan` as output with no stored internal state. This makes it easy to test (same input always produces same output) and easy to call repeatedly from the UI.

**Algorithm:** Greedy priority-first bin-packing. Tasks are sorted by priority (HIGH first), then by category importance (medication before walks), then by duration (shorter first to maximize tasks scheduled). Each task is either placed in the next available time slot or skipped with an explanation.

**Data Members:** None (stateless).

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `generate_plan(owner)` | `DailyPlan` | Main entry point — collects all tasks, sorts them, assigns time slots within the budget, and returns a complete plan |
| `_sort_tasks(tasks)` | `list[Task]` | Sorts tasks by: priority descending, category order, duration ascending |
| `_fits_in_budget(task, remaining_minutes)` | `bool` | Checks whether a task's duration fits in the remaining time |
| `_assign_time(task, current_time, position, remaining_minutes)` | `ScheduledTask` | Creates a ScheduledTask with computed start/end times and a reason string |
| `_build_reason(task, position, remaining_minutes)` | `str` | Generates the human-readable explanation for why a task was scheduled at its position |

---

### Class Relationships

```
Owner  ──has-many──▶  Pet  ──has-many──▶  Task
  │                                          │
  │                                     (wrapped by)
  │                                          ▼
  └──(input to)──▶  Scheduler  ──produces──▶  DailyPlan  ──contains──▶  ScheduledTask
                                                 │
                                            (references skipped Tasks)
```

- **Owner → Pet**: Composition (owner owns their pets)
- **Pet → Task**: Composition (pet owns its tasks)
- **ScheduledTask → Task**: Association (wraps but does not own the original task)
- **Scheduler → Owner**: Dependency (receives as input)
- **Scheduler → DailyPlan**: Dependency (produces as output)
- **DailyPlan → ScheduledTask**: Composition (plan owns its schedule entries)
