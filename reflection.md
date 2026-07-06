# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
My initial UML design consists of 5 classes: Owner, Pet, Task, Timeblock and Schedule. It defines how the owner, pets, tasks and schedule interact

- What classes did you include, and what responsibilities did you assign to each?
Owner: can add pets, track commitments (determines time constraints) and check off completed tasks.
Pet: stores data for a pet's details and holds the tasks associated with that pet
Task: tracks the individual tasks and keeps record of details like duration, priority level, daily recurrence and current completion state
Timeblock: represents a bounded slot on the calendar (defined by a start and end time) that hosts either a personal commitment or pet-related task.
Schedule: calcultes open windows of time and builds the optimal daily timeline by placing pet tasks around fixed commitments.

**b. Design changes**

- Did your design change during implementation?
Yes
- If yes, describe at least one change and why you made it.
1. Overflow handling with priority-first placement and an unplaced list
The original design didn't specify what happens when there isn't enough free time for every task. So I changed it to make build() place tasks highest-priority-first and record whatever doesn't fit in a Schedule.unplaced list, which explain() can then report.

2. Owner orchestrates scheduling instead of Schedule reaching into pets
In the original design it was unclear how Schedule got the tasks it places, since Schedule had no link to the pets. So I added an Owner.build_day() method that gathers every pending task and passes it into Schedule.build(tasks), so the Owner (the only object that knows all the pets) coordinates while Schedule stays focused on placement. This keeps the two classes seprarate and gives a single clear entry point.

3. Option D — Editable, non-destructive schedule (remove/move + clear_plan)
Originally the owner could only add commitments, and an early day-rollover idea would have wiped the whole schedule. I added remove_block/move_block for flexible commitments and a clear_plan() that removes only generated task placements while preserving the owner's commitments, so rebuilding a day never destroys what the owner entered

4. Time stored as minutes-since-midnight instead of time objects
Claude initially gave the skeleton containing block times as datetime.time, but time objects can't be added or subtracted, which the scheduler needs to compute end times and gaps. So, we switched start_min/end_min to integer minutes-since-midnight and added a fmt() helper for display, making the scheduling arithmetic simple and reliable.

5. Design change — the Scheduler retrieves its own tasks (Owner → Scheduler)
Originally the Owner was going to gather every pet's tasks and hand that list to the Schedule, keeping the Schedule decoupled from the pets. I changed this so the Schedule holds a back-reference to its Owner and pulls the tasks itself through a pending_tasks() method, which matches the project's instructions

6. link each Task back to its Pet
Originally a Task only stored its own details (title, duration, priority) and had no idea which pet it belonged to, so once the scheduler merged every pet's tasks into one timeline, the output couldn't say who each task was for — a "Morning walk" gave no hint whether it was the dog's or the cat's. I added a Task.pet back-reference that Pet.add_task sets automatically, and updated explain() to print "task for PetName," which makes a multi-pet schedule actually readable. I deliberately kept this field out of the constructor and out of the dataclass repr/eq so it can't cause an infinite Pet↔Task print loop.
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
