# Smart Functionality Plan — PawPal+

## Context

The core PawPal+ system (Owner, Pet, Task, Scheduler, DailyPlan) is implemented and working. This plan adds 4 "smart" features to make the app more useful: preferred time sorting, filtering, recurring tasks, and conflict detection.

## Implementation Order

**Feature 2 → Feature 1 → Feature 3 → Feature 4**

- Feature 2 (Filtering) adds `is_completed` + `mark_complete()`, which Feature 3 depends on
- Feature 1 (Preferred Time) adds `preferred_time`, which Feature 4 depends on for meaningful conflicts
- Feature 3 (Recurring) depends on Feature 2's completion logic
- Feature 4 (Conflict Detection) depends on Feature 1's preferred times (the sequential scheduler can't produce overlaps on its own)

All existing 18 tests will continue to pass — every change is additive with default values.

---

## Feature 2: Filtering by Pet & Completion Status

**What already exists:** `Pet.get_tasks_by_priority()`, `Pet.get_tasks_by_category()`, `Task.pet_name`
**What's missing:** No `is_completed` attribute, no way to mark tasks done, no status filtering

### Changes to `pawpal_system.py`

**`Task` class — add:**
| Addition | Details |
|----------|---------|
| `is_completed: bool = False` | New attribute after `pet_name` |
| `mark_complete() -> None` | Sets `is_completed = True` |

**`Pet` class — add:**
| Addition | Details |
|----------|---------|
| `get_tasks_by_status(completed: bool) -> list[Task]` | Follows existing filter pattern |

**`Owner` class — modify:**
| Change | Details |
|--------|---------|
| `get_all_tasks(pet_name=None, completed=None)` | Add optional filter params; no args = same as before (backward compatible) |

**`Scheduler.generate_plan()` — modify:**
- After collecting all tasks, filter out completed ones: `all_tasks = [t for t in owner.get_all_tasks() if not t.is_completed]`

**`app.py`:**
- Add filter controls (dropdown for pet name, checkbox for status) in the task display section
- Add "Mark Complete" button next to scheduled tasks

### Tests (7)
- `test_task_default_not_completed` — new Task has `is_completed == False`
- `test_mark_complete` — after calling, `is_completed` is True
- `test_pet_get_tasks_by_status` — 3 tasks, mark 1 complete, verify filter returns correct counts
- `test_owner_filter_by_pet` — owner with 2 pets, filter returns only specified pet's tasks
- `test_owner_filter_by_completed` — returns correct subset
- `test_owner_no_filter_backward_compatible` — no args returns all tasks
- `test_completed_tasks_not_scheduled` — completed task excluded from plan

---

## Feature 1: Sorting Tasks by Preferred Time

**What already exists:** `_sort_tasks()` sorts by priority → category → duration
**What's missing:** No time attribute on Task, no time-based sorting

### Changes to `pawpal_system.py`

**`Task` class — add:**
| Addition | Details |
|----------|---------|
| `preferred_time: time \| None = None` | Optional; when set, scheduler tries to honor it |

**`Task.__str__()` — update:**
- Append `" @ HH:MM"` when `preferred_time` is set

**`Scheduler._sort_tasks()` — update sort key:**
```
key = (
    -priority.value,                                          # HIGH first
    CATEGORY_ORDER,                                           # MEDICATION before WALK
    (0, preferred_time) if preferred_time else (1, time(0,0)),  # timed tasks before untimed
    duration_minutes,                                         # shorter first
)
```

**`Scheduler._assign_time()` — update:**
- If task has `preferred_time` and it's >= `current_time`, use it as `start_time` (creates a gap, which is OK)
- If `preferred_time` < `current_time`, fall back to `current_time` and note in reason
- Gap minutes are "dead time" — only `duration_minutes` counts against the budget

**`Scheduler._build_reason()` — update:**
- If task has `preferred_time`, append `"Preferred time: HH:MM"` to reason

**`app.py`:**
- Add checkbox "Set preferred time?" + `st.time_input()` in task creation form
- Store in session state and pass through to Task construction

### Tests (6)
- `test_task_with_preferred_time_str` — `__str__()` includes "@ HH:MM"
- `test_sort_earlier_preferred_time_first` — 9:00 task sorts before 10:00 task at same priority
- `test_task_without_preferred_time_sorts_after` — timed task before untimed at same priority
- `test_assign_time_uses_preferred_time` — task starts at preferred time, not current_time
- `test_preferred_time_in_past_falls_back` — uses current_time if preferred is already past
- `test_preferred_time_in_reason` — reason string mentions the preferred time

---

## Feature 3: Recurring Tasks

**What already exists:** Nothing — no recurrence attributes or auto-generation
**Depends on:** Feature 2 (`is_completed`, `mark_complete()`)

