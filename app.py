from datetime import time

import streamlit as st

from pawpal_system import Owner, Pet, Priority, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

CATEGORIES = ["walk", "feeding", "meds", "grooming", "play", "training", "other"]
PRIORITIES = [p.value for p in Priority]
TIMES_OF_DAY = ["any", "morning", "afternoon", "evening"]

# The Owner object (with its pets and tasks) lives in session state so it
# survives Streamlit reruns.
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan", available_minutes=120)
owner: Owner = st.session_state.owner

st.title("🐾 PawPal+")
st.caption("Plan your pet's care for the day based on your time and each task's priority.")

# --- Owner ---

st.subheader("1. Owner")
col1, col2 = st.columns(2)
with col1:
    owner.name = st.text_input("Owner name", value=owner.name)
    owner.available_minutes = int(
        st.number_input(
            "Minutes available today", min_value=0, max_value=1440, value=owner.available_minutes
        )
    )
with col2:
    hour, minute = map(int, owner.day_start.split(":"))
    start = st.time_input("Day starts at", value=time(hour, minute))
    owner.day_start = start.strftime("%H:%M")
    owner.preferences = st.multiselect(
        "Preferred task types",
        CATEGORIES,
        default=owner.preferences,
        help="Breaks ties between tasks with the same priority.",
    )

st.divider()

# --- Pets ---

st.subheader("2. Pets")
with st.form("add_pet", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    pet_name = col1.text_input("Pet name")
    species = col2.selectbox("Species", ["dog", "cat", "other"])
    age = col3.number_input("Age", min_value=0, max_value=40, value=0)
    notes = st.text_input("Notes (optional)")
    if st.form_submit_button("Add pet"):
        if not pet_name.strip():
            st.error("Please enter a pet name.")
        elif any(p.name == pet_name.strip() for p in owner.pets):
            st.error(f"You already have a pet named {pet_name.strip()}.")
        else:
            owner.add_pet(Pet(pet_name.strip(), species, int(age), notes))
            st.success(f"Added {pet_name.strip()}.")

if not owner.pets:
    st.info("Add a pet to get started.")
    st.stop()

for pet in owner.pets:
    col1, col2 = st.columns([5, 1])
    details = f"**{pet.name}** · {pet.species}, age {pet.age}"
    if pet.notes:
        details += f" · {pet.notes}"
    col1.markdown(details)
    if col2.button("Remove", key=f"remove_pet_{pet.name}"):
        owner.remove_pet(pet.name)
        st.rerun()

st.divider()

# --- Tasks ---

st.subheader("3. Tasks")
pet = owner.get_pet(st.selectbox("Pet", [p.name for p in owner.pets]))

with st.form("add_task", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    title = col1.text_input("Task title", placeholder="Morning walk")
    duration = col2.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    priority = col3.selectbox("Priority", PRIORITIES, index=2)
    col4, col5 = st.columns(2)
    category = col4.selectbox("Type", CATEGORIES)
    preferred = col5.selectbox("Time of day", TIMES_OF_DAY)
    if st.form_submit_button("Add task"):
        if not title.strip():
            st.error("Please enter a task title.")
        elif any(t.title == title.strip() for t in pet.tasks):
            st.error(f"{pet.name} already has a task called {title.strip()}.")
        else:
            pet.add_task(
                Task(
                    title.strip(),
                    int(duration),
                    priority,
                    category,
                    "" if preferred == "any" else preferred,
                )
            )
            st.success(f"Added {title.strip()} for {pet.name}.")

if pet.tasks:
    st.table(
        [
            {
                "task": t.title,
                "minutes": t.duration_minutes,
                "priority": t.priority.value,
                "type": t.category,
                "time of day": t.preferred_time or "any",
                "done": "✅" if t.completed else "",
            }
            for t in pet.tasks
        ]
    )

    with st.expander("Edit a task"):
        task = next(
            t
            for t in pet.tasks
            if t.title == st.selectbox("Task to edit", [t.title for t in pet.tasks])
        )
        # Keys include the task so the fields reset when a different task is picked.
        key = f"{pet.name}_{task.title}"
        col1, col2, col3 = st.columns(3)
        new_title = col1.text_input("Title", value=task.title, key=f"title_{key}")
        new_duration = col2.number_input(
            "Duration (minutes)",
            min_value=1,
            max_value=240,
            value=task.duration_minutes,
            key=f"duration_{key}",
        )
        new_priority = col3.selectbox(
            "Priority",
            PRIORITIES,
            index=PRIORITIES.index(task.priority.value),
            key=f"priority_{key}",
        )
        col4, col5 = st.columns(2)
        new_category = col4.selectbox(
            "Type",
            CATEGORIES,
            index=CATEGORIES.index(task.category) if task.category in CATEGORIES else 0,
            key=f"category_{key}",
        )
        new_preferred = col5.selectbox(
            "Time of day",
            TIMES_OF_DAY,
            index=TIMES_OF_DAY.index(task.preferred_time or "any"),
            key=f"preferred_{key}",
        )

        col1, col2, col3 = st.columns(3)
        if col1.button("Save changes", key=f"save_{key}"):
            new_title = new_title.strip()
            if not new_title:
                st.error("Title can't be empty.")
            elif new_title != task.title and any(t.title == new_title for t in pet.tasks):
                st.error(f"{pet.name} already has a task called {new_title}.")
            else:
                pet.edit_task(
                    task.title,
                    {
                        "title": new_title,
                        "duration_minutes": int(new_duration),
                        "priority": new_priority,
                        "category": new_category,
                        "preferred_time": "" if new_preferred == "any" else new_preferred,
                    },
                )
                st.rerun()
        if col2.button(
            "Mark done" if not task.completed else "Mark not done", key=f"done_{key}"
        ):
            task.completed = not task.completed
            st.rerun()
        if col3.button("Delete task", key=f"delete_{key}"):
            pet.remove_task(task.title)
            st.rerun()
else:
    st.info(f"No tasks for {pet.name} yet. Add one above.")

st.divider()

# --- Schedule ---

st.subheader("4. Today's plan")
if st.button("Generate schedule", type="primary"):
    plan = Scheduler(owner).generate_plan()

    if not plan.scheduled and not plan.skipped:
        st.info("No tasks to schedule. Add some tasks (or mark some as not done).")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Tasks planned", len(plan.scheduled))
        col2.metric("Minutes used", f"{plan.total_minutes} / {owner.available_minutes}")
        col3.metric("Tasks skipped", len(plan.skipped))

        if plan.scheduled:
            st.table(
                [
                    {k: row[k] for k in ("start", "end", "pet", "task", "priority")}
                    for row in plan.to_table()
                ]
            )

            st.markdown("#### Why this plan")
            st.caption(
                "Tasks are picked by priority until your time runs out. "
                "Ties go to your preferred task types, then to shorter tasks. "
                "Picked tasks are then placed by time of day."
            )
            for item in plan.scheduled:
                st.markdown(
                    f"- **{item.start_time}–{item.end_time} {item.task.title}** "
                    f"({item.pet.name}): {item.reason}"
                )

        if plan.skipped:
            st.markdown("#### Skipped")
            for task in plan.skipped:
                st.warning(f"**{task.title}**: {plan.skip_reasons[task.title]}")
