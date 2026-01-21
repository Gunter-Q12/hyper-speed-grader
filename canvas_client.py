"""Minimal Canvas initializer.

Provides a single init(course_id) function that returns a Course object.
No error handling or extras - intentionally minimal.
"""

import os
from canvasapi import Canvas


def init():
    COURSE_ID = int(os.environ.get("CANVAS_COURSE_ID", "13080964"))
    API_URL = os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")
    API_KEY = os.environ.get("CANVAS_API_KEY")
    canvas = Canvas(API_URL, API_KEY)
    return canvas.get_course(COURSE_ID)
