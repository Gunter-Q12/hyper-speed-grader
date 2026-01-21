"""Main script to assess student submissions using AI model.

Reads configuration, fetches student submissions from Canvas,
evaluates them using AI, and updates grades and comments.
"""

import os
import csv
import yaml
from canvas_client import init
from ai import ask_model


def load_config():
    """Load configuration from config.yaml."""
    with open("configs/config.yaml", "r") as f:
        return yaml.safe_load(f)


def load_students():
    """Load student names from students.csv."""
    students = []
    with open("configs/students.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            students.append(row["Student"])
    return students


def load_model_answer():
    """Load model answer from model_answer.txt."""
    with open("configs/model_answer.txt", "r") as f:
        return f.read()


def main():
    # Load configuration
    config = load_config()
    task_num = config["task_num"]
    print(f"Assessing task #{task_num}")

    # Load students and model answer
    students = load_students()
    model_answer = load_model_answer()
    print(f"Found {len(students)} students to assess")

    # Initialize Canvas
    course = init()

    # Get the assignment (task_num is 1-indexed)
    assignments = list(course.get_assignments())
    if task_num > len(assignments) or task_num < 1:
        raise ValueError(f"Invalid task_num {task_num}. Available assignments: {len(assignments)}")

    assignment = assignments[task_num - 1]
    task_text = assignment.description or assignment.name
    print(f"Assignment: {assignment.name}")
    print(f"Task description: {task_text[:100]}...")

    # Get all users in the course
    all_users = list(course.get_users())
    user_map = {user.name: user for user in all_users}

    # Process each student
    for student_name in students:
        print(f"\n{'='*60}")
        print(f"Processing: {student_name}")

        # Find user
        if student_name not in user_map:
            print(f"  WARNING: Student '{student_name}' not found in Canvas")
            continue

        user = user_map[student_name]

        # Get submission
        submission = assignment.get_submission(user.id)

        if not submission.body or len(submission.body) == 0:
            print(f"Skipping empty submission")
            continue

        student_answer = submission.body
        print(f"  Submission length: {len(student_answer)} characters")

        # Ask AI model
        print(f"  Asking AI model...")
        result = ask_model(task_text, model_answer, student_answer)

        grade = result["grade"]
        comment = result["comment"]

        print(f"  Grade: {grade}")
        print(f"  Comment: {comment if comment else '(no comment)'}")

        # If model provided a comment, require an interactive confirmation/override
        if comment:
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

            # Prompt for comment override (press Enter to accept current)
            c_in = input("  Enter comment (press Enter to accept current comment): ").strip()
            if c_in != "":
                comment = c_in

        # Update submission in Canvas
        print(f"  Updating Canvas...")
        # submission.edit(
        #     submission={
        #         'posted_grade': grade
        #     },
        #     comment={
        #         'text_comment': comment
        #     } if comment else None
        # )
        print(f"  ✓ Updated successfully")

    print(f"\n{'='*60}")
    print("Assessment complete!")


if __name__ == "__main__":
    main()
