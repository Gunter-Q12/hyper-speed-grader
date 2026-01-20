"""Fetch and print full names of all users enrolled in a Canvas course.

Usage:
 - Set CANVAS_API_KEY in your environment (recommended).
 - Optionally set CANVAS_API_URL; default is https://canvas.instructure.com
"""

from canvasapi import Canvas
import os
import sys

API_URL = os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")
API_KEY = os.environ.get("CANVAS_API_KEY")
COURSE_ID = 13080964
if not API_KEY:
    print("Error: set the CANVAS_API_KEY environment variable.")
    sys.exit(1)

canvas = Canvas(API_URL, API_KEY)
course = canvas.get_course(COURSE_ID)

print(f"Enrolled users in course {COURSE_ID}:")
for user in course.get_users(enrollment_type=['student']):
    print(user.name)
