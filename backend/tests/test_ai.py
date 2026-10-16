"""Run: docker compose exec api python -m tests.test_ai  (no network: uses a fake provider)"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql://unused")  # config needs it; this test never connects
os.environ.setdefault("APP_ENV", "dev")
os.environ["AI_PROVIDER"] = "groq"
from app import ai  # noqa: E402

assert isinstance(ai.create_provider("groq"), ai.Groq)
assert isinstance(ai.create_provider("GEMINI"), ai.Gemini)
assert ai.create_provider("groq", model="llama-3.3-70b-versatile").model == "llama-3.3-70b-versatile"
try:
    ai.create_provider("nope")
    raise AssertionError("accepted unknown provider")
except RuntimeError:
    pass

GOOD = {"tasks": [{"title": "Set up laptop", "description": "", "category": "TECHNICAL_SETUP", "week_no": 1,
                   "day_offset": 0, "priority": "HIGH", "subtasks": []}]}


class Fake(ai.Provider):
    name, key_env, default_model = "fake", "FAKE_KEY", "fake-1"

    def __init__(self, *answers):
        super().__init__()
        self.answers, self.prompts = list(answers), []

    def complete(self, system, user, schema):
        self.prompts.append(user)
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a, 10, 20


# bad output -> one corrective retry -> success
f = Fake({"tasks": [{**GOOD["tasks"][0], "title": "abc"}]}, GOOD)
tasks, logs = ai.draft_tasks(f, "Engineer", "Payments", 30, "brief text here")
assert tasks and tasks[0].is_ai_generated and len(logs) == 2, logs
assert [l["validation_passed"] for l in logs] == [False, True]
assert "previous answer was rejected" in f.prompts[1]
assert logs[0]["model_identifier"] == "fake/fake-1"

# timeout -> no retry, manual fallback
tasks, logs = ai.draft_tasks(Fake(TimeoutError("slow")), "Engineer", "Payments", 30, "brief text here")
assert tasks is None and len(logs) == 1 and logs[0]["validation_errors"].startswith("timeout")

# two API errors -> give up after the retry
tasks, logs = ai.draft_tasks(Fake(ai.AIError("500"), ai.AIError("500")), "Engineer", "Payments", 30, "brief text here")
assert tasks is None and len(logs) == 2

print("ok")
