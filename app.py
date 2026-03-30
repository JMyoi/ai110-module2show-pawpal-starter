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

    if st.button("Add Task"):
        if task_title:
            st.session_state.pets[task_pet]["tasks"].append({
                "title": task_title,
                "duration_minutes": int(duration),
                "priority": priority,
                "category": category,
            })
            st.rerun()

    # Show tasks per pet
    for pname, pdata in st.session_state.pets.items():
        if pdata["tasks"]:
            st.markdown(f"**{pname}'s tasks:**")
            st.table(pdata["tasks"])

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
            task = Task(
                title=t["title"],
                duration_minutes=t["duration_minutes"],
                priority=Priority[t["priority"]],
                category=TaskCategory(t["category"]),
            )
            pet.add_task(task)
        owner.add_pet(pet)

    if not owner.get_all_tasks():
        st.warning("Add at least one task before generating a schedule.")
    else:
        scheduler = Scheduler()
        plan = scheduler.generate_plan(owner)

        # Display scheduled tasks
        st.markdown(f"**Time utilization:** {plan.get_utilization():.0f}% "
                    f"({plan.total_scheduled_minutes}/{plan.total_available_minutes} min)")

        st.markdown("### Scheduled Tasks")
        for st_item in plan.scheduled_tasks:
            st.markdown(
                f"**{st_item.start_time.strftime('%H:%M')}–{st_item.end_time.strftime('%H:%M')}** "
                f"| {st_item.task.title} ({st_item.task.pet_name}) "
                f"| *{st_item.reason}*"
            )

        if plan.skipped_tasks:
            st.markdown("### Skipped Tasks")
            for task, reason in plan.skipped_tasks:
                st.markdown(f"- ~~{task.title}~~ — {reason}")