### Changes to `pawpal_system.py`

**`Task` class — add:**
| Addition | Details |
|----------|---------|
| `recurrence: str \| None = None` | Valid values: `None`, `"daily"`, `"weekly"` |

**`Pet` class — add:**
| Addition | Details |
|----------|---------|
| `complete_task(task_title: str) -> Task \| None` | Marks task complete. If recurring, creates a fresh copy with `is_completed=False` and appends it. Returns the new task or None. |

This lives on `Pet` (not Task) because Pet owns the task list and needs to append the new instance.

**`app.py`:**
- Add recurrence selectbox (`None / Daily / Weekly`) in task creation form
- When "Complete" button is clicked, call `pet.complete_task()` and show message if new task was created

### Tests (7)
- `test_task_default_no_recurrence` — `recurrence is None`
- `test_complete_non_recurring` — returns None, task is marked complete
- `test_complete_daily_creates_new` — new incomplete task with same attributes added
- `test_complete_weekly_creates_new` — same for weekly
- `test_new_recurring_task_is_independent` — old is completed, new is not, separate objects
- `test_complete_task_not_found` — returns None, no changes
- `test_completed_recurring_not_rescheduled` — old copy excluded from plan, new copy included

---

## Feature 4: Conflict Detection

**What already exists:** Sequential scheduling prevents overlaps by design — no detection needed
**Depends on:** Feature 1 (`preferred_time` makes overlaps possible)

### Changes to `pawpal_system.py`

**`DailyPlan` class — add:**
| Addition | Details |
|----------|---------|
| `warnings: list[str] = field(default_factory=list)` | Conflict warning messages |

**`Scheduler` class — add:**
| Addition | Details |
|----------|---------|
| `detect_conflicts(plan: DailyPlan) -> list[str]` | O(n²) pairwise overlap check; returns warning strings |

**Design decision:** Schedule both tasks at their preferred times even if they overlap, then report the conflict as a warning. This matches the requirement: "return a warning, NOT crash."

Overlap check: `task_i.end_time > task_j.start_time AND task_j.end_time > task_i.start_time`

**`Scheduler.generate_plan()` — update:**
- At the end, call `detect_conflicts(plan)` and set `plan.warnings`

**`DailyPlan.get_summary()` — update:**
- Add a "Warnings" section at the bottom when `self.warnings` is non-empty

**`app.py`:**
- After displaying schedule, check `plan.warnings` and display each with `st.warning()`

### Tests (7)
- `test_no_conflicts_sequential` — normal plan with no preferred times = no warnings
- `test_conflict_detected_same_preferred_time` — two tasks at 9:00 = warning
- `test_conflict_message_has_task_names` — warning contains both titles
- `test_conflict_message_has_times` — warning contains time ranges
- `test_multiple_conflicts_all_reported` — 3 tasks at same slot = 3 pairwise warnings
- `test_no_crash_on_conflict` — plan still generated, tasks still scheduled
- `test_adjacent_tasks_no_conflict` — A ends 9:30, B starts 9:30 = no overlap

---

## Summary of All Changes

### `pawpal_system.py` — by class

| Class | What's Added | Feature |
|-------|-------------|---------|
| `Task` | `is_completed`, `mark_complete()` | 2 |
| `Task` | `preferred_time` | 1 |
| `Task` | `recurrence` | 3 |
| `Task` | Updated `__str__()` | 1 |
| `Pet` | `get_tasks_by_status()` | 2 |
| `Pet` | `complete_task()` | 3 |
| `Owner` | `get_all_tasks()` gains optional filters | 2 |
| `Scheduler` | Updated `_sort_tasks()` | 1 |
| `Scheduler` | Updated `_assign_time()` | 1 |
| `Scheduler` | Updated `_build_reason()` | 1 |
| `Scheduler` | Updated `generate_plan()` | 2, 4 |
| `Scheduler` | `detect_conflicts()` | 4 |
| `DailyPlan` | `warnings` attribute | 4 |
| `DailyPlan` | Updated `get_summary()` | 4 |

### New Task field order (all defaults, backward compatible)
`title, duration_minutes, priority, category=OTHER, pet_name="", preferred_time=None, is_completed=False, recurrence=None`

### Test count: ~27 new tests across 4 features

### Critical files
- `pawpal_system.py` — all backend changes
- `tests/test_scheduler.py` — all new tests
- `app.py` — UI additions
- `demo.py` — optional update to showcase new features

## Verification
- `pytest tests/test_scheduler.py -v` — all 18 existing + ~27 new tests pass
- `python demo.py` — CLI output shows preferred times, recurring tasks, conflict warnings
- `streamlit run app.py` — UI supports all new inputs and displays warnings
