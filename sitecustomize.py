"""Project-level Python startup customizations.

CrewAI registers telemetry/event-bus shutdown handlers during import. In some
network environments this can block interpreter exit for a long time, which
breaks short health checks like `python -c "import crewai"` and pytest collect.

Disable telemetry by default for this repo unless explicitly overridden.
"""

from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")
