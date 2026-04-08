"""WorkAI — Employee quality & audit system (v2).

Modular pipeline: ingest -> parse -> normalize -> assess -> audit.
Each module is independently replaceable. The contract between modules
is the database schema (raw_tasks, tasks_normalized, daily_task_assessments).
"""

__version__ = "2.0.0-dev"
