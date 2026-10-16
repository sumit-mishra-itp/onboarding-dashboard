"""Run: docker compose exec api python -m tests.test_core"""
from datetime import date

from pydantic import ValidationError

from app.core import TaskIn, current_week, due_date, metrics

start = date(2026, 10, 5)
assert due_date(start, 0) == start
assert due_date(start, 30) == date(2026, 11, 4)
assert current_week(start, date(2026, 10, 1)) == 1   # before start clamps to week 1
assert current_week(start, date(2026, 10, 12)) == 2
assert current_week(start, date(2026, 12, 1)) == 4   # after plan clamps to week 4

today = date(2026, 10, 10)
tasks = [
    {"status": "DONE", "due_date": date(2026, 10, 6)},
    {"status": "TO_DO", "due_date": date(2026, 10, 7)},     # overdue
    {"status": "BLOCKED", "due_date": date(2026, 10, 10)},  # due today: not overdue
    {"status": "TO_DO", "due_date": None},                  # draft: never overdue
]
certs = [
    {"is_mandatory": True, "is_completed": True, "deadline": date(2026, 10, 1)},
    {"is_mandatory": True, "is_completed": False, "deadline": date(2026, 10, 9)},  # overdue
    {"is_mandatory": False, "is_completed": False, "deadline": date(2026, 11, 1)},
]
conns = [{"status": "MET"}, {"status": "PENDING"}]
m = metrics(tasks, certs, conns, today)
assert m["task_completion_percentage"] == 25, m
assert m["total_overdue_items"] == 2, m
assert (m["completed_mandatory_certs"], m["total_mandatory_certs"]) == (1, 2), m
assert (m["met_connections"], m["total_connections"]) == (1, 2), m
assert metrics([], [], [], today)["task_completion_percentage"] is None

ok = dict(title="Set up laptop", category="TECHNICAL_SETUP", week_no=1, day_offset=0)
TaskIn(**ok)
for bad in ({"title": "abc"}, {"week_no": 5}, {"day_offset": 31}, {"category": "FUN"}, {"subtasks": ["x"] * 7}):
    try:
        TaskIn(**{**ok, **bad})
        raise AssertionError(f"accepted {bad}")
    except ValidationError:
        pass

print("ok")
