import streamlit as st
from datetime import time

from pawpal_system import (
    Priority, TaskCategory, Task, Pet, Owner, Scheduler,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Smart pet care scheduling — prioritize what matters most.")

# ──────────────────────────────────────────────
# Session state initialization
# ──────────────────────────────────────────────

if "pets" not in st.session_state:
    st.session_state.pets = {}  # {pet_name: {"species": ..., "age": ..., "tasks": [...]}}
if "last_plan" not in st.session_state:
    st.session_state.last_plan = None  # stores the most recently generated plan

# ──────────────────────────────────────────────
# Owner info
# ──────────────────────────────────────────────

st.subheader("Owner Info")
col_owner1, col_owner2, col_owner3 = st.columns(3)
with col_owner1:
    owner_name = st.text_input("Owner name", value="Jordan")
with col_owner2:
    available_minutes = st.number_input("Available minutes today", min_value=10, max_value=480, value=120)
with col_owner3:
    start_hour = st.number_input("Start hour (24h)", min_value=0, max_value=23, value=8)

st.divider()

# ──────────────────────────────────────────────
# Pet management
# ──────────────────────────────────────────────

st.subheader("Pets")

col_pet1, col_pet2, col_pet3 = st.columns(3)
with col_pet1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col_pet2:
    species = st.selectbox("Species", ["dog", "cat", "other"])
with col_pet3:
    pet_age = st.number_input("Age (years)", min_value=0, max_value=30, value=3)

if st.button("Add Pet"):
    if pet_name and pet_name not in st.session_state.pets:
        st.session_state.pets[pet_name] = {"species": species, "age": pet_age, "tasks": []}
        st.rerun()
    elif pet_name in st.session_state.pets:
        st.warning(f"{pet_name} already exists.")

if st.session_state.pets:
    st.write("**Current pets:**", ", ".join(st.session_state.pets.keys()))
else:
    st.info("No pets yet. Add one above.")

st.divider()

# ──────────────────────────────────────────────
# Task management
# ──────────────────────────────────────────────

st.subheader("Tasks")

if not st.session_state.pets:
    st.info("Add a pet first, then you can add tasks.")
else:
    col1, col2 = st.columns(2)
    with col1:
        task_pet = st.selectbox("For which pet?", list(st.session_state.pets.keys()))
        task_title = st.text_input("Task title", value="Morning Walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority = st.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"])
    category = st.selectbox("Category", [c.value for c in TaskCategory])

    col_time1, col_time2, col_recur = st.columns([1, 2, 1])
    with col_time1:
        use_preferred_time = st.checkbox("Set preferred time?")
    with col_time2:
        preferred_time_val = st.time_input("Preferred time", value=time(9, 0), disabled=not use_preferred_time)
    with col_recur:
        recurrence = st.selectbox("Recurrence", ["None", "Daily", "Weekly"])

    if st.button("Add Task"):
        if task_title:
            task_data = {
                "title": task_title,
                "duration_minutes": int(duration),
                "priority": priority,
                "category": category,
                "preferred_time": preferred_time_val.strftime("%H:%M") if use_preferred_time else None,
                "recurrence": None if recurrence == "None" else recurrence.lower(),
            }
            st.session_state.pets[task_pet]["tasks"].append(task_data)
            st.rerun()

    # Filter controls
    st.markdown("#### Filter Tasks")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_pet = st.selectbox(
            "Filter by pet",
            ["All pets"] + list(st.session_state.pets.keys()),
            key="filter_pet",
        )
    with col_f2:
        filter_status = st.selectbox(
            "Filter by status",
            ["All", "Pending", "Completed"],
            key="filter_status",
        )

    # Show tasks per pet (with filters applied)
    for pname, pdata in st.session_state.pets.items():
        if filter_pet != "All pets" and pname != filter_pet:
            continue
        filtered = pdata["tasks"]
        if filter_status == "Pending":
            filtered = [t for t in filtered if not t.get("is_completed", False)]
        elif filter_status == "Completed":
            filtered = [t for t in filtered if t.get("is_completed", False)]
        if filtered:
            st.markdown(f"**{pname}'s tasks:**")
            display = [
                {
                    "title": t["title"],
                    "duration (min)": t["duration_minutes"],
                    "priority": t["priority"],
                    "category": t["category"],
                    "preferred time": t.get("preferred_time") or "—",
                    "recurrence": t.get("recurrence") or "—",
                    "status": "Done" if t.get("is_completed") else "Pending",
                }
                for t in filtered
            ]
            st.table(display)

