"""Main script to assess student submissions using AI model.

Reads configuration, fetches student submissions from Canvas,
evaluates them using AI, and updates grades and comments.

Behavior changes:
 - Accepts --prompt and --task (required) and --students (optional) to specify file paths
 - If --students is omitted, grades ALL students in the course
 - Skips students that already have a recorded grade
 - Passes (prompt, task, student_answer) to `ask_model`
"""

import os
import sys
import csv
import argparse
from typing import List, Optional, Any

from canvas_client import init
from ai import ask_model


def prompt_task_num(assignments_count: int) -> int:
    """Prompt the user to enter the task number to assess (1-indexed)."""
    while True:
        try:
            s = input(f"Enter task number to assess (1-{assignments_count}): ").strip()
            if not s:
                print("No task number provided. Exiting.", file=sys.stderr)
                sys.exit(2)
            num = int(s)
            if 1 <= num <= assignments_count:
                return num
            print(f"Invalid task number. Must be between 1 and {assignments_count}")
        except ValueError:
            print("Please enter an integer.")


def load_students_from_csv(path: str) -> List[str]:
    """Load student names from a CSV with a 'Student' column."""
    students: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            students.append(row["Student"])
    return students


def load_text_file(path: str, name: str) -> str:
    if not path:
        raise ValueError(f"{name} path is required")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _grade_of(submission: Any) -> str:
    """Return a string representation of an existing grade or empty string if none."""
    if submission is None:
        return ""
    for attr in ("score", "grade", "posted_grade", "entered_grade"):
        val = getattr(submission, attr, None)
        if val is not None and val != "":
            return str(val)
    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assess student submissions with AI")
    parser.add_argument("--prompt", required=True, help="Path to prompt.txt")
    parser.add_argument("--task", required=True, help="Path to task.txt")
    parser.add_argument("--students", help="Path to students.csv (optional). If omitted, grade all students in the course")
    parser.add_argument("--task-num", type=int, required=True, help="1-indexed task number to assess")
    parser.add_argument("--dry-run", action="store_true", help="Do not update Canvas; just print intended changes")
    parser.add_argument(
        "--confirmation",
        choices=["full", "none", "mistakes"],
        default="full",
        help=("Confirmation mode: 'full' prompts before each update, 'none' never prompts, "
              "'mistakes' prompts only when model returned a comment"),
    )
    return parser.parse_args()


def load_prompt_task(args: argparse.Namespace) -> (str, str):
    if not args.prompt or not args.task:
        raise SystemExit("Both --prompt and --task paths are required")
    try:
        prompt_text = load_text_file(args.prompt, "prompt")
        task_text = load_text_file(args.task, "task")
    except Exception as e:
        print(f"Error loading files: {e}", file=sys.stderr)
        raise SystemExit(2)
    return prompt_text, task_text


def choose_assignment(course, task_num: int):
    assignments = list(course.get_assignments())
    if not assignments:
        raise SystemExit("No assignments found in course")
    if task_num is None:
        raise SystemExit("No task number specified. Provide --task-num")
    if task_num < 1 or task_num > len(assignments):
        raise SystemExit(f"Invalid task_num {task_num}. Available assignments: {len(assignments)}")
    assignment = assignments[task_num - 1]
    print(f"Assignment: {assignment.name}")
    return assignment


def build_students_to_process(course, args: argparse.Namespace) -> List[Any]:
    # Prepare list of students to process
    all_users = list(course.get_users())
    user_map = {user.name: user for user in all_users}

    if args.students:
        # Read students from provided CSV by name
        try:
            requested_students = load_students_from_csv(args.students)
        except Exception as e:
            print(f"Error reading students CSV: {e}", file=sys.stderr)
            raise SystemExit(2)
        print(f"Loaded {len(requested_students)} students from {args.students}")

        # Map requested names to user objects, warn if not found
        students_to_process: List[Any] = []
        for name in requested_students:
            user = user_map.get(name)
            if not user:
                print(f"  WARNING: Student '{name}' not found in Canvas, skipping")
                continue
            students_to_process.append(user)
    else:
        # Process all students in the course
        students_to_process = list(course.get_users(enrollment_type=["student"]))
        print(f"Grading all {len(students_to_process)} students in the course")

    return students_to_process


def apply_update(submission, grade, comment, dry_run: bool) -> None:
    payload = {
        'submission': {'posted_grade': grade},
        'comment': {'text_comment': comment} if comment else None,
    }
    if dry_run:
        print(f"  DRY-RUN: would update with: {payload}")
        return
    # perform actual update
    try:
        submission.edit(submission=payload['submission'], comment=payload['comment'])
        print(f"  ✓ Updated successfully")
    except Exception as e:
        print(f"  ERROR updating submission: {e}")


