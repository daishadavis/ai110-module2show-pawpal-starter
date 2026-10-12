# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I used Claude Code (Claude Opus 5.5, in the VS Code extension) to build PawPal+ step by step, giving it one request at a time:

1. Create a UML class diagram in `diagrams/uml.mmd` from the project requirements (owner and pet info, adding and editing tasks with duration and priority, generating a daily plan, and explaining it).
2. Implement the UML design as Python classes, without connecting them to the Streamlit UI yet.
3. Add pytest tests for the key behaviors.
4. Connect the logic to the Streamlit app in `app.py`.
5. Fill out the README sections (Smarter Scheduling, Demo Walkthrough, Sample Output, and Sample test output).

**What did the agent do?**

- **UML:** Read the starter `app.py` to match its field names, then wrote a Mermaid class diagram with `Owner`, `Pet`, `Task`, `Priority`, `Scheduler`, `DailyPlan`, and `ScheduledTask`, including their attributes, methods, and relationships.
- **Python classes:** Created `pawpal_system.py` using dataclasses. It ran a quick script with sample data to check the output and found its own bug: an "evening" task was scheduled at 08:10. It fixed this by making afternoon tasks start no earlier than 12:00 and evening tasks no earlier than 17:00.
- **Tests:** Wrote 21 tests in `tests/test_pawpal.py`, covering task validation, editing, pets and owners, priority sorting, time limits, skipped tasks, owner preferences, time-of-day placement, and the plan explanation. It added `pytest.ini` so the tests can import `pawpal_system`, and it ran the suite until every test passed.
- **Streamlit UI:** Rewrote `app.py` with four sections (Owner, Pets, Tasks, Today's plan). Data is stored in an `Owner` object in session state. It checked the app with Streamlit's `AppTest` by adding a pet, adding and editing tasks, and generating a plan.


**What did you have to verify or fix manually?**

- **UML rendering:** My first Mermaid preview failed with `UnknownDiagramError`. I had only selected part of the file, which left out the `classDiagram` header line. The agent explained the cause and also changed `**changes` to `changes: dict`, because `*` has a special meaning in Mermaid.
- **Design choices:** I reviewed the diagram and made changes myself. I removed and then restored `priority_score()` and the `Priority` enum, until the diagram matched what I wanted.
- **Test failure:** When I ran pytest in my own terminal, `test_task_accepts_priority_as_string` failed, because `.lower()` had been removed from `Task.__post_init__`. I gave the agent the error and it put `.lower()` back. All 21 tests passed again.
- **Checking the running app:** I ran the app myself and took screenshots. My screenshot showed a scheduling quirk: a task named "Morning Walks" with time of day set to "any" was placed at 12:30, after the afternoon tasks. Tasks without a preferred time are placed last, so the time of day has to be set to "morning" for it to be scheduled in the morning.
- **Honest documentation:** The agent did not claim features that don't exist. For example, it marked recurring tasks as "Not implemented" in the README instead of inventing them.

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | | |
| **Prompt** | | |
| **Response summary** | | |
| **What was useful** | | |
| **Problems noticed** | | |
| **Decision** | | |

**Which approach did you use in your final implementation and why?**

<!-- Your conclusion -->
