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
It considers fixed commitments of the owner (like meetings),the window of the day for activities (6am tot 10pm), available time, and due date. Then it acknnowledges priority, preferred time , pet activity level, leaving time between tasks, and best-fit scheduling. If there are conflicts, a warning is raised.

- How did you decide which constraints mattered most?
I first evaluated the non-flexible commitments of the owner (eg. work) as the most important. Then, priority comes in to organise the tasks. The additional constraints such as preference are less important compared to the fixed constraints.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
SInce the scheduler uses a greedy, priority-first placement (rather than using a globally optimal solution), this creates an issue where a single long, high-priority task can prevent several shorter, low-priority tasks from being scheduled.
- Why is that tradeoff reasonable for this scenario?
This is a reasonable tradeoff because the owner is concerned about completing tasks with high priority over completing the most tasks. Also, there is an explain() function that lets the owner know why a task wasnt scheduled so he/she can be aware it may be rescheduled for the next day.
---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
I used it to judge my brainstorming (to check if there were any grey areas or cases that were unnaccounted for), and to check that everything is logical and reasonable. I also used it to automate testing as well.


- How did using separate chat sessions for different phases help you stay organized?
I think it helped to refresh the model and kept its "working memory" free and focused on the task at hand. I will definitely use this from now on

- What kinds of prompts or questions were most helpful?
I liked the ones from the instructions that I wouldn't have thought to ask, like simplifying the code for readability. Since AI is made to sound so confident and sure of itself, we actually think it is 100% correct and accurate and then end up feeling unsure of our own ideas. So even when the code it gave worked, I didn't think to make it more readable (I just thought that experienced developers would be able to reason it out without difficulty and there was no issue with readability). So it was nice to think about that.
Also the prompts about assessing the current system design led to interesting discoveries and helped me understand the full picture of the system better.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
When implementing the daily recurrence logic, it suggested to create a new day at the end of each recurring task. I said that may cause issues swhen the owner tries to schedule ahead of time. Then it agreed with me and then made a method clear_plan() which only clears generated blocks whilts keeping the owner's commitments. This fix also led to other fixes...
- How did you evaluate or verify what the AI suggested?
I asked it to give me the pros and cons of each suggestion and i asked it to test it for and logical loopholes.
---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?

Happy paths — tasks get placed, never overlap commitments, high-priority tasks win contested slots, preferred times are honored (and bumped when blocked), and pets' activity levels bias placement (high→morning, low→afternoon).
Recurrence — completing a daily/weekly task spawns its next occurrence (+1/+7 days); one-off tasks spawn nothing.
Task retrieval — pending_tasks correctly excludes completed and future-dated tasks; filtering and chronological sorting work.
Conflict detection — same-time tasks are flagged (with correct same-pet/different-pet labels), and both clashing tasks still get scheduled.
Free windows — gaps are computed correctly around commitments, including overlapping/nested ones and a fully booked day.
Edge cases — no pets/no tasks, tasks that don't fit, exact-fit windows, the 10-minute buffer between tasks, and input normalization.
Day rollover — future-dated recurrences stay hidden until their day arrives, stale tasks roll forward without duplicating, and commitments survive the rollover.

- Why were these tests important?

These tests matter because the scheduling code can go wrong without crashing — it could quietly drop a task, forget to repeat a daily chore, or book two things at the same time, and the owner would trust a schedule that's actually wrong. The tests check that everything works the way it should, both in normal cases and tricky ones, so I can change the code later without accidentally breaking it. They also show clearly how the system is meant to behave. 

**b. Confidence**

- How confident are you that your scheduler works correctly?
75 before the tests. I just haven't explored other things that could cause it to behave differently

- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
The scheduling algorithm and the different factors it considers

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
I might try to find a way to extend it to a full calendar so you can see tasks for the week and not just for the day. I think daily schedules are great, but if you have a week in front of you, it will be easier to know when to schedule commitments having your pets in mind.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
I liked getting to work with AI to design the system. I haven't yet taken a software engineering course, so I am still new to system design, but it was interesting getting comfortable with knowing what is needed for a particular system and how different components interact with eachother.