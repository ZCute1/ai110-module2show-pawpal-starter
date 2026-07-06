"""Basic tests for PawPal+ core classes."""

from pawpal_system import Pet, Task


def test_task_completion():
    """Calling mark_complete() flips a task from incomplete to complete."""
    task = Task("Morning walk", 30, "high")
    assert task.completed is False  # starts incomplete

    task.mark_complete()

    assert task.completed is True


def test_task_addition_increases_count():
    """Adding a task to a Pet increases that pet's task count."""
    pet = Pet("Mochi", "dog", "Shiba Inu", "high")
    assert len(pet.tasks) == 0  # no tasks yet

    pet.add_task(Task("Feeding", 15, "high"))

    assert len(pet.tasks) == 1