st.divider()

# ──────────────────────────────────────────────
# Schedule generation
# ──────────────────────────────────────────────

st.subheader("Generate Daily Schedule")

if st.button("Generate Schedule", type="primary"):
    # Build Owner/Pet/Task objects from session state
    owner = Owner(
        name=owner_name,
        available_minutes=available_minutes,
        preferred_start_time=time(start_hour, 0),
    )

    for pname, pdata in st.session_state.pets.items():
        pet = Pet(name=pname, species=pdata["species"], age=pdata["age"])
        for t in pdata["tasks"]:
            pt = t.get("preferred_time")
            task = Task(
                title=t["title"],
                duration_minutes=t["duration_minutes"],
                priority=Priority[t["priority"]],
                category=TaskCategory(t["category"]),
                preferred_time=time(int(pt[:2]), int(pt[3:])) if pt else None,
                is_completed=t.get("is_completed", False),
                recurrence=t.get("recurrence"),
            )
            pet.add_task(task)
        owner.add_pet(pet)

    if not owner.get_all_tasks():
        st.warning("Add at least one task before generating a schedule.")
        st.session_state.last_plan = None
    else:
        scheduler = Scheduler()
        plan = scheduler.generate_plan(owner)
        # Persist plan data in session state so it survives reruns (e.g. when Done is clicked)
        st.session_state.last_plan = {
            "utilization": plan.get_utilization(),
            "total_scheduled": plan.total_scheduled_minutes,
            "total_available": plan.total_available_minutes,
            "warnings": plan.warnings,
            "scheduled": [
                {
                    "start": st_item.start_time.strftime("%H:%M"),
                    "end": st_item.end_time.strftime("%H:%M"),
                    "title": st_item.task.title,
                    "pet_name": st_item.task.pet_name,
                    "reason": st_item.reason,
                    "preferred_time": st_item.task.preferred_time.strftime("%H:%M") if st_item.task.preferred_time else None,
                    "recurrence": st_item.task.recurrence,
                }
                for st_item in plan.scheduled_tasks
            ],
            "skipped": [
                {"title": task.title, "pet_name": task.pet_name, "reason": reason}
                for task, reason in plan.skipped_tasks
            ],
        }

# Display the last generated plan (persists across reruns from Done buttons)
if st.session_state.last_plan:
    plan_data = st.session_state.last_plan

    st.markdown(
        f"**Time utilization:** {plan_data['utilization']:.0f}% "
        f"({plan_data['total_scheduled']}/{plan_data['total_available']} min)"
    )

    st.markdown("### Scheduled Tasks")
    for item in plan_data["scheduled"]:
        is_done = st.session_state.pets.get(item["pet_name"], {})
        task_done = any(
            t["title"] == item["title"] and t.get("is_completed")
            for t in st.session_state.pets.get(item["pet_name"], {}).get("tasks", [])
        )
        col_task, col_btn = st.columns([5, 1])
        with col_task:
            label = f"~~{item['title']}~~" if task_done else item["title"]
            st.markdown(
                f"**{item['start']}–{item['end']}** "
                f"| {label} ({item['pet_name']}) "
                f"| *{item['reason']}*"
            )
        with col_btn:
            if task_done:
                st.markdown("✅")
            else:
                btn_key = f"complete_{item['pet_name']}_{item['title']}"
                if st.button("Done", key=btn_key):
                    pet_tasks = st.session_state.pets[item["pet_name"]]["tasks"]
                    for t in pet_tasks:
                        if t["title"] == item["title"] and not t.get("is_completed"):
                            t["is_completed"] = True
                            # If recurring, create the next occurrence in session state
                            if t.get("recurrence") in ("daily", "weekly"):
                                next_task = {k: v for k, v in t.items()}
                                next_task["is_completed"] = False
                                pet_tasks.append(next_task)
                                st.toast(f"'{item['title']}' done! Next {t['recurrence']} occurrence added.")
                            else:
                                st.toast(f"'{item['title']}' marked complete!")
                            st.rerun()

    if plan_data["skipped"]:
        st.markdown("### Skipped Tasks")
        for item in plan_data["skipped"]:
            st.markdown(f"- ~~{item['title']}~~ ({item['pet_name']}) — {item['reason']}")

    if plan_data.get("warnings"):
        st.markdown("### Warnings")
        for w in plan_data["warnings"]:
            st.warning(w)
