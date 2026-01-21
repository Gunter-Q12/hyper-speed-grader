"""Minimal script to print full names of users enrolled in a Canvas course."""

from canvas_client import init



course = init()
for user in course.get_users():
    print(user.name)