def process_student(user, assignment, prompt_text: str, task_text: str, dry_run: bool = False, confirmation_mode: str = "full") -> None:
    display_name = getattr(user, "name", str(user))
    print(f"\n{'='*60}")
    print(f"Processing: {display_name}")

    submission = assignment.get_submission(user.id)

    # Skip if already graded
    existing_grade = _grade_of(submission)
    if existing_grade != "":
        print(f"  SKIP: Already graded (grade: {existing_grade})")
        return

    # Skip empty submissions
    if not submission or not getattr(submission, "body", None) or len(submission.body) == 0:
        print(f"  SKIP: Empty submission")
        return

    student_answer = submission.body
    print(f"  Submission length: {len(student_answer)} characters")

    # Ask AI model with (prompt, task, student_answer)
    print(f"  Asking AI model...")
    result = ask_model(prompt_text, task_text, student_answer)

    grade = result.get("grade")
    comment = result.get("comment")

    print(f"  Grade: {grade}")
    print(f"  Comment: {comment if comment else '(no comment)'}")

    # Decide whether to prompt the user
    should_prompt = False
    if confirmation_mode == "full":
        should_prompt = True
    elif confirmation_mode == "mistakes" and comment:
        should_prompt = True
    elif confirmation_mode == "none":
        should_prompt = False

    if not should_prompt:
        # Auto-apply
        apply_update(submission, grade, comment, dry_run)
        return

    # Interactive confirmation flow
    while True:
        print("[A] Accept / [E] Edit / [M] Manual")
        choice = input("Choose action: ").strip().lower()
        if choice == "a":
            apply_update(submission, grade, comment, dry_run)
            return
        elif choice == "e":
            # Prompt for grade override (press Enter to accept current)
            while True:
                g_in = input(f"  Enter grade (press Enter to accept current {grade}): ").strip()
                if g_in == "":
                    break
                try:
                    grade = float(g_in)
                    break
                except ValueError:
                    print("  Invalid grade, please enter a numeric value or press Enter to keep current.")

            # Prompt for comment override (press Enter to accept current, ':q' to set empty)
            c_in = input("  Enter comment (press Enter to accept current comment, or ':q' to set empty): ").strip()
            if c_in == "":
                # keep current comment
                pass
            elif c_in == ":q":
                # explicit empty comment
                comment = ""
            else:
                comment = c_in

            apply_update(submission, grade, comment, dry_run)
            return
        elif choice == "m":
            print("Manual review link: https://stub.com")
            cont = input("Continue (Y/n)? ").strip().lower()
            if cont == "" or cont == "y":
                # Do not update from script; assume manual grading will happen externally
                print("  Skipping update for manual grading")
                return
            else:
                # go back to menu
                continue
        else:
            print("Unknown choice. Please press A, E, or M.")


def main():
    args = parse_args()

    prompt_text, task_text = load_prompt_task(args)

    # Initialize Canvas and get assignment
    course = init()
    assignment = choose_assignment(course, args.task_num)

    students_to_process = build_students_to_process(course, args)

    # Process each student
    for user in students_to_process:
        process_student(user, assignment, prompt_text, task_text, dry_run=args.dry_run, confirmation_mode=args.confirmation)

    print(f"\n{'='*60}")
    print("Assessment complete!")
    # Initialize Canvas and get assignment
    course = init()
    assignments = list(course.get_assignments())

    task_num = prompt_task_num(len(assignments))
    print(f"Assessing task #{task_num}")

    if task_num > len(assignments) or task_num < 1:
        raise ValueError(f"Invalid task_num {task_num}. Available assignments: {len(assignments)}")

    assignment = assignments[task_num - 1]
    print(f"Assignment: {assignment.name}")

    # Prepare list of students to process
    all_users = list(course.get_users())
    user_map = {user.name: user for user in all_users}

    if args.students:
        # Read students from provided CSV by name
        try:
            requested_students = load_students_from_csv(args.students)
        except Exception as e:
            print(f"Error reading students CSV: {e}", file=sys.stderr)
            sys.exit(2)
        print(f"Loaded {len(requested_students)} students from {args.students}")

        # Map requested names to user objects, warn if not found
        students_to_process: List[Any] = []
        for name in requested_students:
            user = user_map.get(name)
            if not user:
                print(f"  WARNING: Student '{name}' not found in Canvas, skipping")
                continue
            students_to_process.append(user)
    else:
        # Process all students in the course
        students_to_process = list(course.get_users(enrollment_type=["student"]))
        print(f"Grading all {len(students_to_process)} students in the course")

    # Process each student
    for user in students_to_process:
        display_name = getattr(user, "name", str(user))
        print(f"\n{'='*60}")
        print(f"Processing: {display_name}")

        submission = assignment.get_submission(user.id)

        # Skip if already graded
        existing_grade = _grade_of(submission)
        if existing_grade != "":
            print(f"  SKIP: Already graded (grade: {existing_grade})")
            continue

        # Skip empty submissions
        if not submission or not getattr(submission, "body", None) or len(submission.body) == 0:
            print(f"  SKIP: Empty submission")
            continue

        student_answer = submission.body
        print(f"  Submission length: {len(student_answer)} characters")

        # Ask AI model with (prompt, task, student_answer)
        print(f"  Asking AI model...")
        result = ask_model(prompt_text, task_text, student_answer)

        grade = result.get("grade")
        comment = result.get("comment")

        print(f"  Grade: {grade}")
        print(f"  Comment: {comment if comment else '(no comment)'}")

        # If model provided a comment, require an interactive confirmation/override
        if comment:
            print(f"Student answer:\n{student_answer}")
            # Prompt for grade override (press Enter to accept current)
            while True:
                g_in = input(f"  Enter grade (press Enter to accept current {grade}): ").strip()
                if g_in == "":
                    break
                try:
                    grade = float(g_in)
                    break
                except ValueError:
                    print("  Invalid grade, please enter a numeric value or press Enter to keep current.")

            # Prompt for comment override (press Enter to accept current, ':q' to set empty)
            c_in = input("  Enter comment (press Enter to accept current comment, or ':q' to set empty): ").strip()
            if c_in == "":
                # keep current comment
                pass
            elif c_in == ":q":
                # explicit empty comment
                comment = ""
            else:
                comment = c_in

        # Update submission in Canvas
        print(f"  Updating Canvas...")
        submission.edit(
            submission={
                'posted_grade': grade
            },
            comment={
                'text_comment': comment
            } if comment else None
        )
        print(f"  ✓ Updated successfully")

    print(f"\n{'='*60}")
    print("Assessment complete!")


if __name__ == "__main__":
    main()
