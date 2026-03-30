# PawPal+ Project Reflection

## 1. System Design

Three core actions a user can perform
-Add a pet and basic pet info
-add and edit a task, name, description, duration and priority
-see todays tasks

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?
Classes I included are 
-Owner,A pet owner with time constraints and preferences
-Pet, A pet with its associated care tasks
-Task, A pet care task request (input to the scheduler)
-Scheduler, scheduler that produces a DailyPlan from an Owner's and pet's data

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.
added 2 enumeration classes, Priority[low, medium, high], and Task category, to organize the data better in the classes that need these Enum. 

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

The scheduler considers four constraints: the owner's available time budget (tasks are skipped if they don't fit), task priority (HIGH/MEDIUM/LOW), task category (e.g. medication always before walks at the same priority), and preferred start time (the scheduler honors a task's requested time if it's not before the owner's day start). Priority was treated as most important because a pet's medical needs should never be bumped for something optional like enrichment, regardless of duration or timing.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

The scheduler uses a greedy approach: it processes tasks in priority order and schedules each one as soon as it fits, without looking ahead. This means a single long HIGH-priority task could use up most of the time budget and cause several shorter MEDIUM tasks to be skipped, even if dropping the long task would fit more total tasks. This is a reasonable tradeoff for pet care because critical tasks like medications must always be included, and the owner is better served by transparency (a clear skipped list) than by a complex optimization that might drop a HIGH task to fit more LOW ones.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?
I first started by planning, using Opus, 4.6, because it is a good planner and implemented with Sonnet 4.6, I started by making a plan and giving it a detailed prompt on what I'm trying to build and how the nature of the project should be implemented. 
Then I started implementing feature by feature, making sure to test manually, and with pytest, along the way. The most usefull promt and quesitons I used were that on the nature of planning. 

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?
I did not accept the classes that the model reccomended to me at first but then I realized after reading more of it's reasoning that it was a pretty good class design. 

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

The 46 tests cover: priority ordering (HIGH before LOW, medication before walk), time budget enforcement (tasks skipped when over budget), time slot assignment (sequential, non-overlapping, preferred time honored), filtering by completion status and pet, recurring task creation, and conflict detection. These were important because the scheduler's core promise is "critical tasks first, within budget" — any bug in sorting or budget tracking would silently produce a wrong plan with no visible error.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

Fairly confident for normal use cases. The test suite covers all four smart features and the core scheduling path. If I had more time I'd test: a task whose duration exactly equals the remaining budget (boundary case), a preferred time at midnight that rolls over to the next day, and an owner with no pets at all.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
I am satisfied with the schedular logic and implementation, It is robust and implemented via a Greedy priority-first bin-packing

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
I would make the UI prettier, right now it is pretty simple but works. 

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
