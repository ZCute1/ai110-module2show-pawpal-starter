# Terminal demo: builds a small PawPal+ scenario and prints today's schedule.

from datetime import date

from pawpal_system import Owner, Pet, Task


def main() -> None:
    """Run the terminal demo: set up an owner, pets, tasks, and commitments,
    then exercise sorting, filtering, conflict detection, scheduling, and
    recurrence — printing each result so the features can be seen end to end.
    """
    # One owner, planning for today.
    owner = Owner("Jordan", date.today())

    # Two pets with different details.
    mochi = Pet("Mochi", "dog", "Shiba Inu", "high")
    luna = Pet("Luna", "cat", "Tabby", "low")
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # Tasks added OUT OF ORDER on purpose, so sort_by_time has real work to do.
    # Each now carries a preferred "HH:MM" time.
    mochi.add_task(Task("Training session", 30, "medium", scheduled_time="15:00"))
    luna.add_task(Task("Feeding", 15, "high", scheduled_time="07:30", recurrence="daily"))
    mochi.add_task(Task("Morning walk", 45, "high", scheduled_time="08:00", recurrence="daily"))
    luna.add_task(Task("Playtime", 20, "low", scheduled_time="18:30", recurrence="weekly"))

    # A task that WANTS a midday slot (12:30) — but that's inside Work, so the
    # scheduler bumps it to the nearest free time and explain() flags it.
    mochi.add_task(Task("Vet phone call", 20, "medium", scheduled_time="12:30"))

    # Tasks with NO preferred time: placement leans on the pet's activity level.
    # Mochi is high-energy -> nudged toward morning; Luna is low-energy -> later.
    mochi.add_task(Task("Fetch in the yard", 20, "medium"))
    luna.add_task(Task("Grooming", 20, "low"))

    # Two tasks deliberately requested at the SAME time (06:30) — the conflict
    # detector should flag these before the scheduler quietly bumps one of them.
    mochi.add_task(Task("Groomer appointment", 30, "medium", scheduled_time="06:30"))
    mochi.add_task(Task("Puppy playdate", 30, "low", scheduled_time="06:30"))

    # Mark one task done so the status filter has something to show.
    owner.check_off(mochi.tasks[0])  # Training session

    # The owner's fixed commitments (time constraints) the scheduler works around.
    print(owner.add_commitment(9 * 60, 17 * 60, "Work"))          # 09:00-17:00
    print(owner.add_commitment(12 * 60, 13 * 60, "Lunch w/ Sam")) # 12:00-13:00 (overlaps Work)

    sched = owner.schedule

    # --- Sorting: tasks were added out of order; sort them by time of day. ---
    print("\n===== Tasks sorted by time =====")
    for t in sched.sort_by_time():
        status = "done" if t.completed else "pending"
        print(f"  {t.scheduled_time or '--:--'}  {t.title} for {t.pet_name} ({status})")

    # --- Filtering by pet name ---
    print("\n===== Luna's tasks =====")
    for t in sched.filter_tasks(pet_name="Luna"):
        print(f"  {t.scheduled_time or '--:--'}  {t.title}")

    # --- Filtering by completion status ---
    print("\n===== Still to do (incomplete) =====")
    for t in sched.filter_tasks(completed=False):
        print(f"  {t.scheduled_time or '--:--'}  {t.title} for {t.pet_name}")

    # --- Conflict detection: warn about tasks requested at the same time. ---
    print("\n===== Conflict check =====")
    conflicts = sched.detect_conflicts()
    if conflicts:
        for warning in conflicts:
            print(f"  ⚠️  {warning}")
    else:
        print("  No conflicting task times.")

    # Let the scheduler build the day, then print it.
    owner.build_day()

    print("\n===== Today's Schedule =====")
    print(sched.explain())

    # --- Recurrence: completing a recurring task spawns its next occurrence. ---
    print("\n===== Recurrence (spawn on complete) =====")
    feeding = luna.tasks[0]  # "Feeding" — a daily task
    print(f"Before: Luna has {len(luna.tasks)} tasks; "
          f"'{feeding.title}' ({feeding.recurrence}) due {feeding.due_date}.")
    owner.check_off(feeding)
    spawned = luna.tasks[-1]  # the freshly created next occurrence
    print(f"After completing it: Luna has {len(luna.tasks)} tasks; "
          f"new '{spawned.title}' due {spawned.due_date}.")

    # It's dated for tomorrow, so it stays off today's plan until the day rolls.
    owner.start_new_day()
    owner.build_day()
    print(f"\n===== Schedule after 'start new day' ({sched.day.isoformat()}) =====")
    print(sched.explain())


if __name__ == "__main__":
    main()
