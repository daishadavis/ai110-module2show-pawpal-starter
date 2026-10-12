# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

My initial UML split the system into the data the user enters (owner, pets, tasks) and the scheduling logic that turns that data into a plan.

- **Owner**: stores the owner's name, how many minutes they have available, when their day starts, and their preferred task types. It owns the list of pets and can collect every task across all pets (`all_tasks()`).
- **Pet**: stores basic pet info (name, species, age, notes) and owns that pet's care tasks. It is responsible for adding, editing, and removing tasks.
- **Task**: one care activity with a title, duration, priority, category, preferred time of day, and a completed flag. It can update itself, mark itself complete, and turn its priority into a number (`priority_score()`).
- **Priority**: an enumeration (LOW, MEDIUM, HIGH) so priority is always one of three valid values.
- **Scheduler**: reads the owner's constraints and builds the plan (`generate_plan()`), using helper methods to sort tasks and check whether a task fits in the remaining time.
- **DailyPlan**: the result. It holds the scheduled tasks, the skipped tasks, and the total minutes used, and it can explain itself (`explain()`) or turn itself into table rows for the UI (`to_table()`).
- **ScheduledTask**: links a task and its pet to a start time, an end time, and the reason it was chosen.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes. When I reviewed the first diagram, I removed `priority_score()` and the `Priority` enum. I later added both back, because the scheduler needs a number to sort tasks by priority and the enum keeps priority values valid.

During implementation:

- **`DailyPlan` gained a `skip_reasons` field.** The diagram only had a list of skipped tasks, but explaining the plan meant recording *why* each task was skipped, so `explain()` could say something like "needs 90 min but only 30 min left."
- **Time-of-day start times were added (`SLOT_STARTS`).** The first version placed tasks back to back from the start of the day, so an "evening" task ended up at 08:10. Now afternoon tasks start no earlier than 12:00 and evening tasks no earlier than 17:00.
- **`Task` accepts priority as plain text** (for example `"high"`) and converts it to `Priority`. That way the Streamlit dropdown value can be passed straight in.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

The scheduler considers:

1. **Available time:** the total minutes of scheduled tasks can never exceed `Owner.available_minutes`.
2. **Priority:** tasks are chosen high → medium → low.
3. **Owner preferences:** when two tasks have the same priority, the one whose category is in the owner's preferred types wins.
4. **Duration:** after that, shorter tasks go first so more tasks can fit.
5. **Preferred time of day:** chosen tasks are placed morning → afternoon → evening, starting from the owner's day start.
6. **Completion:** tasks already marked done are left out.

Time is a hard limit, because the owner can't do more than they have time for. Priority comes next, because the scenario is about making sure the most important care (like medication or feeding) happens. Preferences and duration only break ties, because they are about convenience, not about the pet's needs.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

The scheduler is **greedy**: it walks through tasks in priority order and takes each one that still fits. It does not search for the combination that uses the time best. For example, a 50-minute high-priority task can use up time that would have fit two 25-minute medium-priority tasks.

This tradeoff is reasonable because, for pet care, getting the most important tasks done matters more than fitting in the most tasks. A greedy approach is also easy to explain: every skipped task has a simple reason ("needs X min but only Y min left"). That supports the requirement to explain the plan, and it's predictable for the owner.

A second, smaller tradeoff: tasks with no preferred time ("any") are placed after the tasks that have a time of day. This keeps the placement logic simple. But it means an "any" task can end up late in the day, even when the morning is free.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

I used Claude Code (an AI coding agent in VS Code) through the whole project:

- **Design:** generating the UML class diagram from the requirements.
- **Implementation:** turning the UML into Python classes in `pawpal_system.py`.
- **Testing:** writing pytest tests for the key behaviors.
- **Integration:** connecting the classes to the Streamlit UI.
- **Debugging:** fixing a Mermaid rendering error and a failing test.

The most helpful prompts were **specific and limited to one step**. For example: "implement the classes first, don't connect it to the Streamlit UI yet." That kept each change small enough for me to review. Pasting the **exact error message**, like the Mermaid `UnknownDiagramError` and the pytest traceback, was also very effective, because the AI could find the real cause instead of guessing.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

When I reviewed the AI's first UML diagram, I didn't accept it as-is. I questioned whether `Task` needed `priority_score()`, and had it removed along with the `Priority` enum. After thinking about how the scheduler would actually sort tasks, I had both added back. Making those changes myself meant I understood why each piece was in the design, instead of accepting the whole diagram at once.

To verify the AI's work, I:

- previewed the Mermaid diagram myself (which is how I found the rendering error)
- ran `pytest` in my own terminal, where I caught a failing test (`test_task_accepts_priority_as_string`) and fed the error back
- ran the Streamlit app and checked the generated plan with real input

Running the app showed me a behavior I wouldn't have noticed from the code alone: a task called "Morning Walks" with time of day set to "any" was scheduled at 12:30.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

The 21 tests in `tests/test_pawpal.py` cover:

- **Task validation:** priority given as text is converted correctly; zero or negative durations, invalid times of day, and unknown fields in edits are rejected; edits are validated again after they're applied.
- **Pets and owners:** adding, editing, and removing tasks and pets; collecting tasks across pets; missing names raise errors.
- **Scheduling:**
  - high-priority tasks are chosen first when time is short
  - the plan never exceeds the available time
  - a smaller task can still fit after a larger one is skipped
  - completed tasks are ignored
  - owner preferences break ties
  - tasks run back to back from the day start
  - morning, afternoon, and evening times are respected
  - each scheduled task records the right pet
  - an empty plan is handled
- **Output:** `explain()` and `to_table()` include the right reasons and columns.

These tests matter because the scheduler is the core of the app. If it overbooks the owner's time or drops a high-priority task like medication, the plan is wrong in a way that affects the pet. The validation tests matter because the UI passes user input straight into these classes.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

I'm fairly confident for normal use. All 21 tests pass, and I checked the plan in the running app. I'm less confident about some edge cases the tests don't cover yet:

- **Two pets with tasks of the same name** (like "Walk" for a dog and a cat): skip reasons are stored by task title, so one reason could overwrite the other.
- **Plans that run past midnight:** a late day start plus evening tasks could produce an invalid time like "24:10".
- **"Any" time tasks** being placed after evening tasks instead of filling free time earlier in the day.
- **Zero available minutes**, and very large numbers of tasks.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

I'm most satisfied that the app explains its decisions. Every scheduled task shows why it was chosen, and every skipped task shows why it didn't fit. This makes the plan easy to trust and easy to adjust. Designing the UML first also made the later steps (code, tests, UI) go smoothly, because each class already had a clear job.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

I would:

- improve how tasks with no preferred time are placed, so they fill the earliest free time
- fix the two-pets-same-task-name issue by tracking skip reasons per task object instead of by title
- add recurring tasks (daily vs. weekly)
- save data so it isn't lost when the page refreshes
- update the UML so it matches the final code, including `skip_reasons`

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

The AI was most useful when I stayed in charge of the design and verification. Breaking the work into small, specific steps (UML → classes → tests → UI) let me review each piece before moving on. Running the tests and the app myself caught problems that reading the code alone wouldn't have. AI can write a lot of code quickly, but I still have to decide what the system should do and check that it really does it.
