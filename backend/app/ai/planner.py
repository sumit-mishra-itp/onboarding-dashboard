"""The one AI capability (BRD §11): brief -> draft task list. Never saves anything; the manager approves."""
import json
import time

from pydantic import BaseModel, ValidationError

from ..core import Category, Priority, TaskIn
from .providers import AIError, Provider

PROMPT_VERSION = "v2"

SYSTEM = """You draft onboarding plans for new employees. Turn the manager's brief into a task list.
Rules:
- Return 5 to 15 tasks spread across weeks 1 to 4.
- day_offset is days after the start date (0 to {duration}); week_no must match it (days 0-6 = week 1, 7-13 = week 2, 14-20 = week 3, 21+ = week 4).
- title is 5 to 100 characters; description is under 500 characters; at most 6 short subtasks.
- Never invent people's names, email addresses or calendar dates.
Reply with only a JSON object matching this JSON schema:
{schema}"""


# Plain types only: the provider enforces shape, TaskIn enforces the length/range limits afterwards.
class _Task(BaseModel):
    title: str
    description: str
    category: Category
    week_no: int
    day_offset: int
    priority: Priority
    subtasks: list[str]


class Draft(BaseModel):
    tasks: list[_Task]


_SCHEMA = json.dumps(Draft.model_json_schema())


def draft_tasks(llm: Provider, job_title: str, team: str, duration_days: int,
                brief: str) -> tuple[list[TaskIn] | None, list[dict]]:
    """Returns (tasks or None, one ai_run_log row per attempt). One corrective retry on invalid output (BR-07).
    Only non-identifying context is sent (BRD §6 privacy): no names, emails or ids."""
    system = SYSTEM.format(duration=duration_days, schema=_SCHEMA)
    prompt = f"Job title: {job_title}\nTeam: {team}\nPlan duration: {duration_days} days\n\nManager brief:\n{brief}"
    content, logs = prompt, []
    for _ in range(2):
        log = {"prompt_version": PROMPT_VERSION, "model_identifier": f"{llm.name}/{llm.model}", "input_brief": brief,
               "raw_output": None, "validation_passed": False, "validation_errors": None,
               "prompt_tokens": None, "completion_tokens": None}
        t0, tasks, retry = time.monotonic(), None, True
        try:
            data, log["prompt_tokens"], log["completion_tokens"] = llm.complete(system, content, Draft)
            log["raw_output"] = data
            draft = Draft.model_validate(data)
            if not 1 <= len(draft.tasks) <= 15:
                raise ValueError(f"expected 1-15 tasks, got {len(draft.tasks)}")
            tasks = [TaskIn(**t.model_dump(), is_ai_generated=True) for t in draft.tasks]
            log["validation_passed"] = True
        except TimeoutError as e:
            log["validation_errors"], retry = f"timeout: {e}", False  # 20s budget spent; go straight to manual
        except (AIError, ValidationError, ValueError) as e:
            log["validation_errors"] = str(e)[:2000]
            content = f"{prompt}\n\nYour previous answer was rejected: {str(e)[:500]}\nFollow every rule exactly."
        log["latency_ms"] = int((time.monotonic() - t0) * 1000)
        logs.append(log)
        if tasks or not retry:
            return tasks, logs
    return None, logs
