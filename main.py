# Terminal demo: builds a small PawPal+ scenario and prints today's schedule.

from datetime import date

from pawpal_system import Owner, Pet, Task


def main() -> None:
    # One owner, planning for today.
    owner = Owner("Jordan", date.today())

    # Two pets with different details.
    mochi = Pet("Mochi", "dog", "Shiba Inu", "high")
    luna = Pet("Luna", "cat", "Tabby", "low")
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # At least three tasks, with different durations and priorities.
    mochi.add_task(Task("Morning walk", 45, "high", recurring_daily=True))
    mochi.add_task(Task("Training session", 30, "medium"))
    luna.add_task(Task("Feeding", 15, "high", recurring_daily=True))
    luna.add_task(Task("Playtime", 20, "low"))

    # The owner's fixed commitments (time constraints) the scheduler works around.
    print(owner.add_commitment(9 * 60, 17 * 60, "Work"))          # 09:00-17:00
    print(owner.add_commitment(12 * 60, 13 * 60, "Lunch w/ Sam")) # 12:00-13:00 (overlaps Work)

    # Let the scheduler build the day, then print it.
    owner.build_day()

    print("\n===== Today's Schedule =====")
    print(owner.schedule.explain())


if __name__ == "__main__":
    main()
