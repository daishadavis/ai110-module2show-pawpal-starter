import pytest

from pawpal_system import DailyPlan, Owner, Pet, Priority, Scheduler, Task


@pytest.fixture
def owner():
    owner = Owner("Jordan", available_minutes=60)
    owner.add_pet(Pet("Mochi", "dog"))
    return owner


def titles(plan):
    return [item.task.title for item in plan.scheduled]


# --- Task ---


def test_task_accepts_priority_as_string():
    task = Task("Walk", 20, "HIGH")
    assert task.priority is Priority.HIGH
    assert task.priority_score() == 3


def test_priority_scores_are_ordered():
    scores = [Task("t", 5, p).priority_score() for p in ("low", "medium", "high")]
    assert scores == sorted(scores)


@pytest.mark.parametrize("duration", [0, -5])
def test_task_rejects_non_positive_duration(duration):
    with pytest.raises(ValueError):
        Task("Walk", duration)


def test_task_rejects_unknown_preferred_time():
    with pytest.raises(ValueError):
        Task("Walk", 20, preferred_time="midnight")


def test_mark_complete():
    task = Task("Walk", 20)
    task.mark_complete()
    assert task.completed


def test_update_changes_fields_and_revalidates():
    task = Task("Walk", 20, "low")
    task.update({"duration_minutes": 30, "priority": "high"})
    assert task.duration_minutes == 30
    assert task.priority is Priority.HIGH

    with pytest.raises(ValueError):
        task.update({"duration_minutes": 0})


def test_update_rejects_unknown_field():
    task = Task("Walk", 20)
    with pytest.raises(ValueError):
        task.update({"color": "blue"})


# --- Pet and Owner ---


def test_pet_add_edit_remove_task():
    pet = Pet("Mochi", "dog")
    pet.add_task(Task("Walk", 20))
    pet.edit_task("Walk", {"duration_minutes": 25})
    assert pet.tasks[0].duration_minutes == 25

    pet.remove_task("Walk")
    assert pet.tasks == []


def test_pet_missing_task_raises():
    pet = Pet("Mochi", "dog")
    with pytest.raises(KeyError):
        pet.edit_task("Nope", {"duration_minutes": 5})


def test_owner_manages_pets_and_collects_tasks(owner):
    cat = Pet("Luna", "cat")
    owner.add_pet(cat)
    owner.get_pet("Mochi").add_task(Task("Walk", 20))
    cat.add_task(Task("Feed", 5))

    assert [t.title for t in owner.all_tasks()] == ["Walk", "Feed"]

    owner.remove_pet("Luna")
    with pytest.raises(KeyError):
        owner.get_pet("Luna")


# --- Scheduler ---


def test_high_priority_tasks_chosen_first_when_time_is_short(owner):
    pet = owner.get_pet("Mochi")
    pet.add_task(Task("Grooming", 40, "low"))
    pet.add_task(Task("Meds", 30, "high"))
    pet.add_task(Task("Play", 30, "medium"))

    plan = Scheduler(owner).generate_plan()

    assert titles(plan) == ["Meds", "Play"]
    assert [t.title for t in plan.skipped] == ["Grooming"]


def test_plan_never_exceeds_available_time(owner):
    pet = owner.get_pet("Mochi")
    for i in range(10):
        pet.add_task(Task(f"Task {i}", 15, "medium"))

    plan = Scheduler(owner).generate_plan()

    assert plan.total_minutes <= owner.available_minutes
    assert len(plan.scheduled) + len(plan.skipped) == 10


def test_smaller_task_still_fits_after_large_one_is_skipped(owner):
    pet = owner.get_pet("Mochi")
    pet.add_task(Task("Long walk", 50, "high"))
    pet.add_task(Task("Vet trip", 30, "high"))
    pet.add_task(Task("Brush", 10, "low"))

    plan = Scheduler(owner).generate_plan()

    # Vet trip (shorter) wins the tie, Long walk no longer fits, Brush still does.
    assert titles(plan) == ["Vet trip", "Brush"]
    assert [t.title for t in plan.skipped] == ["Long walk"]


def test_completed_tasks_are_ignored(owner):
    pet = owner.get_pet("Mochi")
    done = Task("Breakfast", 10, "high")
    done.mark_complete()
    pet.add_task(done)
    pet.add_task(Task("Walk", 20))

    plan = Scheduler(owner).generate_plan()

    assert titles(plan) == ["Walk"]
    assert plan.skipped == []


def test_owner_preference_breaks_priority_ties():
    owner = Owner("Jordan", available_minutes=20, preferences=["walk"])
    pet = Pet("Mochi", "dog")
    owner.add_pet(pet)
    pet.add_task(Task("Puzzle toy", 20, "high", category="enrichment"))
    pet.add_task(Task("Walk", 20, "high", category="walk"))

    plan = Scheduler(owner).generate_plan()

    assert titles(plan) == ["Walk"]
    assert "owner prefers walk" in plan.scheduled[0].reason


def test_tasks_are_back_to_back_from_day_start(owner):
    owner.day_start = "07:30"
    pet = owner.get_pet("Mochi")
    pet.add_task(Task("Feed", 10, "high"))
    pet.add_task(Task("Walk", 20, "medium"))

    plan = Scheduler(owner).generate_plan()

    times = [(i.start_time, i.end_time) for i in plan.scheduled]
    assert times == [("07:30", "07:40"), ("07:40", "08:00")]


def test_preferred_times_are_respected(owner):
    pet = owner.get_pet("Mochi")
    pet.add_task(Task("Evening walk", 20, "high", preferred_time="evening"))
    pet.add_task(Task("Lunch", 10, "high", preferred_time="afternoon"))
    pet.add_task(Task("Breakfast", 10, "high", preferred_time="morning"))

    plan = Scheduler(owner).generate_plan()

    by_title = {i.task.title: i for i in plan.scheduled}
    assert by_title["Breakfast"].start_time == "08:00"
    assert by_title["Lunch"].start_time == "12:00"
    assert by_title["Evening walk"].start_time == "17:00"


def test_scheduled_task_records_its_pet():
    owner = Owner("Jordan", available_minutes=60)
    dog, cat = Pet("Mochi", "dog"), Pet("Luna", "cat")
    owner.add_pet(dog)
    owner.add_pet(cat)
    cat.add_task(Task("Litter box", 10, "high"))

    plan = Scheduler(owner).generate_plan()

    assert plan.scheduled[0].pet is cat


def test_empty_plan(owner):
    plan = Scheduler(owner).generate_plan()
    assert plan.scheduled == []
    assert plan.explain() == "No tasks to schedule."


# --- DailyPlan output ---


def test_explain_and_table_describe_the_plan(owner):
    pet = owner.get_pet("Mochi")
    pet.add_task(Task("Walk", 30, "high"))
    pet.add_task(Task("Bath", 45, "low"))

    plan = Scheduler(owner).generate_plan()
    text = plan.explain()

    assert "Walk" in text and "high priority" in text
    assert "Skipped Bath" in text and "45 min" in text

    row = plan.to_table()[0]
    assert row["task"] == "Walk"
    assert row["pet"] == "Mochi"
    assert row["priority"] == "high"
    assert {"start", "end", "reason"} <= row.keys()

